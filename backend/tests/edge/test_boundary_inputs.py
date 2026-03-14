from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_oversized_resource_request_is_marked_failed(client):
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
    response = await client.post(
        "/api/tasks",
        json={"command": "echo big", "cpu_required": 9999, "mem_required": 9999},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "failed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cpu_required", "mem_required"),
    [(4, 1), (1, 8), (4, 8), (1, 1), (2147483647, 2147483647)],
)
async def test_boundary_values_are_accepted_by_schema(client, cpu_required: int, mem_required: int):
    response = await client.post(
        "/api/tasks",
        json={"command": "echo 你好世界 🌍", "cpu_required": cpu_required, "mem_required": mem_required},
    )

    assert response.status_code == 200
    assert response.json()["data"]["command"] == "echo 你好世界 🌍"


@pytest.mark.asyncio
async def test_shell_metacharacters_are_accepted_as_known_design_choice(client):
    response = await client.post(
        "/api/tasks",
        json={"command": "echo $(whoami) && rm -rf /", "cpu_required": 1, "mem_required": 1},
    )

    assert response.status_code == 200
    assert response.json()["data"]["command"] == "echo $(whoami) && rm -rf /"
