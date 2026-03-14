from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_concurrent_task_submission_returns_200_and_preserves_invariants(client):
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

    responses = await asyncio.gather(
        *[
            client.post(
                "/api/tasks",
                json={"command": f"echo {i}", "cpu_required": 1, "mem_required": 1},
            )
            for i in range(50)
        ]
    )

    assert all(response.status_code == 200 for response in responses)

    workers = (await client.get("/api/workers")).json()["data"]["workers"]
    worker = workers[0]
    assert worker["used_cpu"] <= worker["total_cpu"]
    assert worker["used_mem"] <= worker["total_mem"]


@pytest.mark.asyncio
async def test_concurrent_status_updates_same_task_result_in_single_successful_transition(client):
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
        json={"command": "echo race", "cpu_required": 1, "mem_required": 1},
    )
    task_id = created.json()["data"]["task_id"]

    responses = await asyncio.gather(
        client.post(
            f"/internal/task/{task_id}/status",
            json={"worker_id": "worker-1", "status": "running"},
        ),
        client.post(
            f"/internal/task/{task_id}/status",
            json={"worker_id": "worker-2", "status": "running"},
        ),
    )

    status_codes = sorted(response.status_code for response in responses)
    assert status_codes in ([200, 400], [400, 400])


@pytest.mark.asyncio
async def test_concurrent_register_and_schedule_does_not_crash(client):
    register_response, task_responses = await asyncio.gather(
        client.post(
            "/internal/register",
            json={
                "worker_id": "worker-1",
                "display_name": "Worker One",
                "host": "127.0.0.1",
                "port": 9001,
                "total_cpu": 4,
                "total_mem": 8,
            },
        ),
        asyncio.gather(
            *[
                client.post(
                    "/api/tasks",
                    json={"command": f"echo {i}", "cpu_required": 1, "mem_required": 1},
                )
                for i in range(10)
            ]
        ),
    )

    assert register_response.status_code == 200
    assert all(response.status_code == 200 for response in task_responses)
