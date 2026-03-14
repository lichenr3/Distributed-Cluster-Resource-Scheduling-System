from datetime import datetime, timezone
from typing import Literal

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from master.core import store
from master.schemas.ws import (
    LogConnectedFrame,
    LogLineFrame,
    TaskCompletedFrame,
)

log_subscribers: dict[str, set[WebSocket]] = {}


async def logs_ws_endpoint(websocket: WebSocket, task_id: str) -> None:
    await websocket.accept()
    subscribers = log_subscribers.setdefault(task_id, set())
    subscribers.add(websocket)

    connected_frame = LogConnectedFrame(
        task_id=task_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    await websocket.send_json(connected_frame.model_dump())

    history_lines = [
        {
            "line_no": line["line_no"],
            "content": line["content"],
            "timestamp": line["timestamp"],
        }
        for line in store.get_or_create_log_buffer(task_id)
    ]
    await websocket.send_json(
        {
            "type": "history",
            "task_id": task_id,
            "lines": history_lines,
        }
    )

    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _remove_subscriber(task_id, websocket)


def _remove_subscriber(task_id: str, websocket: WebSocket) -> None:
    subscribers = log_subscribers.get(task_id)
    if not subscribers:
        return
    subscribers.discard(websocket)
    if not subscribers:
        _ = log_subscribers.pop(task_id, None)


async def broadcast_log(task_id: str, log_entry: store.LogEntry) -> None:
    subscribers = log_subscribers.get(task_id)
    if not subscribers:
        return

    frame = LogLineFrame(
        task_id=task_id,
        line_no=log_entry["line_no"],
        content=log_entry["content"],
        timestamp=log_entry["timestamp"],
    )

    dead_connections: list[WebSocket] = []
    for websocket in list(subscribers):
        try:
            await websocket.send_json(frame.model_dump())
        except Exception:
            dead_connections.append(websocket)

    for websocket in dead_connections:
        _remove_subscriber(task_id, websocket)


async def broadcast_task_completed(
    task_id: str,
    status: Literal["success", "failed"],
    exit_code: int | None,
) -> None:
    subscribers = log_subscribers.get(task_id)
    if not subscribers:
        return

    safe_status: Literal["success", "failed"]
    if status == "success":
        safe_status = "success"
    else:
        safe_status = "failed"

    frame = TaskCompletedFrame(
        task_id=task_id,
        status=safe_status,
        exit_code=exit_code,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    dead_connections: list[WebSocket] = []
    for websocket in list(subscribers):
        try:
            await websocket.send_json(frame.model_dump())
        except Exception:
            dead_connections.append(websocket)

    for websocket in dead_connections:
        _remove_subscriber(task_id, websocket)


async def close_all_log_connections() -> None:
    for task_id, subscribers in list(log_subscribers.items()):
        for websocket in list(subscribers):
            try:
                await websocket.close()
            except Exception:
                pass
            finally:
                _remove_subscriber(task_id, websocket)
