from __future__ import annotations

from collections import deque

from master.core import store
from master.core.config import LOG_BUFFER_SIZE


def test_get_or_create_log_buffer_creates_and_reuses_same_buffer():
    buffer = store.get_or_create_log_buffer("task-1")

    assert isinstance(buffer, deque)
    assert buffer.maxlen == LOG_BUFFER_SIZE
    assert store.get_or_create_log_buffer("task-1") is buffer


def test_log_buffer_respects_maxlen():
    buffer = store.get_or_create_log_buffer("task-1")

    for index in range(LOG_BUFFER_SIZE + 1):
        buffer.append(
            {
                "line_no": index,
                "content": f"line-{index}",
                "timestamp": "2026-03-14T00:00:00+00:00",
            }
        )

    assert len(buffer) == LOG_BUFFER_SIZE
    assert buffer[0]["line_no"] == 1


def test_get_next_worker_display_name_increments_counter(reset_store):
    first = store.get_next_worker_display_name()
    second = store.get_next_worker_display_name()

    assert first == "worker-0"
    assert second == "worker-1"
    _ = reset_store


def test_store_typed_dict_shapes_via_factory_fixtures(make_worker, make_task, make_log_buffer):
    worker = make_worker(worker_id="worker-1", display_name="Worker One")
    task = make_task(task_id="task-1", worker_id=None)
    buffer = make_log_buffer("task-1")
    buffer.append({"line_no": 1, "content": "hello", "timestamp": "2026-03-14T00:00:00+00:00"})

    assert isinstance(worker["worker_id"], str)
    assert isinstance(worker["port"], int)
    assert worker["status"] in {"online", "offline"}
    assert isinstance(task["cpu_required"], int)
    assert task["status"] in {"pending", "running", "success", "failed"}
    assert isinstance(buffer[0]["line_no"], int)
    assert isinstance(buffer[0]["content"], str)
