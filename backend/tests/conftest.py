from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Callable, Generator, Literal

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from master.core import store
from master.core.config import LOG_BUFFER_SIZE


@pytest.fixture(autouse=True)
def reset_store() -> Generator[None, None, None]:
    store.workers.clear()
    store.tasks.clear()
    store.task_logs.clear()
    yield
    store.workers.clear()
    store.tasks.clear()
    store.task_logs.clear()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def make_worker() -> Callable[..., store.WorkerState]:
    def _make_worker(
        worker_id: str = "worker-1",
        *,
        display_name: str | None = None,
        host: str = "127.0.0.1",
        port: int = 9001,
        total_cpu: int = 4,
        total_mem: int = 8,
        used_cpu: int = 0,
        used_mem: int = 0,
        status: Literal["online", "offline"] = "online",
        task_count: int = 0,
        last_heartbeat: str | None = None,
        registered_at: str | None = None,
    ) -> store.WorkerState:
        now = _utc_now()
        worker: store.WorkerState = {
            "worker_id": worker_id,
            "display_name": display_name or worker_id,
            "host": host,
            "port": port,
            "total_cpu": total_cpu,
            "total_mem": total_mem,
            "used_cpu": used_cpu,
            "used_mem": used_mem,
            "status": status,
            "task_count": task_count,
            "last_heartbeat": last_heartbeat or now,
            "registered_at": registered_at or now,
        }
        store.workers[worker_id] = worker
        return worker

    return _make_worker


@pytest.fixture
def make_task() -> Callable[..., store.TaskState]:
    def _make_task(
        task_id: str = "task-1",
        *,
        command: str = "echo hello",
        cpu_required: int = 1,
        mem_required: int = 1,
        status: Literal["pending", "running", "success", "failed"] = "pending",
        worker_id: str | None = None,
        created_at: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
        scheduled_at: str | None = None,
    ) -> store.TaskState:
        now = _utc_now()
        task: store.TaskState = {
            "task_id": task_id,
            "command": command,
            "cpu_required": cpu_required,
            "mem_required": mem_required,
            "status": status,
            "worker_id": worker_id,
            "created_at": created_at or now,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        if scheduled_at is not None:
            task["scheduled_at"] = scheduled_at
        store.tasks[task_id] = task
        return task

    return _make_task


@pytest.fixture
def make_log_buffer() -> Callable[[str, int], deque[store.LogEntry]]:
    def _make_log_buffer(task_id: str, size: int = LOG_BUFFER_SIZE) -> deque[store.LogEntry]:
        buffer: deque[store.LogEntry] = deque(maxlen=size)
        store.task_logs[task_id] = buffer
        return buffer

    return _make_log_buffer
