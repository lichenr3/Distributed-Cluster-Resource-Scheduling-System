import asyncio
from datetime import datetime, timezone

import httpx

from master.core import store


class SchedulerService:
    def __init__(self) -> None:
        self._lock: asyncio.Lock = asyncio.Lock()

    def score_worker(
        self,
        worker_dict: store.WorkerState,
        task_dict: store.TaskState,
    ) -> float | None:
        if worker_dict["status"] != "online":
            return None

        remaining_cpu = worker_dict["total_cpu"] - worker_dict["used_cpu"]
        remaining_mem = worker_dict["total_mem"] - worker_dict["used_mem"]

        cpu_required = task_dict["cpu_required"]
        mem_required = task_dict["mem_required"]

        if remaining_cpu < cpu_required or remaining_mem < mem_required:
            return None

        score = ((remaining_cpu - cpu_required) / worker_dict["total_cpu"]) + (
            (remaining_mem - mem_required) / worker_dict["total_mem"]
        )
        return score

    async def schedule_task(self, task_dict: store.TaskState) -> bool:
        if task_dict["status"] != "pending" or task_dict.get("worker_id"):
            return False

        async with self._lock:
            best_worker: store.WorkerState | None = None
            best_score: float | None = None

            for worker in store.workers.values():
                score = self.score_worker(worker, task_dict)
                if score is None:
                    continue
                if best_score is None or score < best_score:
                    best_score = score
                    best_worker = worker

            if best_worker is None:
                return False

            best_worker["used_cpu"] += task_dict["cpu_required"]
            best_worker["used_mem"] += task_dict["mem_required"]
            best_worker["task_count"] += 1
            task_dict["worker_id"] = best_worker["worker_id"]

        dispatched = await self.dispatch_to_worker(best_worker, task_dict)
        if not dispatched:
            async with self._lock:
                if task_dict.get("worker_id") == best_worker["worker_id"]:
                    best_worker["used_cpu"] = max(
                        0, best_worker["used_cpu"] - task_dict["cpu_required"]
                    )
                    best_worker["used_mem"] = max(
                        0, best_worker["used_mem"] - task_dict["mem_required"]
                    )
                    best_worker["task_count"] = max(0, best_worker["task_count"] - 1)
                    task_dict["worker_id"] = None
                    task_dict["status"] = "pending"
            return False

        task_dict["scheduled_at"] = datetime.now(timezone.utc).isoformat()
        return True

    async def try_reschedule_pending(self) -> None:
        for task in list(store.tasks.values()):
            if task["status"] == "pending" and task.get("worker_id") is None:
                _ = await self.schedule_task(task)

    async def release_resources(self, task_id: str) -> None:
        task = store.tasks.get(task_id)
        if task is None:
            return
        worker_id = task.get("worker_id")
        if not worker_id:
            return

        worker = store.workers.get(worker_id)
        if worker is None:
            return

        async with self._lock:
            worker["used_cpu"] = max(0, worker["used_cpu"] - task["cpu_required"])
            worker["used_mem"] = max(0, worker["used_mem"] - task["mem_required"])
            worker["task_count"] = max(0, worker["task_count"] - 1)

    async def dispatch_to_worker(
        self,
        worker_dict: store.WorkerState,
        task_dict: store.TaskState,
    ) -> bool:
        worker_host = self._resolve_worker_host(worker_dict["host"])
        worker_url = f"http://{worker_host}:{worker_dict['port']}/execute"
        payload = {
            "task_id": task_dict["task_id"],
            "command": task_dict["command"],
            "cpu_required": task_dict["cpu_required"],
            "mem_required": task_dict["mem_required"],
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(worker_url, json=payload)
            return response.status_code < 400
        except httpx.HTTPError:
            return False

    @staticmethod
    def _resolve_worker_host(host: str) -> str:
        if host in {"0.0.0.0", "::", "[::]"}:
            return "127.0.0.1"
        return host
