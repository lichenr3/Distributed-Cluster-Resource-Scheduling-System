from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_terminal_state_reverse_transitions_rejected(client):
    created = await client.post(
        "/api/tasks",
        json={"command": "echo done", "cpu_required": 1, "mem_required": 1},
    )
    task_id = created.json()["data"]["task_id"]

    await client.post(
        f"/internal/task/{task_id}/status",
        json={"worker_id": "worker-1", "status": "failed"},
    )
    response = await client.post(
        f"/internal/task/{task_id}/status",
        json={"worker_id": "worker-1", "status": "running"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Task already in terminal state"


@pytest.mark.asyncio
async def test_pending_to_success_is_invalid_transition(client):
    await client.post(
        "/internal/register",
        json={
            "worker_id": "worker-1",
            "display_name": "Worker One",
            "host": "127.0.0.1",
            "port": 9001,
            "total_cpu": 4,
            "total_mem": 8,
        },
    )
    created = await client.post(
        "/api/tasks",
        json={"command": "echo skip", "cpu_required": 1, "mem_required": 1},
    )
    task_id = created.json()["data"]["task_id"]

    response = await client.post(
        f"/internal/task/{task_id}/status",
        json={"worker_id": "worker-1", "status": "success"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid status transition"


@pytest.mark.asyncio
async def test_running_to_pending_rejected_by_schema(client):
    created = await client.post(
        "/api/tasks",
        json={"command": "echo invalid", "cpu_required": 1, "mem_required": 1},
    )
    task_id = created.json()["data"]["task_id"]

    response = await client.post(
        f"/internal/task/{task_id}/status",
        json={"worker_id": "worker-1", "status": "pending"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_nonexistent_task_status_and_log_return_404(client):
    status_response = await client.post(
        "/internal/task/fake-id/status",
        json={"worker_id": "worker-1", "status": "running"},
    )
    log_response = await client.post(
        "/internal/task/fake-id/log",
        json={"worker_id": "worker-1", "line_no": 1, "content": "oops"},
    )

    assert status_response.status_code == 404
    assert status_response.json()["detail"] == "Task not found"
    assert log_response.status_code == 404
    assert log_response.json()["detail"] == "Task not found"
