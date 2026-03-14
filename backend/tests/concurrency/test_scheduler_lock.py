from __future__ import annotations

import asyncio

import pytest

from master.core import store
from master.services.scheduler import SchedulerService


@pytest.mark.asyncio
async def test_concurrent_schedule_exact_fit_prevents_overselling(monkeypatch, make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(worker_id="worker-1", total_cpu=4, total_mem=8)
    tasks = [make_task(task_id=f"task-{i}", cpu_required=2, mem_required=4) for i in range(10)]

    async def fake_dispatch(worker_dict, task_dict):
        await asyncio.sleep(0)
        return True

    monkeypatch.setattr(scheduler, "dispatch_to_worker", fake_dispatch)

    results = await asyncio.gather(*[scheduler.schedule_task(task) for task in tasks])

    assert sum(results) == 2
    assert sum(1 for task in tasks if task["worker_id"] == worker["worker_id"]) == 2
    assert worker["used_cpu"] == 4
    assert worker["used_mem"] == 8
    assert worker["used_cpu"] <= worker["total_cpu"]
    assert worker["used_mem"] <= worker["total_mem"]


@pytest.mark.asyncio
async def test_concurrent_schedule_cpu_bottleneck_limits_assignments(monkeypatch, make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(worker_id="worker-1", total_cpu=4, total_mem=8)
    tasks = [make_task(task_id=f"task-{i}", cpu_required=1, mem_required=1) for i in range(50)]

    async def fake_dispatch(worker_dict, task_dict):
        await asyncio.sleep(0)
        return True

    monkeypatch.setattr(scheduler, "dispatch_to_worker", fake_dispatch)

    results = await asyncio.gather(*[scheduler.schedule_task(task) for task in tasks])

    assert sum(results) == 4
    assert worker["used_cpu"] == 4
    assert worker["used_mem"] == 4
    assert worker["task_count"] == 4


@pytest.mark.asyncio
async def test_concurrent_schedule_and_release_keeps_resource_accounting_consistent(
    monkeypatch,
    make_worker,
    make_task,
):
    scheduler = SchedulerService()
    worker = make_worker(worker_id="worker-1", total_cpu=4, total_mem=8, used_cpu=2, used_mem=4, task_count=1)
    existing = make_task(task_id="existing", cpu_required=2, mem_required=4, worker_id="worker-1", status="running")
    tasks = [make_task(task_id=f"task-{i}", cpu_required=2, mem_required=4) for i in range(5)]

    async def fake_dispatch(worker_dict, task_dict):
        await asyncio.sleep(0)
        return True

    monkeypatch.setattr(scheduler, "dispatch_to_worker", fake_dispatch)

    results = await asyncio.gather(
        scheduler.release_resources(existing["task_id"]),
        *[scheduler.schedule_task(task) for task in tasks],
    )

    scheduled_count = sum(1 for item in results[1:] if item)
    assert scheduled_count <= 2
    assert 0 <= worker["used_cpu"] <= worker["total_cpu"]
    assert 0 <= worker["used_mem"] <= worker["total_mem"]
    existing["worker_id"] = None
    assigned = [
        task
        for task in store.tasks.values()
        if task.get("worker_id") == worker["worker_id"] and task["status"] == "pending"
    ]
    assert worker["used_cpu"] == sum(task["cpu_required"] for task in assigned)
    assert worker["used_mem"] == sum(task["mem_required"] for task in assigned)
