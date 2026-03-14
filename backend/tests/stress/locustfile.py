from __future__ import annotations

from locust import HttpUser, between, task


class SchedulerUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task(5)
    def submit_task(self) -> None:
        self.client.post(
            "/api/tasks",
            json={"command": "echo hello", "cpu_required": 1, "mem_required": 1},
            name="POST /api/tasks",
        )

    @task(1)
    def list_tasks(self) -> None:
        self.client.get("/api/tasks", name="GET /api/tasks")

    @task(1)
    def list_workers(self) -> None:
        self.client.get("/api/workers", name="GET /api/workers")
