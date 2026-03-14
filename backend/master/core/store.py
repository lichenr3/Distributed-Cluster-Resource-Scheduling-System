from collections import deque
from typing import Literal, NotRequired, TypedDict

from master.core.config import LOG_BUFFER_SIZE


class WorkerState(TypedDict):
    worker_id: str
    display_name: str
    host: str
    port: int
    total_cpu: int
    total_mem: int
    used_cpu: int
    used_mem: int
    status: Literal["online", "offline"]
    task_count: int
    last_heartbeat: str
    registered_at: str


class TaskState(TypedDict):
    task_id: str
    command: str
    cpu_required: int
    mem_required: int
    status: Literal["pending", "running", "success", "failed"]
    worker_id: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None
    scheduled_at: NotRequired[str]


class LogEntry(TypedDict):
    line_no: int
    content: str
    timestamp: str


workers: dict[str, WorkerState] = {}
tasks: dict[str, TaskState] = {}
task_logs: dict[str, deque[LogEntry]] = {}

_worker_name_counter: int = 0


def get_next_worker_display_name() -> str:
    """Generate next worker display name (worker-0, worker-1, ...)."""
    global _worker_name_counter
    name = f"worker-{_worker_name_counter}"
    _worker_name_counter += 1
    return name


def get_or_create_log_buffer(task_id: str) -> deque[LogEntry]:
    if task_id not in task_logs:
        task_logs[task_id] = deque(maxlen=LOG_BUFFER_SIZE)
    return task_logs[task_id]
