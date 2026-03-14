from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_workers_returns_empty_then_registered_workers(client):
    empty = await client.get("/api/workers")
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
    populated = await client.get("/api/workers")

    assert empty.status_code == 200
    assert empty.json()["data"] == {"workers": [], "total": 0}
    assert populated.status_code == 200
    assert populated.json()["data"]["total"] == 1
    assert populated.json()["data"]["workers"][0]["worker_id"] == "worker-1"
