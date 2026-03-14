import asyncio
from datetime import datetime, timezone

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from master.core import store
from master.core.config import CLUSTER_BROADCAST_INTERVAL
from master.schemas.ws import ClusterStateData, ClusterStateFrame

cluster_clients: set[WebSocket] = set()


async def cluster_ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    cluster_clients.add(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        cluster_clients.discard(websocket)


async def broadcast_cluster_state() -> None:
    if not cluster_clients:
        return

    workers: list[dict[str, object]] = []
    for worker in store.workers.values():
        worker_payload: dict[str, object] = {
            "worker_id": worker["worker_id"],
            "display_name": worker["display_name"],
            "host": worker["host"],
            "port": worker["port"],
            "total_cpu": worker["total_cpu"],
            "total_mem": worker["total_mem"],
            "used_cpu": worker["used_cpu"],
            "used_mem": worker["used_mem"],
            "status": worker["status"],
            "task_count": worker["task_count"],
            "last_heartbeat": worker["last_heartbeat"],
            "registered_at": worker["registered_at"],
        }
        workers.append(worker_payload)
    summary = {"pending": 0, "running": 0, "success": 0, "failed": 0, "total": 0}
    for task in store.tasks.values():
        summary[task["status"]] += 1
        summary["total"] += 1

    frame = ClusterStateFrame(
        timestamp=datetime.now(timezone.utc).isoformat(),
        data=ClusterStateData(workers=workers, tasks_summary=summary),
    )

    dead_connections: list[WebSocket] = []
    for websocket in list(cluster_clients):
        try:
            await websocket.send_json(frame.model_dump())
        except Exception:
            dead_connections.append(websocket)

    for websocket in dead_connections:
        cluster_clients.discard(websocket)


async def _cluster_broadcast_loop() -> None:
    while True:
        await broadcast_cluster_state()
        await asyncio.sleep(CLUSTER_BROADCAST_INTERVAL)


def start_cluster_broadcast() -> asyncio.Task[None]:
    return asyncio.create_task(_cluster_broadcast_loop(), name="cluster_broadcast")


async def close_all_cluster_connections() -> None:
    for websocket in list(cluster_clients):
        try:
            await websocket.close()
        except Exception:
            pass
        finally:
            cluster_clients.discard(websocket)
