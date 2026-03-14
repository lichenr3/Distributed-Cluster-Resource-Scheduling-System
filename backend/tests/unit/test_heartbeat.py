from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from master.services import heartbeat


@pytest.mark.asyncio
async def test_heartbeat_monitor_marks_workers_offline_after_timeout(monkeypatch, make_worker):
    stale_at = (datetime.now(timezone.utc) - timedelta(seconds=16)).isoformat()
    make_worker(worker_id="worker-stale", last_heartbeat=stale_at)
    make_worker(worker_id="worker-fresh", last_heartbeat=datetime.now(timezone.utc).isoformat())
    offline_calls: list[str] = []

    async def fake_mark_offline(worker_id: str):
        offline_calls.append(worker_id)

    async def fake_sleep(_: int):
        raise RuntimeError("stop-loop")

    monkeypatch.setattr(heartbeat.worker_service, "mark_offline", fake_mark_offline)
    monkeypatch.setattr(heartbeat.asyncio, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop-loop"):
        await heartbeat._heartbeat_monitor_loop()

    assert offline_calls == ["worker-stale"]


@pytest.mark.asyncio
async def test_heartbeat_monitor_skips_recent_and_offline_workers(monkeypatch, make_worker):
    recent_at = (datetime.now(timezone.utc) - timedelta(seconds=14)).isoformat()
    make_worker(worker_id="worker-boundary", last_heartbeat=recent_at, status="online")
    make_worker(worker_id="worker-offline", status="offline")
    offline_calls: list[str] = []

    async def fake_mark_offline(worker_id: str):
        offline_calls.append(worker_id)

    async def fake_sleep(_: int):
        raise RuntimeError("stop-loop")

    monkeypatch.setattr(heartbeat.worker_service, "mark_offline", fake_mark_offline)
    monkeypatch.setattr(heartbeat.asyncio, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop-loop"):
        await heartbeat._heartbeat_monitor_loop()

    assert offline_calls == []


@pytest.mark.asyncio
async def test_start_heartbeat_monitor_creates_named_task(monkeypatch):
    created: dict[str, object] = {}

    def fake_create_task(coro, name: str):
        created["coro"] = coro
        created["name"] = name
        coro.close()
        return "task-handle"

    monkeypatch.setattr(heartbeat.asyncio, "create_task", fake_create_task)

    result = heartbeat.start_heartbeat_monitor()

    assert result == "task-handle"
    assert created["name"] == "heartbeat_monitor"
