from datetime import datetime, timezone
from uuid import uuid4

from master.core import store
from master.schemas.task import TaskInfo, TaskLogReport, TaskStatusReport, TaskSubmitRequest
from master.services.scheduler import SchedulerService
from master.ws.logs import broadcast_log, broadcast_task_completed


class TaskService:
    def __init__(self, scheduler: SchedulerService) -> None:
        self.scheduler: SchedulerService = scheduler

    async def create_and_schedule(self, req: TaskSubmitRequest) -> TaskInfo:
        now = datetime.now(timezone.utc).isoformat()
        task_id = str(uuid4())

        task: store.TaskState = {
            "task_id": task_id,
            "command": req.command,
            "cpu_required": req.cpu_required,
            "mem_required": req.mem_required,
            "status": "pending",
            "worker_id": None,
            "created_at": now,
            "started_at": None,
            "finished_at": None,
        }
        store.tasks[task_id] = task
        _ = store.get_or_create_log_buffer(task_id)

        _ = await self.scheduler.schedule_task(task)
        return self._to_task_info(task)

    def list_tasks(
        self,
        status_filter: str | None = None,
    ) -> dict[str, list[TaskInfo] | int]:
        task_list: list[TaskInfo] = []
        for task in store.tasks.values():
            if status_filter and task["status"] != status_filter:
                continue
            task_list.append(self._to_task_info(task))
        return {"tasks": task_list, "total": len(task_list)}

    def get_task(self, task_id: str) -> TaskInfo | None:
        task = store.tasks.get(task_id)
        if task is None:
            return None
        return self._to_task_info(task)

    async def update_status(self, task_id: str, report: TaskStatusReport) -> TaskInfo:
        task = store.tasks.get(task_id)
        if task is None:
            raise KeyError(task_id)

        if task.get("worker_id") and task["worker_id"] != report.worker_id:
            raise ValueError("Worker mismatch for task status report")

        current = task["status"]
        next_status = report.status

        if current in {"success", "failed"}:
            raise ValueError("Task already in terminal state")
        if current == "pending" and next_status not in {"running", "failed"}:
            raise ValueError("Invalid status transition")
        if current == "running" and next_status not in {"success", "failed"}:
            raise ValueError("Invalid status transition")

        task["status"] = next_status
        now = datetime.now(timezone.utc).isoformat()
        if next_status == "running" and task["started_at"] is None:
            task["started_at"] = now
        if next_status in {"success", "failed"}:
            task["finished_at"] = now
            await self.scheduler.release_resources(task_id)
            completion_status = "success" if next_status == "success" else "failed"
            await broadcast_task_completed(task_id, completion_status, None)
            await self.scheduler.try_reschedule_pending()

        return self._to_task_info(task)

    async def append_log(self, task_id: str, report: TaskLogReport) -> dict[str, bool]:
        task = store.tasks.get(task_id)
        if task is None:
            raise KeyError(task_id)

        log_entry: store.LogEntry = {
            "line_no": report.line_no,
            "content": report.content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        store.get_or_create_log_buffer(task_id).append(log_entry)
        await broadcast_log(task_id, log_entry)
        return {"accepted": True}

    def _to_task_info(self, task: store.TaskState) -> TaskInfo:
        return TaskInfo(
            task_id=task["task_id"],
            command=task["command"],
            cpu_required=task["cpu_required"],
            mem_required=task["mem_required"],
            status=task["status"],
            worker_id=task["worker_id"],
            created_at=task["created_at"],
            started_at=task["started_at"],
            finished_at=task["finished_at"],
        )
