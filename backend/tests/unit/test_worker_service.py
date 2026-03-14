from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from master.core import store
from master.schemas.worker import WorkerHeartbeatRequest, WorkerRegisterRequest
from master.services.scheduler import SchedulerService
from master.services.worker_service import WorkerService


@pytest.fixture
def scheduler() -> SchedulerService:
    return SchedulerService()


@pytest.fixture
def service(scheduler: SchedulerService) -> WorkerService:
    return WorkerService(scheduler)


def build_register_request(
    worker_id: str = "worker-1",
    **overrides: Any,
) -> WorkerRegisterRequest:
    payload = {
        "worker_id": worker_id,
        "display_name": "Worker One",
        "host": "127.0.0.1",
        "port": 9001,
        "total_cpu": 4,
        "total_mem": 8,
    }
    payload.update(overrides)
    return WorkerRegisterRequest(**payload)


@pytest.mark.asyncio
async def test_register_creates_worker_with_initial_state(monkeypatch, service):
    reschedule_calls: list[str] = []

    async def fake_reschedule():
        reschedule_calls.append("called")

    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)

    result = await service.register(build_register_request())

    worker = store.workers["worker-1"]
    assert result == {"registered": True, "worker_id": "worker-1"}
    assert worker["status"] == "online"
    assert worker["used_cpu"] == 0
    assert worker["used_mem"] == 0
    assert worker["task_count"] == 0
    assert worker["display_name"] == "Worker One"
    assert reschedule_calls == ["called"]


@pytest.mark.asyncio
async def test_register_reregister_resets_resources_and_preserves_registered_at(monkeypatch, service, make_worker):
    original = make_worker(
        worker_id="worker-1",
        display_name="Original Name",
        total_cpu=8,
        total_mem=16,
        used_cpu=6,
        used_mem=12,
        task_count=3,
        status="offline",
        registered_at="2026-03-14T00:00:00+00:00",
    )

    async def fake_reschedule():
        return None

    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)

    await service.register(
        build_register_request(
            worker_id="worker-1",
            display_name=None,
            host="10.0.0.2",
            port=9010,
            total_cpu=4,
            total_mem=8,
        )
    )

    worker = store.workers["worker-1"]
    assert worker["registered_at"] == original["registered_at"]
    assert worker["display_name"] == "Original Name"
    assert worker["status"] == "online"
    assert worker["used_cpu"] == 0
    assert worker["used_mem"] == 0
    assert worker["task_count"] == 0
    assert worker["host"] == "10.0.0.2"
    assert worker["port"] == 9010


@pytest.mark.asyncio
async def test_register_cleans_up_stale_tasks_and_broadcasts(monkeypatch, service, make_task):
    running = make_task(task_id="task-running", status="running", worker_id="worker-1")
    pending = make_task(task_id="task-pending", status="pending", worker_id="worker-1")
    unrelated = make_task(task_id="task-other", status="running", worker_id="worker-2")
    completion_calls: list[tuple[str, str, int | None]] = []

    async def fake_broadcast(task_id: str, status: str, exit_code: int | None):
        completion_calls.append((task_id, status, exit_code))

    async def fake_reschedule():
        return None

    monkeypatch.setattr("master.services.worker_service.broadcast_task_completed", fake_broadcast)
    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)

    await service.register(build_register_request(worker_id="worker-1"))

    assert running["status"] == "failed"
    assert running["finished_at"] is not None
    assert pending["status"] == "pending"
    assert pending["worker_id"] is None
    assert unrelated["status"] == "running"
    assert completion_calls == [("task-running", "failed", None)]


@pytest.mark.asyncio
async def test_register_auto_generates_display_name(monkeypatch, service):
    async def fake_reschedule():
        return None

    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)

    await service.register(build_register_request(worker_id="worker-1", display_name=None))
    await service.register(build_register_request(worker_id="worker-2", display_name=None))

    assert store.workers["worker-1"]["display_name"] == "worker-0"
    assert store.workers["worker-2"]["display_name"] == "worker-1"


@pytest.mark.asyncio
async def test_heartbeat_returns_false_for_unknown_worker(service):
    result = await service.heartbeat(WorkerHeartbeatRequest(worker_id="missing"))

    assert result == {"exist": False}


@pytest.mark.asyncio
async def test_heartbeat_updates_timestamp_and_revives_offline_worker(monkeypatch, service, make_worker):
    worker = make_worker(
        worker_id="worker-1",
        status="offline",
        last_heartbeat=(datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
    )
    previous_heartbeat = worker["last_heartbeat"]
    reschedule_calls: list[str] = []

    async def fake_reschedule():
        reschedule_calls.append("called")

    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)

    result = await service.heartbeat(WorkerHeartbeatRequest(worker_id="worker-1"))

    assert result == {"exist": True}
    assert worker["status"] == "online"
    assert worker["last_heartbeat"] != previous_heartbeat
    assert reschedule_calls == ["called"]


@pytest.mark.asyncio
async def test_heartbeat_online_worker_does_not_reschedule(monkeypatch, service, make_worker):
    worker = make_worker(worker_id="worker-1", status="online")
    previous_heartbeat = worker["last_heartbeat"]
    reschedule_calls: list[str] = []

    async def fake_reschedule():
        reschedule_calls.append("called")

    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)

    result = await service.heartbeat(WorkerHeartbeatRequest(worker_id="worker-1"))

    assert result == {"exist": True}
    assert worker["status"] == "online"
    assert worker["last_heartbeat"] != previous_heartbeat
    assert reschedule_calls == []


@pytest.mark.asyncio
async def test_mark_offline_updates_tasks_releases_resources_and_reschedules(
    monkeypatch,
    service,
    make_worker,
    make_task,
):
    worker = make_worker(worker_id="worker-1", status="online")
    running = make_task(task_id="task-running", status="running", worker_id="worker-1")
    pending = make_task(task_id="task-pending", status="pending", worker_id="worker-1")
    other = make_task(task_id="task-other", status="running", worker_id="worker-2")
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
    monkeypatch.setattr("master.services.worker_service.broadcast_task_completed", fake_broadcast)

    await service.mark_offline(worker["worker_id"])

    assert worker["status"] == "offline"
    assert running["status"] == "failed"
    assert running["finished_at"] is not None
    assert pending["status"] == "pending"
    assert pending["worker_id"] is None
    assert other["status"] == "running"
    assert release_calls == ["task-running", "task-pending"]
    assert completion_calls == [("task-running", "failed", None)]
    assert reschedule_calls == ["called"]


@pytest.mark.asyncio
async def test_mark_offline_is_noop_for_missing_or_already_offline_worker(monkeypatch, service, make_worker):
    make_worker(worker_id="worker-1", status="offline")
    release_calls: list[str] = []
    reschedule_calls: list[str] = []

    async def fake_release(task_id: str):
        release_calls.append(task_id)

    async def fake_reschedule():
        reschedule_calls.append("called")

    monkeypatch.setattr(service.scheduler, "release_resources", fake_release)
    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)

    await service.mark_offline("worker-1")
    await service.mark_offline("missing")

    assert release_calls == []
    assert reschedule_calls == []


def test_list_workers_returns_all_registered_workers(service, make_worker):
    make_worker(worker_id="worker-1", display_name="one")
    make_worker(worker_id="worker-2", display_name="two", status="offline")

    result = service.list_workers()

    assert result["total"] == 2
    worker_ids = {worker.worker_id for worker in result["workers"]}
    assert worker_ids == {"worker-1", "worker-2"}
