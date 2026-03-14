from __future__ import annotations

import asyncio

import pytest

from master.core import store
from master.core.config import LOG_BUFFER_SIZE
from master.schemas.task import TaskLogReport
from master.services.scheduler import SchedulerService
from master.services.task_service import TaskService


@pytest.mark.asyncio
@pytest.mark.stress
async def test_high_frequency_log_api_caps_buffer_and_accepts_all(monkeypatch, make_task):
    scheduler = SchedulerService()
    service = TaskService(scheduler)
    task = make_task(task_id="task-flood")
    broadcast_count = 0

    async def fake_broadcast(task_id: str, log_entry):
        nonlocal broadcast_count
        broadcast_count += 1

    monkeypatch.setattr("master.services.task_service.broadcast_log", fake_broadcast)

    _ = await asyncio.gather(
        *[
            service.append_log(
                task["task_id"],
                TaskLogReport(worker_id="worker-1", line_no=index, content=f"line-{index}"),
            )
            for index in range(10_000)
        ]
    )

    buffer = store.task_logs[task["task_id"]]
    assert len(buffer) == LOG_BUFFER_SIZE
    assert buffer[0]["line_no"] == 9000
    assert buffer[-1]["line_no"] == 9999
    assert broadcast_count == 10_000


@pytest.mark.asyncio
@pytest.mark.stress
async def test_multiple_flooding_tasks_keep_each_buffer_bounded(monkeypatch, make_task):
    scheduler = SchedulerService()
    service = TaskService(scheduler)
    tasks = [make_task(task_id=f"task-{index}") for index in range(10)]

    async def fake_broadcast(task_id: str, log_entry):
        return None

    monkeypatch.setattr("master.services.task_service.broadcast_log", fake_broadcast)

    _ = await asyncio.gather(
        *[
            service.append_log(
                task["task_id"],
                TaskLogReport(worker_id="worker-1", line_no=line_no, content=f"{task['task_id']}-{line_no}"),
            )
            for task in tasks
            for line_no in range(2_000)
        ]
    )

    assert all(len(store.task_logs[task["task_id"]]) == LOG_BUFFER_SIZE for task in tasks)
    assert all(store.task_logs[task["task_id"]][0]["line_no"] == 1000 for task in tasks)
