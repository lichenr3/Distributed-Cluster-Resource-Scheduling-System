from __future__ import annotations

import pytest

from master.services.scheduler import SchedulerService


def test_score_worker_exact_fit_returns_zero(make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(total_cpu=4, total_mem=8)
    task = make_task(cpu_required=4, mem_required=8)

    assert scheduler.score_worker(worker, task) == 0.0


def test_score_worker_partial_fit_returns_expected_score(make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(total_cpu=4, total_mem=8)
    task = make_task(cpu_required=2, mem_required=4)

    assert scheduler.score_worker(worker, task) == 1.0


@pytest.mark.parametrize(
    ("worker_kwargs", "task_kwargs"),
    [
        ({"total_cpu": 4, "total_mem": 8, "used_cpu": 3}, {"cpu_required": 2, "mem_required": 1}),
        ({"total_cpu": 8, "total_mem": 2}, {"cpu_required": 2, "mem_required": 4}),
        ({"total_cpu": 1, "total_mem": 1}, {"cpu_required": 2, "mem_required": 2}),
        ({"total_cpu": 100, "total_mem": 100, "status": "offline"}, {"cpu_required": 1, "mem_required": 1}),
        ({"total_cpu": 4, "total_mem": 8, "used_cpu": 4}, {"cpu_required": 1, "mem_required": 1}),
    ],
)
def test_score_worker_returns_none_when_worker_cannot_fit(
    make_worker,
    make_task,
    worker_kwargs,
    task_kwargs,
):
    scheduler = SchedulerService()
    worker = make_worker(**worker_kwargs)
    task = make_task(**task_kwargs)

    assert scheduler.score_worker(worker, task) is None


def test_score_worker_handles_asymmetric_resources(make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(total_cpu=8, total_mem=4)
    task = make_task(cpu_required=1, mem_required=3)

    assert scheduler.score_worker(worker, task) == pytest.approx(1.125)


def test_can_any_worker_fit_checks_total_capacity_not_remaining(make_worker, make_task):
    scheduler = SchedulerService()
    make_worker(total_cpu=8, total_mem=16, used_cpu=8, used_mem=16)
    task = make_task(cpu_required=4, mem_required=8)

    assert scheduler.can_any_worker_fit(task) is True


@pytest.mark.asyncio
async def test_schedule_task_selects_best_fit_and_sets_scheduled_at(monkeypatch, make_worker, make_task):
    scheduler = SchedulerService()
    make_worker(worker_id="worker-a", total_cpu=4, total_mem=8, port=9101)
    worker_b = make_worker(worker_id="worker-b", total_cpu=2, total_mem=4, port=9102)
    task = make_task(cpu_required=2, mem_required=4)

    async def fake_dispatch(worker_dict, task_dict):
        return True

    monkeypatch.setattr(scheduler, "dispatch_to_worker", fake_dispatch)

    scheduled = await scheduler.schedule_task(task)

    assert scheduled is True
    assert task["worker_id"] == "worker-b"
    assert task.get("scheduled_at") is not None
    assert worker_b["used_cpu"] == 2
    assert worker_b["used_mem"] == 4
    assert worker_b["task_count"] == 1


@pytest.mark.asyncio
async def test_schedule_task_returns_false_when_no_worker_available(monkeypatch, make_task):
    scheduler = SchedulerService()
    task = make_task(cpu_required=2, mem_required=4)

    async def fake_dispatch(worker_dict, task_dict):
        return True

    monkeypatch.setattr(scheduler, "dispatch_to_worker", fake_dispatch)

    assert await scheduler.schedule_task(task) is False
    assert task["worker_id"] is None


@pytest.mark.asyncio
async def test_schedule_task_skips_preassigned_or_non_pending_tasks(monkeypatch, make_worker, make_task):
    scheduler = SchedulerService()
    make_worker()
    preassigned = make_task(task_id="task-preassigned", worker_id="worker-1")
    running = make_task(task_id="task-running", status="running")

    async def fake_dispatch(worker_dict, task_dict):
        return True

    monkeypatch.setattr(scheduler, "dispatch_to_worker", fake_dispatch)

    assert await scheduler.schedule_task(preassigned) is False
    assert await scheduler.schedule_task(running) is False


@pytest.mark.asyncio
async def test_schedule_task_rolls_back_resources_on_dispatch_failure(monkeypatch, make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(total_cpu=4, total_mem=8)
    task = make_task(cpu_required=2, mem_required=4)

    async def fake_dispatch(worker_dict, task_dict):
        return False

    monkeypatch.setattr(scheduler, "dispatch_to_worker", fake_dispatch)

    scheduled = await scheduler.schedule_task(task)

    assert scheduled is False
    assert task["worker_id"] is None
    assert task["status"] == "pending"
    assert worker["used_cpu"] == 0
    assert worker["used_mem"] == 0
    assert worker["task_count"] == 0


@pytest.mark.asyncio
async def test_release_resources_is_idempotent_and_never_negative(make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(used_cpu=2, used_mem=4, task_count=1)
    make_task(cpu_required=2, mem_required=4, worker_id=worker["worker_id"])

    await scheduler.release_resources("task-1")
    await scheduler.release_resources("task-1")

    assert worker["used_cpu"] == 0
    assert worker["used_mem"] == 0
    assert worker["task_count"] == 0


@pytest.mark.asyncio
async def test_release_resources_noops_for_missing_task_or_worker(make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(used_cpu=2, used_mem=2, task_count=1)
    make_task(task_id="task-without-worker", worker_id=None)
    make_task(task_id="task-missing-worker", worker_id="ghost", cpu_required=2, mem_required=2)

    await scheduler.release_resources("missing")
    await scheduler.release_resources("task-without-worker")
    await scheduler.release_resources("task-missing-worker")

    assert worker["used_cpu"] == 2
    assert worker["used_mem"] == 2
    assert worker["task_count"] == 1


@pytest.mark.asyncio
async def test_try_reschedule_pending_schedules_after_capacity_frees(monkeypatch, make_worker, make_task):
    scheduler = SchedulerService()
    worker = make_worker(total_cpu=4, total_mem=8, used_cpu=4, used_mem=8, task_count=1)
    task = make_task(cpu_required=2, mem_required=4)

    async def fake_dispatch(worker_dict, task_dict):
        return True

    monkeypatch.setattr(scheduler, "dispatch_to_worker", fake_dispatch)

    worker["used_cpu"] = 0
    worker["used_mem"] = 0
    worker["task_count"] = 0
    await scheduler.try_reschedule_pending()

    assert task["worker_id"] == worker["worker_id"]
    assert task.get("scheduled_at") is not None


@pytest.mark.asyncio
async def test_try_reschedule_pending_marks_unfittable_task_failed(make_task):
    scheduler = SchedulerService()
    task = make_task(cpu_required=100, mem_required=100)

    await scheduler.try_reschedule_pending()

    assert task["status"] == "failed"
    assert task["finished_at"] is not None
