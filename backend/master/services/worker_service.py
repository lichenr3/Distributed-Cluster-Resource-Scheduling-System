from datetime import datetime, timezone

from master.core import store
from master.schemas.worker import WorkerHeartbeatRequest, WorkerInfo, WorkerRegisterRequest
from master.services.scheduler import SchedulerService
from master.ws.logs import broadcast_task_completed


class WorkerService:
    def __init__(self, scheduler: SchedulerService) -> None:
        self.scheduler: SchedulerService = scheduler

    async def register(self, req: WorkerRegisterRequest) -> dict[str, bool | str]:
        now = datetime.now(timezone.utc).isoformat()
        existing = store.workers.get(req.worker_id)
        registered_at = existing["registered_at"] if existing else now
        # Use provided display_name or auto-generate one
        display_name = req.display_name or (existing["display_name"] if existing else store.get_next_worker_display_name())

        store.workers[req.worker_id] = {
            "worker_id": req.worker_id,
            "display_name": display_name,
            "host": req.host,
            "port": req.port,
            "total_cpu": req.total_cpu,
            "total_mem": req.total_mem,
            "used_cpu": 0,
            "used_mem": 0,
            "status": "online",
            "task_count": 0,
            "last_heartbeat": now,
            "registered_at": registered_at,
        }

        for task in store.tasks.values():
            if task.get("worker_id") == req.worker_id and task["status"] in {
                "pending",
                "running",
            }:
                task["worker_id"] = None
                if task["status"] == "running":
                    task["status"] = "failed"
                    task["finished_at"] = now
                    await broadcast_task_completed(task["task_id"], "failed", None)

        await self.scheduler.try_reschedule_pending()
        return {"registered": True, "worker_id": req.worker_id}

    async def heartbeat(self, req: WorkerHeartbeatRequest) -> dict[str, bool]:
        worker = store.workers.get(req.worker_id)
        if worker is None:
            return {"exist": False}

        was_offline = worker["status"] == "offline"
        worker["status"] = "online"
        worker["last_heartbeat"] = datetime.now(timezone.utc).isoformat()

        if was_offline:
            await self.scheduler.try_reschedule_pending()

        return {"exist": True}

    def list_workers(self) -> dict[str, list[WorkerInfo] | int]:
        workers = [self._to_worker_info(worker) for worker in store.workers.values()]
        return {"workers": workers, "total": len(workers)}

    async def mark_offline(self, worker_id: str) -> None:
        worker = store.workers.get(worker_id)
        if worker is None or worker["status"] == "offline":
            return

        now = datetime.now(timezone.utc).isoformat()
        worker["status"] = "offline"

        for task in store.tasks.values():
            if task.get("worker_id") != worker_id:
                continue

            if task["status"] == "running":
                task["status"] = "failed"
                task["finished_at"] = now
                await self.scheduler.release_resources(task["task_id"])
                await broadcast_task_completed(task["task_id"], "failed", None)
            elif task["status"] == "pending":
                await self.scheduler.release_resources(task["task_id"])
                task["worker_id"] = None

        await self.scheduler.try_reschedule_pending()

    def _to_worker_info(self, worker: store.WorkerState) -> WorkerInfo:
        return WorkerInfo(
            worker_id=worker["worker_id"],
            display_name=worker["display_name"],
            host=worker["host"],
            port=worker["port"],
            total_cpu=worker["total_cpu"],
            total_mem=worker["total_mem"],
            used_cpu=worker["used_cpu"],
            used_mem=worker["used_mem"],
            status=worker["status"],
            task_count=worker["task_count"],
            last_heartbeat=worker["last_heartbeat"],
            registered_at=worker["registered_at"],
        )
