from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from master.core import store
from master.main import app
from master.ws import logs


@pytest.mark.asyncio
async def test_logs_websocket_receives_connected_history_log_and_completion(make_task, make_log_buffer):
    task = make_task(task_id="task-1")
    buffer = make_log_buffer(task["task_id"])
    buffer.append({"line_no": 1, "content": "history line", "timestamp": "2026-03-14T00:00:00+00:00"})

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/logs/{task['task_id']}") as websocket:
            connected = websocket.receive_json()
            history = websocket.receive_json()

            await logs.broadcast_log(
                task["task_id"],
                {"line_no": 2, "content": "live line", "timestamp": "2026-03-14T00:00:01+00:00"},
            )
            live = websocket.receive_json()

            await logs.broadcast_task_completed(task["task_id"], "success", 0)
            completed = websocket.receive_json()

    assert connected["type"] == "connected"
    assert connected["task_id"] == task["task_id"]
    assert history == {
        "type": "history",
        "task_id": task["task_id"],
        "lines": [
            {
                "line_no": 1,
                "content": "history line",
                "timestamp": "2026-03-14T00:00:00+00:00",
            }
        ],
    }
    assert live["type"] == "log"
    assert live["content"] == "live line"
    assert completed["type"] == "task_completed"
    assert completed["status"] == "success"
    assert completed["exit_code"] == 0


@pytest.mark.asyncio
async def test_logs_broadcast_reaches_multiple_subscribers_and_cleans_dead_connections(make_task):
    task = make_task(task_id="task-1")

    class DeadWebSocket:
        async def send_json(self, payload):
            raise RuntimeError("dead")

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/logs/{task['task_id']}") as ws1:
            with client.websocket_connect(f"/ws/logs/{task['task_id']}") as ws2:
                _ = ws1.receive_json()
                _ = ws1.receive_json()
                _ = ws2.receive_json()
                _ = ws2.receive_json()

                dead = DeadWebSocket()
                logs.log_subscribers[task["task_id"]].add(dead)  # type: ignore[arg-type]

                await logs.broadcast_log(
                    task["task_id"],
                    {"line_no": 1, "content": "fanout", "timestamp": "2026-03-14T00:00:00+00:00"},
                )
                frame1 = ws1.receive_json()
                frame2 = ws2.receive_json()

    assert frame1["content"] == "fanout"
    assert frame2["content"] == "fanout"
    assert dead not in logs.log_subscribers.get(task["task_id"], set())


def test_logs_websocket_cleanup_removes_empty_task_key(make_task):
    task = make_task(task_id="task-1")

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/logs/{task['task_id']}") as websocket:
            _ = websocket.receive_json()
            _ = websocket.receive_json()
            assert task["task_id"] in logs.log_subscribers
            websocket.close()

    assert task["task_id"] not in logs.log_subscribers
