from __future__ import annotations

import pytest

from master.schemas.task import TaskStatusReport
from master.services.scheduler import SchedulerService
from master.services.task_service import TaskService


@pytest.mark.asyncio
async def test_dispatch_failure_rolls_back_resources(monkeypatch, make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(worker_id="worker-1", total_cpu=4, total_mem=8)
    task = make_task(cpu_required=2, mem_required=4)

    async def fake_dispatch(worker_dict, task_dict):
        return False

    monkeypatch.setattr(scheduler, "dispatch_to_worker", fake_dispatch)

    result = await scheduler.schedule_task(task)

    assert result is False
    assert worker["used_cpu"] == 0
    assert worker["used_mem"] == 0
    assert worker["task_count"] == 0
    assert task["worker_id"] is None
    assert task["status"] == "pending"


@pytest.mark.asyncio
async def test_failed_execution_releases_resources_and_reschedules(monkeypatch, make_worker, make_task):
    scheduler = SchedulerService()
    service = TaskService(scheduler)
    worker = make_worker(worker_id="worker-1", total_cpu=4, total_mem=8, used_cpu=2, used_mem=4, task_count=1)
    running = make_task(task_id="task-running", status="running", worker_id="worker-1", cpu_required=2, mem_required=4)
    pending = make_task(task_id="task-pending", status="pending", worker_id=None, cpu_required=2, mem_required=4)
    release_calls: list[str] = []
    reschedule_calls: list[str] = []

    async def fake_release(task_id: str):
        release_calls.append(task_id)
        worker["used_cpu"] = 0
        worker["used_mem"] = 0
        worker["task_count"] = 0

    async def fake_reschedule():
        reschedule_calls.append("called")

    async def fake_broadcast(task_id: str, status: str, exit_code: int | None):
        return None

    monkeypatch.setattr(service.scheduler, "release_resources", fake_release)
    monkeypatch.setattr(service.scheduler, "try_reschedule_pending", fake_reschedule)
    monkeypatch.setattr("master.services.task_service.broadcast_task_completed", fake_broadcast)

    result = await service.update_status(
        running["task_id"],
        TaskStatusReport(worker_id="worker-1", status="failed"),
    )

    assert result.status == "failed"
    assert release_calls == ["task-running"]
    assert reschedule_calls == ["called"]
    assert worker["used_cpu"] == 0
    assert worker["used_mem"] == 0
    assert worker["task_count"] == 0
    assert pending["status"] == "pending"
