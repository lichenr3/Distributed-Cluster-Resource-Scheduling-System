from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_task_accepts_valid_payload(client):
    response = await client.post(
        "/api/tasks",
        json={"command": "echo hello", "cpu_required": 1, "mem_required": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["message"] == "success"
    assert body["data"]["task_id"]
    assert body["data"]["status"] in {"pending", "failed"}
    assert body["data"]["command"] == "echo hello"


@pytest.mark.asyncio
async def test_create_task_rejects_invalid_payloads(client):
    empty_command = await client.post(
        "/api/tasks",
        json={"command": "", "cpu_required": 1, "mem_required": 1},
    )
    missing_fields = await client.post("/api/tasks", json={"command": "echo hello"})
    bad_cpu = await client.post(
        "/api/tasks",
        json={"command": "echo hello", "cpu_required": 0, "mem_required": 1},
    )

    assert empty_command.status_code == 422
    assert missing_fields.status_code == 422
    assert bad_cpu.status_code == 422


@pytest.mark.asyncio
async def test_list_tasks_returns_all_and_filters_by_status(client):
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
    pending_response = await client.post(
        "/api/tasks",
        json={"command": "echo pending", "cpu_required": 1, "mem_required": 1},
    )
    task_id = pending_response.json()["data"]["task_id"]
    status_update = await client.post(
        f"/internal/task/{task_id}/status",
        json={"worker_id": "worker-1", "status": "running"},
    )

    list_all = await client.get("/api/tasks")
    list_running = await client.get("/api/tasks", params={"status": "running"})
    list_success = await client.get("/api/tasks", params={"status": "success"})

    assert list_all.status_code == 200
    assert status_update.status_code == 200
    assert list_all.json()["data"]["total"] == 1
    assert list_running.json()["data"]["total"] == 1
    assert list_running.json()["data"]["tasks"][0]["status"] == "running"
    assert list_success.json()["data"] == {"tasks": [], "total": 0}


@pytest.mark.asyncio
async def test_list_tasks_rejects_invalid_status_filter(client):
    response = await client.get("/api/tasks", params={"status": "invalid"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid status filter"


@pytest.mark.asyncio
async def test_get_task_returns_existing_and_404_for_missing(client):
    created = await client.post(
        "/api/tasks",
        json={"command": "echo lookup", "cpu_required": 1, "mem_required": 1},
    )
    task_id = created.json()["data"]["task_id"]

    existing = await client.get(f"/api/tasks/{task_id}")
    missing = await client.get("/api/tasks/not-found")

    assert existing.status_code == 200
    assert existing.json()["data"]["task_id"] == task_id
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Task not found"
