from master.services.scheduler import SchedulerService
from master.services.task_service import TaskService
from master.services.worker_service import WorkerService

scheduler = SchedulerService()
task_service = TaskService(scheduler=scheduler)
worker_service = WorkerService(scheduler=scheduler)


def get_scheduler_service() -> SchedulerService:
    return scheduler


def get_task_service() -> TaskService:
    return task_service


def get_worker_service() -> WorkerService:
    return worker_service
