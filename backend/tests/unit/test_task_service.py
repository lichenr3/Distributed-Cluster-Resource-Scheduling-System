from __future__ import annotations

from collections import deque
from uuid import UUID

import pytest
from pydantic import ValidationError

from master.core import store
from master.core.config import LOG_BUFFER_SIZE
from master.schemas.task import TaskLogReport, TaskStatusReport, TaskSubmitRequest
from master.services.scheduler import SchedulerService
from master.services.task_service import TaskService


@pytest.fixture
def scheduler() -> SchedulerService:
    return SchedulerService()


@pytest.fixture
def service(scheduler: SchedulerService) -> TaskService:
    return TaskService(scheduler)


@pytest.mark.asyncio
async def test_create_and_schedule_creates_pending_task_and_log_buffer(monkeypatch, service):
    async def fake_schedule(task_dict):
        return False

    monkeypatch.setattr(service.scheduler, "schedule_task", fake_schedule)
    monkeypatch.setattr(service.scheduler, "can_any_worker_fit", lambda task_dict: True)

    result = await service.create_and_schedule(
        TaskSubmitRequest(command="echo hello", cpu_required=1, mem_required=2)
    )

    _ = UUID(result.task_id)
    assert result.status == "pending"
    assert result.worker_id is None
    assert result.created_at is not None
    assert result.started_at is None
    assert result.finished_at is None
    assert result.task_id in store.task_logs
    assert isinstance(store.task_logs[result.task_id], deque)
    assert store.task_logs[result.task_id].maxlen == LOG_BUFFER_SIZE


@pytest.mark.asyncio
async def test_create_and_schedule_marks_failed_when_no_worker_can_fit(monkeypatch, service):
    async def fake_schedule(task_dict):
        return False

    monkeypatch.setattr(service.scheduler, "schedule_task", fake_schedule)
    monkeypatch.setattr(service.scheduler, "can_any_worker_fit", lambda task_dict: False)

    result = await service.create_and_schedule(
        TaskSubmitRequest(command="python app.py", cpu_required=99, mem_required=99)
    )

    assert result.status == "failed"
    assert result.finished_at is not None


@pytest.mark.asyncio
async def test_update_status_pending_to_running_sets_started_at(service, make_task):
    task = make_task(status="pending", worker_id="worker-1")

    result = await service.update_status(
        task["task_id"],
        TaskStatusReport(worker_id="worker-1", status="running"),
    )

    assert result.status == "running"
    assert result.started_at is not None
    assert store.tasks[task["task_id"]]["started_at"] is not None


@pytest.mark.asyncio
async def test_update_status_running_to_success_releases_resources_and_reschedules(
    monkeypatch,
    service,
    make_task,
):
    task = make_task(status="running", worker_id="worker-1")
    release_calls: list[str] = []
    reschedule_calls: list[str] = []
    completion_calls: list[tuple[str, str, int | None]] = []

    async def fake_release(task_id: str):
        release_calls.append(task_id)

    async def fake_reschedule():
        reschedule_calls.append("called")

    async def fake_broadcast(task_id: str, status: str, exit_code: int | None):
        completion_calls.append((task_id, status, exit_code))

    monkeypatch.setattr(service.scheduler, "release_resources", fake_release)
    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)
    monkeypatch.setattr("master.services.task_service.broadcast_task_completed", fake_broadcast)

    result = await service.update_status(
        task["task_id"],
        TaskStatusReport(worker_id="worker-1", status="success"),
    )

    assert result.status == "success"
    assert result.finished_at is not None
    assert release_calls == [task["task_id"]]
    assert reschedule_calls == ["called"]
    assert completion_calls == [(task["task_id"], "success", None)]


@pytest.mark.asyncio
async def test_update_status_running_to_failed_broadcasts_failed(monkeypatch, service, make_task):
    task = make_task(status="running", worker_id="worker-1")
    completion_calls: list[tuple[str, str, int | None]] = []

    async def fake_release(task_id: str):
        return None

    async def fake_reschedule():
        return None

    async def fake_broadcast(task_id: str, status: str, exit_code: int | None):
        completion_calls.append((task_id, status, exit_code))

    monkeypatch.setattr(service.scheduler, "release_resources", fake_release)
    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)
    monkeypatch.setattr("master.services.task_service.broadcast_task_completed", fake_broadcast)

    result = await service.update_status(
        task["task_id"],
        TaskStatusReport(worker_id="worker-1", status="failed"),
    )

    assert result.status == "failed"
    assert completion_calls == [(task["task_id"], "failed", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("initial_status", "next_status", "error_type", "message"),
    [
        ("success", "running", ValueError, "Task already in terminal state"),
        ("success", "failed", ValueError, "Task already in terminal state"),
        ("failed", "running", ValueError, "Task already in terminal state"),
        ("pending", "success", ValueError, "Invalid status transition"),
        ("running", "pending", ValidationError, "Input should be 'running', 'success' or 'failed'"),
    ],
)
async def test_update_status_rejects_invalid_transitions(
    service,
    make_task,
    initial_status,
    next_status,
    error_type,
    message,
):
    task = make_task(status=initial_status, worker_id="worker-1")

    with pytest.raises(error_type, match=message):
        await service.update_status(
            task["task_id"],
            TaskStatusReport(worker_id="worker-1", status=next_status),
        )


@pytest.mark.asyncio
async def test_update_status_rejects_worker_mismatch(service, make_task):
    task = make_task(status="running", worker_id="worker-a")

    with pytest.raises(ValueError, match="Worker mismatch"):
        await service.update_status(
            task["task_id"],
            TaskStatusReport(worker_id="worker-b", status="success"),
        )


@pytest.mark.asyncio
async def test_update_status_raises_key_error_for_missing_task(service):
    with pytest.raises(KeyError):
        await service.update_status(
            "missing-task",
            TaskStatusReport(worker_id="worker-1", status="running"),
        )


@pytest.mark.asyncio
async def test_append_log_appends_and_broadcasts(monkeypatch, service, make_task):
    task = make_task()
    broadcast_calls: list[tuple[str, store.LogEntry]] = []

    async def fake_broadcast(task_id: str, log_entry: store.LogEntry):
        broadcast_calls.append((task_id, log_entry))

    monkeypatch.setattr("master.services.task_service.broadcast_log", fake_broadcast)

    result = await service.append_log(
        task["task_id"],
        TaskLogReport(worker_id="worker-1", line_no=1, content="hello log"),
    )

    assert result == {"accepted": True}
    assert len(store.task_logs[task["task_id"]]) == 1
    assert store.task_logs[task["task_id"]][0]["content"] == "hello log"
    assert broadcast_calls[0][0] == task["task_id"]
    assert broadcast_calls[0][1]["line_no"] == 1


@pytest.mark.asyncio
async def test_append_log_ring_buffer_caps_at_maxlen(monkeypatch, service, make_task):
    task = make_task()

    async def fake_broadcast(task_id: str, log_entry: store.LogEntry):
        return None

    monkeypatch.setattr("master.services.task_service.broadcast_log", fake_broadcast)

    for i in range(LOG_BUFFER_SIZE + 1):
        await service.append_log(
            task["task_id"],
            TaskLogReport(worker_id="worker-1", line_no=i, content=f"line-{i}"),
        )

    assert len(store.task_logs[task["task_id"]]) == LOG_BUFFER_SIZE
    assert store.task_logs[task["task_id"]][0]["line_no"] == 1


@pytest.mark.asyncio
async def test_append_log_raises_for_missing_task(service):
    with pytest.raises(KeyError):
        await service.append_log(
            "missing-task",
            TaskLogReport(worker_id="worker-1", line_no=1, content="oops"),
        )


def test_list_tasks_can_filter_by_status(service, make_task):
    make_task(task_id="task-pending", status="pending")
    make_task(task_id="task-running", status="running")

    pending_only = service.list_tasks(status_filter="pending")
    all_tasks = service.list_tasks()

    assert pending_only["total"] == 1
    assert pending_only["tasks"][0].task_id == "task-pending"
    assert all_tasks["total"] == 2
