import asyncio
from datetime import datetime, timezone

from master.core import store
from master.core.config import HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT
from master.core.dependencies import worker_service


async def _heartbeat_monitor_loop() -> None:
    while True:
        now = datetime.now(timezone.utc)
        workers_snapshot = list(store.workers.values())
        for worker in workers_snapshot:
            if worker["status"] != "online":
                continue
            last_heartbeat = datetime.fromisoformat(worker["last_heartbeat"])
            if (now - last_heartbeat).total_seconds() > HEARTBEAT_TIMEOUT:
                await worker_service.mark_offline(worker["worker_id"])
        await asyncio.sleep(HEARTBEAT_INTERVAL)


def start_heartbeat_monitor() -> asyncio.Task[None]:
    return asyncio.create_task(_heartbeat_monitor_loop(), name="heartbeat_monitor")
