from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_register_worker_and_reregister(client):
    first = await client.post(
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
    second = await client.post(
        "/internal/register",
        json={
            "worker_id": "worker-1",
            "display_name": "Worker One Reloaded",
            "host": "127.0.0.2",
            "port": 9002,
            "total_cpu": 8,
            "total_mem": 16,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"] == {"registered": True, "worker_id": "worker-1"}
    assert second.json()["data"] == {"registered": True, "worker_id": "worker-1"}


@pytest.mark.asyncio
async def test_register_worker_validates_required_fields(client):
    response = await client.post("/internal/register", json={"worker_id": "worker-1"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_worker_heartbeat_known_and_unknown(client):
    unknown = await client.post("/internal/heartbeat", json={"worker_id": "missing"})
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
    known = await client.post("/internal/heartbeat", json={"worker_id": "worker-1"})

    assert unknown.status_code == 200
    assert unknown.json()["data"] == {"exist": False}
    assert known.status_code == 200
    assert known.json()["data"] == {"exist": True}


@pytest.mark.asyncio
async def test_report_task_status_success_invalid_and_not_found(client):
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
        json={"command": "echo lifecycle", "cpu_required": 1, "mem_required": 1},
    )
    task_id = created.json()["data"]["task_id"]

    running = await client.post(
        f"/internal/task/{task_id}/status",
        json={"worker_id": "worker-1", "status": "running"},
    )
    invalid = await client.post(
        f"/internal/task/{task_id}/status",
        json={"worker_id": "worker-1", "status": "running"},
    )
    missing = await client.post(
        "/internal/task/missing/status",
        json={"worker_id": "worker-1", "status": "running"},
    )

    assert running.status_code == 200
    assert running.json()["data"]["status"] == "running"
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "Invalid status transition"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Task not found"


@pytest.mark.asyncio
async def test_report_task_log_accepts_existing_and_404_for_missing(client):
    created = await client.post(
        "/api/tasks",
        json={"command": "echo log", "cpu_required": 1, "mem_required": 1},
    )
    task_id = created.json()["data"]["task_id"]

    accepted = await client.post(
        f"/internal/task/{task_id}/log",
        json={"worker_id": "worker-1", "line_no": 1, "content": "hello"},
    )
    missing = await client.post(
        "/internal/task/missing/log",
        json={"worker_id": "worker-1", "line_no": 1, "content": "hello"},
    )

    assert accepted.status_code == 200
    assert accepted.json()["data"] == {"accepted": True}
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Task not found"
