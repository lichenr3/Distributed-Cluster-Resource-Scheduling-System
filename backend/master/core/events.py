import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from master.services.heartbeat import start_heartbeat_monitor
from master.ws.cluster import close_all_cluster_connections, start_cluster_broadcast
from master.ws.logs import close_all_log_connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    heartbeat_task = start_heartbeat_monitor()
    cluster_broadcast_task = start_cluster_broadcast()

    try:
        yield
    finally:
        for task in (heartbeat_task, cluster_broadcast_task):
            cancelled = task.cancel()
            _ = cancelled
        gathered = await asyncio.gather(
            heartbeat_task,
            cluster_broadcast_task,
            return_exceptions=True,
        )
        _ = gathered
        await close_all_cluster_connections()
        await close_all_log_connections()
