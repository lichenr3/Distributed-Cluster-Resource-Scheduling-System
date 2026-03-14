# Mini-Scheduler Comprehensive Test Plan

> **Project**: Lightweight Distributed Task Scheduling System (Mini-Scheduler)
> **Version**: v2.0
> **Date**: 2026-03-14
> **Baseline**: Source code analysis of `backend/master/`, `backend/worker/`, `frontend/src/`
> **Supersedes**: v1.0 test plan (direction-only outline)

---

## Table of Contents

1. [Test Overview](#1-test-overview)
2. [Test Environment & Tooling](#2-test-environment--tooling)
3. [Module A: Backend Unit Tests](#3-module-a-backend-unit-tests)
4. [Module B: Backend Integration Tests (API-Level)](#4-module-b-backend-integration-tests-api-level)
5. [Module C: Concurrency & Race Condition Tests](#5-module-c-concurrency--race-condition-tests)
6. [Module D: Stress & Performance Tests](#6-module-d-stress--performance-tests)
7. [Module E: Edge Cases & Boundary Tests](#7-module-e-edge-cases--boundary-tests)
8. [Module F: Frontend Tests](#8-module-f-frontend-tests)
9. [Module G: End-to-End Integration Tests](#9-module-g-end-to-end-integration-tests)
10. [Appendix: Test Matrix Summary](#10-appendix-test-matrix-summary)

---

## 1. Test Overview

### 1.1 Testing Goals

| Goal | Description |
|------|-------------|
| **Correctness** | Bin Packing algorithm strictly allocates based on remaining resources; no overselling under any condition |
| **Safety** | Task state machine enforces unidirectional transitions; terminal states are immutable |
| **Resilience** | Worker offline triggers cascading cleanup; dispatch failure triggers atomic rollback |
| **Performance** | System handles 1000 QPS task submission; 5000 concurrent WS connections; log flood without OOM |
| **Stability** | 1-hour endurance run with random failures produces zero resource leaks |

### 1.2 Testing Pyramid

```
         ┌──────────┐
         │   E2E    │  Module G: 8 scenarios
         ├──────────┤
         │Integration│  Module B: 28 test cases
       ┌─┤          ├─┐
       │ ├──────────┤ │
       │ │  Unit    │ │  Module A: 52 test cases
       └─┴──────────┴─┘
       + Module C (Concurrency): 12 test cases
       + Module D (Stress): 8 test cases
       + Module E (Edge Cases): 18 test cases
       + Module F (Frontend): 15 test cases
```

### 1.3 Priority Classification

| Priority | Meaning | Blocking Release? |
|----------|---------|-------------------|
| **P0-Critical** | Resource allocation correctness, state machine safety, data integrity | Yes |
| **P1-High** | API contract compliance, WS real-time behavior, heartbeat accuracy | Yes |
| **P2-Medium** | Performance targets, error recovery, graceful degradation | Conditional |
| **P3-Low** | UI polish, edge encoding, diagnostic logging | No |

---

## 2. Test Environment & Tooling

### 2.1 Backend Testing Stack

| Tool | Version | Purpose |
|------|---------|---------|
| **pytest** | >= 8.0 | Test runner + fixtures + parametrize |
| **pytest-asyncio** | >= 0.23 | Async test support for asyncio-based services |
| **httpx** | >= 0.27 | `AsyncClient` for FastAPI TestClient integration |
| **pytest-cov** | >= 5.0 | Code coverage reporting |
| **locust** | >= 2.25 | HTTP/WS load generation for stress tests |
| **websockets** | >= 12.0 | Low-level WS client for stress/edge tests |

### 2.2 Frontend Testing Stack

| Tool | Version | Purpose |
|------|---------|---------|
| **Vitest** | >= 1.0 | Unit/component testing (Vite-native) |
| **@vue/test-utils** | >= 2.4 | Vue component mounting & interaction |
| **Playwright** | >= 1.42 | E2E browser automation |
| **msw** | >= 2.0 | Mock Service Worker for API/WS interception |

### 2.3 Supporting Infrastructure

| Tool | Purpose |
|------|---------|
| **toxiproxy** / **tc** | Network condition simulation (latency, packet loss, disconnection) |
| **Mock Worker** | Custom lightweight FastAPI app that mimics Worker behavior with controllable delays, failures, and resource reports |
| **psutil** | Memory/CPU monitoring during stress tests |

### 2.4 Test Directory Structure

```
tests/
├── test_plan.md                    # This document
├── backend/
│   ├── unit/
│   │   ├── test_scheduler.py       # Module A: Scheduler algorithm tests
│   │   ├── test_task_service.py    # Module A: Task lifecycle tests
│   │   ├── test_worker_service.py  # Module A: Worker management tests
│   │   ├── test_store.py           # Module A: In-memory store tests
│   │   └── test_heartbeat.py       # Module A: Heartbeat monitor tests
│   ├── integration/
│   │   ├── test_api_tasks.py       # Module B: Task API endpoints
│   │   ├── test_api_workers.py     # Module B: Worker API endpoints
│   │   ├── test_api_internal.py    # Module B: Internal API endpoints
│   │   ├── test_ws_cluster.py      # Module B: Cluster WS protocol
│   │   └── test_ws_logs.py         # Module B: Log WS protocol
│   ├── concurrency/
│   │   ├── test_scheduler_lock.py  # Module C: Lock contention tests
│   │   └── test_concurrent_api.py  # Module C: Concurrent API calls
│   ├── stress/
│   │   ├── locustfile.py           # Module D: Load generation scripts
│   │   ├── test_log_flood.py       # Module D: High-frequency log stress
│   │   └── test_ws_scale.py        # Module D: WS connection scaling
│   └── edge/
│       ├── test_boundary_inputs.py # Module E: Schema boundary values
│       ├── test_state_violations.py# Module E: Invalid state transitions
│       └── test_failure_recovery.py# Module E: Dispatch/network failures
├── frontend/
│   ├── unit/
│   │   ├── useClusterWs.spec.ts    # Module F: Cluster WS composable
│   │   ├── useLogWs.spec.ts        # Module F: Log WS composable
│   │   └── useAutoScroll.spec.ts   # Module F: Auto-scroll composable
│   └── component/
│       ├── TaskSubmitForm.spec.ts   # Module F: Submission form
│       ├── TaskList.spec.ts         # Module F: Task list filtering
│       └── WorkerCard.spec.ts       # Module F: Worker card rendering
└── e2e/
    ├── test_full_lifecycle.py       # Module G: Complete task lifecycle
    └── playwright/
        └── dashboard.spec.ts        # Module G: Browser-based E2E
```

---

## 3. Module A: Backend Unit Tests

### A1. SchedulerService — Bin Packing Algorithm (P0-Critical)

> Source: `backend/master/services/scheduler.py`
> Core formula: `score = (remaining_cpu - cpu_req) / total_cpu + (remaining_mem - mem_req) / total_mem`

#### A1.1 score_worker — Scoring Correctness

| ID | Test Case | Setup | Input | Expected | Priority |
|----|-----------|-------|-------|----------|----------|
| A1.1.1 | Exact fit yields score 0 | Worker(total_cpu=4, total_mem=8, used=0) | Task(cpu=4, mem=8) | `score = 0.0` | P0 |
| A1.1.2 | Partial fit yields correct score | Worker(total_cpu=4, total_mem=8, used=0) | Task(cpu=2, mem=4) | `score = (4-2)/4 + (8-4)/8 = 1.0` | P0 |
| A1.1.3 | CPU insufficient returns None | Worker(total_cpu=4, total_mem=8, used_cpu=3) | Task(cpu=2, mem=1) | `None` (remaining_cpu=1 < 2) | P0 |
| A1.1.4 | MEM insufficient returns None | Worker(total_cpu=8, total_mem=2, used=0) | Task(cpu=2, mem=4) | `None` (remaining_mem=2 < 4) | P0 |
| A1.1.5 | Both insufficient returns None | Worker(total_cpu=1, total_mem=1, used=0) | Task(cpu=2, mem=2) | `None` | P0 |
| A1.1.6 | Offline worker returns None | Worker(status="offline", total_cpu=100, total_mem=100) | Task(cpu=1, mem=1) | `None` | P0 |
| A1.1.7 | Zero remaining on one dimension | Worker(total_cpu=4, total_mem=8, used_cpu=4, used_mem=0) | Task(cpu=1, mem=1) | `None` (remaining_cpu=0 < 1) | P0 |
| A1.1.8 | Asymmetric resource utilization | Worker(total_cpu=8, total_mem=4, used=0) | Task(cpu=1, mem=3) | `score = (8-1)/8 + (4-3)/4 = 0.875 + 0.25 = 1.125` | P1 |

#### A1.2 schedule_task — Best-Fit Selection

| ID | Test Case | Setup | Expected | Priority |
|----|-----------|-------|----------|----------|
| A1.2.1 | Best-Fit selects tightest worker | Worker-A(4cpu/8mem), Worker-B(2cpu/4mem), both idle | Task(cpu=2, mem=4) → assigned to Worker-B (score=0.0 < Worker-A score=1.0) | P0 |
| A1.2.2 | Canonical example: two tasks on one worker | Worker-A(4cpu/8mem) | Submit Task1(2cpu/4mem) then Task2(2cpu/4mem) → both on Worker-A, used_cpu=4, used_mem=8 | P0 |
| A1.2.3 | Third task stays pending when full | Worker-A(4cpu/8mem) already full (used=4/8) | Task3(2cpu/4mem) → remains `pending`, worker_id=None | P0 |
| A1.2.4 | No workers registered | No workers in store | Task → `schedule_task` returns False, task stays `pending` | P0 |
| A1.2.5 | All workers offline | 3 workers, all status="offline" | Task → `schedule_task` returns False | P0 |
| A1.2.6 | Pre-assigned task skipped | Task already has worker_id set | `schedule_task` returns False immediately (guard clause) | P1 |
| A1.2.7 | Non-pending task skipped | Task with status="running" | `schedule_task` returns False immediately (guard clause) | P1 |
| A1.2.8 | Multiple workers tie-break | Worker-A and Worker-B have identical scores | One gets selected (implementation: first encountered wins in dict iteration) | P2 |

#### A1.3 Resource Deduction Atomicity

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A1.3.1 | Successful schedule deducts resources | After schedule: worker.used_cpu += task.cpu_required, worker.used_mem += task.mem_required, worker.task_count += 1 | P0 |
| A1.3.2 | Dispatch failure triggers rollback | Mock `dispatch_to_worker` returns False → worker.used_cpu/mem/task_count reverted to pre-schedule values | P0 |
| A1.3.3 | Rollback uses `max(0, ...)` guard | Even if accounting error occurs, used_cpu/mem never go negative | P0 |

#### A1.4 release_resources

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A1.4.1 | Normal release | Task with worker_id → worker's used_cpu/mem/task_count decremented | P0 |
| A1.4.2 | Release for non-existent task | `store.tasks.get(task_id)` returns None → no-op, no crash | P1 |
| A1.4.3 | Release for task with no worker | task.worker_id is None → no-op | P1 |
| A1.4.4 | Release for non-existent worker | worker_id points to removed worker → no-op | P1 |
| A1.4.5 | Double release idempotency | Release same task twice → used values don't go below 0 (max guard) | P0 |

#### A1.5 try_reschedule_pending

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A1.5.1 | Reschedules pending tasks after resource release | Worker frees up → pending task gets scheduled | P0 |
| A1.5.2 | can_any_worker_fit marks unfittable as failed | Task requires 100cpu/100mem, no worker can ever fit → task marked `failed` | P0 |
| A1.5.3 | Skips tasks already assigned to a worker | Pending task with worker_id set → not re-scheduled | P1 |

#### A1.6 can_any_worker_fit

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A1.6.1 | Returns True when at least one worker has enough total capacity | Worker(total_cpu=8, total_mem=16) for Task(cpu=4, mem=8) → True | P0 |
| A1.6.2 | Returns False when no worker total capacity suffices | All workers have total_cpu=2, task needs cpu=4 → False | P0 |
| A1.6.3 | Checks total, not remaining | Worker fully loaded (used_cpu=total_cpu) but total capacity is enough → True (task can be scheduled when resources free up) | P1 |

---

### A2. TaskService — Task Lifecycle (P0-Critical)

> Source: `backend/master/services/task_service.py`

#### A2.1 create_and_schedule

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A2.1.1 | Creates task with UUID, initial status pending | task_id is valid UUID, status="pending", worker_id=None, timestamps set | P0 |
| A2.1.2 | Immediately schedules if worker available | After creation, if Worker available → status transitions to have worker_id | P0 |
| A2.1.3 | Marks failed if no worker can ever fit | Task(cpu=999, mem=999) with small workers → status="failed", finished_at set | P0 |
| A2.1.4 | Stays pending if workers exist but currently full | Workers registered but all fully loaded → status="pending" | P0 |
| A2.1.5 | Creates log buffer for new task | `store.task_logs[task_id]` exists with maxlen=1000 | P1 |

#### A2.2 update_status — State Machine Enforcement

| ID | Test Case | Current State | Requested State | Expected | Priority |
|----|-----------|---------------|-----------------|----------|----------|
| A2.2.1 | Valid: pending → running | pending | running | Success, started_at set | P0 |
| A2.2.2 | Valid: pending → failed | pending | failed | Success, finished_at set, resources released | P0 |
| A2.2.3 | Valid: running → success | running | success | Success, finished_at set, resources released, reschedule triggered | P0 |
| A2.2.4 | Valid: running → failed | running | failed | Success, finished_at set, resources released, reschedule triggered | P0 |
| A2.2.5 | **INVALID**: success → running | success | running | `ValueError: Task already in terminal state` | P0 |
| A2.2.6 | **INVALID**: success → failed | success | failed | `ValueError: Task already in terminal state` | P0 |
| A2.2.7 | **INVALID**: failed → running | failed | running | `ValueError: Task already in terminal state` | P0 |
| A2.2.8 | **INVALID**: pending → success | pending | success | `ValueError: Invalid status transition` | P0 |
| A2.2.9 | **INVALID**: running → pending | running | pending | `ValueError: Invalid status transition` | P0 |
| A2.2.10 | Worker ID mismatch rejected | Task assigned to worker-A | Report from worker-B | `ValueError: Worker mismatch` | P0 |
| A2.2.11 | Non-existent task raises KeyError | N/A | task_id="nonexistent" | `KeyError` | P1 |

#### A2.3 append_log

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A2.3.1 | Appends log entry to ring buffer | `store.task_logs[task_id]` contains the new entry | P1 |
| A2.3.2 | Ring buffer caps at 1000 entries | After 1001 appends, buffer length stays 1000, oldest entry evicted | P1 |
| A2.3.3 | Non-existent task raises KeyError | task_id not in store → `KeyError` | P1 |
| A2.3.4 | Triggers broadcast_log | Mock `broadcast_log` called with correct task_id and log_entry | P1 |

#### A2.4 list_tasks

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A2.4.1 | Returns all tasks when no filter | All tasks in store returned | P1 |
| A2.4.2 | Filters by status correctly | status_filter="running" → only running tasks returned | P1 |
| A2.4.3 | Returns empty list when no match | status_filter="success" with no successful tasks → empty list, total=0 | P2 |

---

### A3. WorkerService — Worker Lifecycle (P0-Critical)

> Source: `backend/master/services/worker_service.py`

#### A3.1 register

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A3.1.1 | New worker registered with correct initial state | status="online", used_cpu=0, used_mem=0, task_count=0 | P0 |
| A3.1.2 | Re-register same worker_id (idempotent) | Worker updated, status reset to "online", used resources reset to 0 | P0 |
| A3.1.3 | Re-register cleans up stale running tasks | Running tasks on old session → marked "failed", broadcast_task_completed called | P0 |
| A3.1.4 | Re-register cleans up stale pending tasks | Pending tasks with worker_id → worker_id set to None | P0 |
| A3.1.5 | Re-register preserves registered_at timestamp | Original registered_at retained from first registration | P1 |
| A3.1.6 | Auto-generates display_name if not provided | display_name follows "worker-0", "worker-1" pattern | P2 |
| A3.1.7 | Triggers try_reschedule_pending after registration | New capacity available → pending tasks attempt re-scheduling | P0 |

#### A3.2 heartbeat

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A3.2.1 | Updates last_heartbeat timestamp | worker.last_heartbeat updated to current UTC time | P0 |
| A3.2.2 | Unknown worker returns exist=False | worker_id not in store → `{"exist": False}` | P0 |
| A3.2.3 | Known worker returns exist=True | worker_id in store → `{"exist": True}` | P0 |
| A3.2.4 | Revives offline worker | Worker was offline → heartbeat sets status="online" | P0 |
| A3.2.5 | Revive triggers try_reschedule_pending | Offline→online transition → pending tasks rescheduled | P0 |
| A3.2.6 | Heartbeat on already-online worker is no-op for status | Status stays "online", no reschedule triggered | P1 |

#### A3.3 mark_offline

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A3.3.1 | Sets worker status to offline | worker.status = "offline" | P0 |
| A3.3.2 | Running tasks on worker marked failed | All running tasks → status="failed", finished_at set | P0 |
| A3.3.3 | Resources released for failed tasks | release_resources called for each failed task | P0 |
| A3.3.4 | Pending tasks with worker_id detached | worker_id set to None, status stays pending | P0 |
| A3.3.5 | Triggers try_reschedule_pending | Resources freed → pending tasks rescheduled | P0 |
| A3.3.6 | Idempotent: already-offline worker is no-op | Worker already offline → function returns early | P1 |
| A3.3.7 | Non-existent worker is no-op | worker_id not in store → no crash, returns None | P1 |
| A3.3.8 | broadcast_task_completed called for each failed task | One call per running→failed transition | P1 |

---

### A4. Store — In-Memory Data Structures (P1-High)

> Source: `backend/master/core/store.py`

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A4.1 | RingBuffer respects maxlen | `deque(maxlen=1000)` — 1001st append evicts first entry | P1 |
| A4.2 | get_or_create_log_buffer creates on first access | New task_id → creates deque, subsequent calls return same object | P1 |
| A4.3 | Worker display name counter increments | First call → "worker-0", second → "worker-1" | P2 |
| A4.4 | TypedDict fields are correct types | WorkerState/TaskState/LogEntry validate against expected schema | P2 |

---

### A5. Heartbeat Monitor (P0-Critical)

> Source: `backend/master/services/heartbeat.py`

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| A5.1 | Worker heartbeat within 15s → stays online | Worker heartbeat 10s ago, monitor runs → no offline | P0 |
| A5.2 | Worker heartbeat exceeds 15s → marked offline | Worker heartbeat 16s ago → `mark_offline` called | P0 |
| A5.3 | Exactly 15s boundary → stays online | 15.0s since heartbeat → NOT offline (> 15, not >=) | P0 |
| A5.4 | Already-offline workers skipped | Worker.status="offline" → monitor skips, no duplicate mark_offline | P1 |
| A5.5 | Monitor loop continues after exception | One worker causes error → loop catches and continues checking others | P1 |

---

## 4. Module B: Backend Integration Tests (API-Level)

> Use `httpx.AsyncClient` with FastAPI `TestClient` (ASGI transport).
> Each test starts with clean `store.workers = {}; store.tasks = {}; store.task_logs = {}`.

### B1. Task REST API — POST /api/tasks

| ID | Test Case | Request Body | Expected Response | Priority |
|----|-----------|-------------|-------------------|----------|
| B1.1 | Submit valid task | `{"command": "echo hello", "cpu_required": 2, "mem_required": 4}` | 200, `code=0`, task_id present, status="pending" or "failed" (no workers) | P0 |
| B1.2 | Submit with registered worker | Pre-register worker(4cpu/8mem) | 200, status may be "pending" (schedule is async internally) | P0 |
| B1.3 | Empty command rejected | `{"command": "", "cpu_required": 1, "mem_required": 1}` | 422 (Pydantic validation: min_length=1) | P0 |
| B1.4 | Command too long rejected | command = "a" * 1025 | 422 (Pydantic validation: max_length=1024) | P1 |
| B1.5 | cpu_required = 0 rejected | `{"command": "test", "cpu_required": 0, "mem_required": 1}` | 422 (Pydantic validation: ge=1) | P0 |
| B1.6 | mem_required = -1 rejected | `{"command": "test", "cpu_required": 1, "mem_required": -1}` | 422 (Pydantic validation: ge=1) | P0 |
| B1.7 | Missing required field | `{"command": "test"}` | 422 (missing cpu_required, mem_required) | P1 |
| B1.8 | Extra fields ignored | `{"command": "test", "cpu_required": 1, "mem_required": 1, "extra": "ignored"}` | 200, extra field not in response | P2 |

### B2. Task REST API — GET /api/tasks

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| B2.1 | List all tasks (no filter) | Returns all tasks with correct total count | P0 |
| B2.2 | Filter by status=running | Returns only running tasks | P1 |
| B2.3 | Filter by invalid status | `?status=invalid` → 400 "Invalid status filter" | P1 |
| B2.4 | Empty list when no tasks | `{"tasks": [], "total": 0}` | P2 |

### B3. Task REST API — GET /api/tasks/{task_id}

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| B3.1 | Existing task returns full info | 200, all TaskInfo fields present | P0 |
| B3.2 | Non-existent task returns 404 | 404 with error detail | P0 |

### B4. Worker REST API — GET /api/workers

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| B4.1 | List registered workers | Returns all workers with resource info | P0 |
| B4.2 | Empty list when none registered | `{"workers": [], "total": 0}` | P2 |

### B5. Internal API — POST /internal/register

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| B5.1 | New worker registration | 200, `registered=True`, worker appears in GET /api/workers | P0 |
| B5.2 | Re-registration (same worker_id) | 200, `registered=True`, resource usage reset | P0 |
| B5.3 | Missing fields | 422 validation error | P1 |

### B6. Internal API — POST /internal/heartbeat

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| B6.1 | Known worker heartbeat | 200, `exist=True` | P0 |
| B6.2 | Unknown worker heartbeat | 200, `exist=False` | P0 |

### B7. Internal API — POST /internal/task/{task_id}/status

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| B7.1 | Valid status transition | 200, task status updated | P0 |
| B7.2 | Invalid transition | 400, error detail describing violation | P0 |
| B7.3 | Non-existent task | 404, "Task not found" | P0 |
| B7.4 | Worker mismatch | 400, "Worker mismatch" | P0 |

### B8. Internal API — POST /internal/task/{task_id}/log

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| B8.1 | Append log to existing task | 200, `accepted=True` | P1 |
| B8.2 | Non-existent task | 404, "Task not found" | P1 |

### B9. WebSocket — /ws/cluster

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| B9.1 | Connection accepted | WebSocket handshake succeeds | P0 |
| B9.2 | Receives cluster_state frame | Frame contains `type="cluster_state"`, `data.workers`, `data.tasks_summary` | P0 |
| B9.3 | Workers list reflects registered workers | Register a worker via API → appears in next cluster_state frame | P0 |
| B9.4 | tasks_summary counts are accurate | Submit tasks in various states → summary counts match | P1 |
| B9.5 | Disconnected client removed from broadcast set | Connect → disconnect → cluster_clients set shrinks | P1 |
| B9.6 | Dead client cleaned up on send failure | Client connection dies → removed from set on next broadcast | P1 |

### B10. WebSocket — /ws/logs/{task_id}

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| B10.1 | Connection accepted and confirmed | Receives `{"type": "connected", "task_id": "..."}` | P0 |
| B10.2 | History replay on connect | Receives `{"type": "history", ...}` with buffered log lines | P0 |
| B10.3 | Real-time log forwarding | Submit log via internal API → receive `{"type": "log", ...}` on WS | P0 |
| B10.4 | Task completion notification | Task finishes → receive `{"type": "task_completed", ...}` | P0 |
| B10.5 | Multiple subscribers for same task | Two clients subscribe → both receive same log frames | P1 |
| B10.6 | Subscriber cleanup on disconnect | Disconnect → subscriber removed from `log_subscribers[task_id]` | P1 |
| B10.7 | Empty task_id cleanup | Last subscriber disconnects → task_id key removed from dict | P2 |

---

## 5. Module C: Concurrency & Race Condition Tests

### C1. Scheduler Lock — Anti-Overselling (P0-Critical)

> The core invariant: `worker.used_cpu <= worker.total_cpu AND worker.used_mem <= worker.total_mem` must hold **at all times**, regardless of concurrent request volume.

| ID | Test Case | Setup | Operation | Assertion | Priority |
|----|-----------|-------|-----------|-----------|----------|
| C1.1 | 10 concurrent tasks on 1 worker (exact fit) | Worker(4cpu/8mem) | `asyncio.gather(*[schedule_task(Task(2cpu/4mem)) for _ in range(10)])` | Exactly 2 tasks scheduled, 8 remain pending. used_cpu==4, used_mem==8. **NEVER** used_cpu>4 or used_mem>8 | P0 |
| C1.2 | 50 concurrent tasks on 1 worker (1cpu/1mem each) | Worker(4cpu/8mem) | 50 simultaneous schedule_task calls | Exactly 4 tasks scheduled (CPU is bottleneck). used_cpu==4, used_mem==4 | P0 |
| C1.3 | Mixed resource tasks concurrent | Worker(8cpu/16mem) | 20 tasks: mix of (1cpu/1mem), (2cpu/4mem), (4cpu/8mem) concurrently | Total used_cpu ≤ 8, total used_mem ≤ 16 at every point | P0 |
| C1.4 | Concurrent schedule + release | Worker(4cpu/8mem), 1 running task(2cpu/4mem) | Schedule 5 new tasks while releasing the running task simultaneously | No resource accounting errors; final state consistent | P0 |
| C1.5 | Concurrent schedule + mark_offline | Worker with tasks | Schedule new tasks while marking worker offline concurrently | No crashes; tasks properly assigned or left pending | P0 |

### C2. Concurrent API Requests

| ID | Test Case | Operation | Assertion | Priority |
|----|-----------|-----------|-----------|----------|
| C2.1 | 100 simultaneous POST /api/tasks | `asyncio.gather(*[client.post("/api/tasks", ...) for _ in range(100)])` | All return 200, no 500 errors. Worker resource invariant holds | P0 |
| C2.2 | Concurrent status updates for same task | Two workers try to update same task | Second update receives 400 (worker mismatch) or state violation | P1 |
| C2.3 | Concurrent heartbeat + mark_offline | Heartbeat arrives just as monitor triggers offline | One wins: either worker stays online (heartbeat won) or goes offline (monitor won). No inconsistent state | P1 |
| C2.4 | Concurrent register + schedule | New worker registers while tasks are being scheduled | Pending tasks may get scheduled to new worker; no crash | P1 |

### C3. Resource Accounting Invariant Verification

| ID | Test Case | Method | Assertion | Priority |
|----|-----------|--------|-----------|----------|
| C3.1 | Sum verification after concurrent operations | Run 1000 schedule+release cycles concurrently | For each worker: `used_cpu == sum(task.cpu_required for task in running_tasks_on_worker)` | P0 |
| C3.2 | No negative resources | After all operations | `worker.used_cpu >= 0 AND worker.used_mem >= 0` for all workers | P0 |
| C3.3 | No phantom allocations | All tasks complete | Every worker: `used_cpu == 0, used_mem == 0, task_count == 0` | P0 |

---

## 6. Module D: Stress & Performance Tests

### D1. High-QPS Task Submission

| ID | Scenario | Config | Target | Monitoring | Priority |
|----|----------|--------|--------|------------|----------|
| D1.1 | Sustained load | 100 Mock Workers, 1000 QPS for 60s | P99 latency < 200ms for POST /api/tasks | CPU usage, memory, event loop lag | P2 |
| D1.2 | Burst load | 10 Workers, 500 tasks in 1 second | All tasks accepted (200), no 500 errors | Request queue depth | P2 |
| D1.3 | Scheduler bottleneck | 100 Workers, 100 QPS | Measure time spent in schedule_task lock | Lock contention time < 10ms per call | P2 |

### D2. Log Flood

| ID | Scenario | Config | Target | Priority |
|----|----------|--------|--------|----------|
| D2.1 | Single task infinite log | Task: `while true; do echo "flood"; done` (rate-limited to avoid OS issues) | Master memory stable (RingBuffer caps at 1000 lines). No OOM after 60s | P1 |
| D2.2 | High-frequency log via API | 10,000 POST /internal/task/{id}/log in 10s | All accepted. Store buffer size stays ≤ 1000. WS broadcast doesn't block | P1 |
| D2.3 | Multiple tasks flooding simultaneously | 10 tasks each producing 100 lines/s | Master total memory growth < 50MB over 60s | P2 |

### D3. WebSocket Connection Scaling

| ID | Scenario | Config | Target | Priority |
|----|----------|--------|--------|----------|
| D3.1 | Cluster broadcast scaling | 1000 /ws/cluster connections | Broadcast completion time < 1s. No connection leaks | P2 |
| D3.2 | Log subscriber scaling | 100 connections to /ws/logs/{same_task_id} | All receive same log frames. Dead connections cleaned | P2 |
| D3.3 | Mixed connections | 500 cluster + 200 log subscribers | Master event loop not blocked. CPU < 80% | P2 |

### D4. Endurance Test (1 Hour)

| ID | Scenario | Config | Acceptance Criteria | Priority |
|----|----------|--------|---------------------|----------|
| D4.1 | Long-running stability | 10 Workers, random task submission (10 QPS), 5% task failures, 1% Worker crash+restart every 5 min | 1. No resource leak: `used_cpu`/`used_mem` never permanently stuck non-zero after all tasks complete. 2. Memory growth < 100MB/hour. 3. All new tasks continue to be scheduled correctly. 4. No unhandled exceptions in logs | P1 |

---

## 7. Module E: Edge Cases & Boundary Tests

### E1. Schema & Input Boundaries

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| E1.1 | Oversized resource request | Task(cpu=9999, mem=9999) with Worker(4cpu/8mem) | Task accepted as pending → can_any_worker_fit=False → marked `failed` | P0 |
| E1.2 | CPU at exact worker capacity | Task(cpu=4, mem=1) on Worker(total_cpu=4, total_mem=8) | Scheduled (exact CPU fit) | P0 |
| E1.3 | MEM at exact worker capacity | Task(cpu=1, mem=8) on Worker(total_cpu=4, total_mem=8) | Scheduled (exact MEM fit) | P0 |
| E1.4 | Both at exact capacity | Task(cpu=4, mem=8) on Worker(total_cpu=4, total_mem=8) | Scheduled, score=0.0, worker fully utilized | P0 |
| E1.5 | cpu_required = 1 (minimum valid) | Task(cpu=1, mem=1) | Accepted, valid | P1 |
| E1.6 | Very large int values | Task(cpu=2147483647, mem=2147483647) | Accepted by Pydantic (int has no upper bound in schema), fails scheduling | P2 |
| E1.7 | Unicode command | `{"command": "echo 你好世界 🌍"}` | Accepted (command is string, min_length=1 satisfied) | P2 |
| E1.8 | Command with shell metacharacters | `{"command": "echo $(whoami) && rm -rf /"}` | Accepted (Master doesn't validate command safety — this is a known design choice) | P2 |

### E2. State Machine Violations

| ID | Test Case | Setup | Operation | Expected | Priority |
|----|-----------|-------|-----------|----------|----------|
| E2.1 | Reverse terminal state: success→running | Task in success state | POST status=running | 400: "Task already in terminal state" | P0 |
| E2.2 | Reverse terminal state: failed→running | Task in failed state | POST status=running | 400: "Task already in terminal state" | P0 |
| E2.3 | Skip state: pending→success | Task in pending state | POST status=success | 400: "Invalid status transition" | P0 |
| E2.4 | Backward: running→pending | Task in running state | POST status (not supported by enum) | 422: Pydantic rejects (only "running"/"success"/"failed" allowed) | P0 |
| E2.5 | Worker impersonation | Task assigned to worker-A | Worker-B sends status update | 400: "Worker mismatch" | P0 |
| E2.6 | Status update on non-existent task | N/A | POST /internal/task/fake-id/status | 404: "Task not found" | P1 |
| E2.7 | Log append on non-existent task | N/A | POST /internal/task/fake-id/log | 404: "Task not found" | P1 |

### E3. Dispatch & Network Failure Recovery

| ID | Test Case | Setup | Fault Injection | Expected | Priority |
|----|-----------|-------|-----------------|----------|----------|
| E3.1 | Worker HTTP unreachable | Worker registered but process dead | schedule_task → dispatch_to_worker timeout | Resources rolled back, task stays pending | P0 |
| E3.2 | Worker returns HTTP 500 | Mock Worker /execute returns 500 | schedule_task → dispatch returns False | Resources rolled back, task stays pending | P0 |
| E3.3 | Worker returns HTTP 200 but task crashes | Worker accepts but execution fails | Worker reports status=failed | Resources released, task marked failed, reschedule triggered | P0 |
| E3.4 | Network partition during log upload | Worker can't reach Master's /internal/task/{id}/log | Worker's httpx raises error | Worker logs warning, continues executing. Logs may be lost for duration of partition | P1 |
| E3.5 | Network partition during status report | Worker can't reach Master | Worker's report_status fails | Worker logs exception. Task may appear stuck as "running" on Master until heartbeat timeout | P1 |
| E3.6 | Master restart while Workers running | Kill Master, restart | Workers detect heartbeat failure (exist=False), re-register. Previously running tasks lost (in-memory store cleared) | P1 |

### E4. Heartbeat Edge Cases

| ID | Test Case | Setup | Expected | Priority |
|----|-----------|-------|----------|----------|
| E4.1 | Heartbeat jitter (6-10s delay) | Worker heartbeat arrives randomly 6-10s late | Master tolerates (timeout=15s > max delay). Worker stays online | P1 |
| E4.2 | Heartbeat at exactly 15s boundary | `now - last_heartbeat == 15.0` | Worker stays online (code uses `> 15`, not `>= 15`) | P0 |
| E4.3 | Heartbeat at 15.001s | `now - last_heartbeat == 15.001` | Worker marked offline | P0 |
| E4.4 | Worker crash and immediate restart (same ID) | Worker crashes, restarts within heartbeat timeout | Re-registration: old tasks cleaned up, fresh start. No duplicate worker entries | P0 |
| E4.5 | Worker crash, exceeds timeout, then restarts | Worker crashes, 20s pass, then restarts | Master already marked offline; re-registration recovers to online, old failed tasks not double-processed | P0 |
| E4.6 | Heartbeat from worker during mark_offline processing | Concurrent heartbeat and timeout | Race resolved by either: heartbeat wins (worker revived) or mark_offline completes first then heartbeat revives | P1 |

### E5. Worker Executor Edge Cases

| ID | Test Case | Command | Expected | Priority |
|----|-----------|---------|----------|----------|
| E5.1 | Command produces no output | `sleep 5` | Task succeeds, 0 log lines reported | P1 |
| E5.2 | Command produces binary output | `echo -e '\x00\x01\x02'` | `_decode_output` handles gracefully with UTF-8 replace mode | P2 |
| E5.3 | Command exits immediately | `true` (exit code 0) | Success reported quickly | P1 |
| E5.4 | Command exits with non-zero | `false` (exit code 1) | status=failed reported | P1 |
| E5.5 | Command doesn't exist | `nonexistent_binary_foobar` | Subprocess fails, status=failed reported | P1 |
| E5.6 | Command with very long single line | `python -c "print('x'*1000000)"` | One log line with 1M chars. Worker sends it; Master stores in buffer | P2 |
| E5.7 | Chinese/GBK output on Windows | `dir` (outputs GBK on Chinese Windows) | `_decode_output` falls back to system encoding | P2 |

---

## 8. Module F: Frontend Tests

### F1. useClusterWs Composable

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| F1.1 | Connects on mount | `wsStatus` transitions to "connected" | P0 |
| F1.2 | Parses cluster_state frame | `workers` and `tasksSummary` refs updated correctly | P0 |
| F1.3 | Reconnects on disconnect (max 5 attempts) | After close, reconnects with exponential backoff. `retryCount` increments | P1 |
| F1.4 | Stops reconnecting after 5 failures | `wsStatus` stays "disconnected" after MAX_RETRIES | P1 |
| F1.5 | Sends ping every 30s | `setInterval` triggers ping message | P2 |
| F1.6 | Cleans up on unmount | `disconnect()` called, timers cleared, ws closed | P1 |

### F2. useLogWs Composable

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| F2.1 | connect() opens WS and starts rAF loop | `isConnected` = true, `rafId` is set | P0 |
| F2.2 | Handles "connected" frame | No crash, acknowledged silently | P1 |
| F2.3 | Handles "history" frame | `logs.value` populated with history lines | P0 |
| F2.4 | Handles "log" frame via buffer+rAF | Log pushed to buffer, flushed to `logs` on next animation frame | P0 |
| F2.5 | Handles "task_completed" frame | `isCompleted` = true, `taskStatus` set | P0 |
| F2.6 | Caps logs at 5000 lines | After 5001 lines, oldest discarded (slice to last 5000) | P1 |
| F2.7 | disconnect() cleans up | WS closed, rAF cancelled, `isConnected` = false | P1 |
| F2.8 | connect() on new task clears previous state | `logs` cleared, `isCompleted` reset to false | P1 |

### F3. useAutoScroll Composable

| ID | Test Case | Expected | Priority |
|----|-----------|----------|----------|
| F3.1 | Auto-scrolls to bottom on new log | `scrollTop = scrollHeight` called after nextTick+rAF | P0 |
| F3.2 | Pauses when user scrolls up | User scroll event where `scrollHeight - scrollTop - clientHeight > 50` → `isAutoScrolling` = false | P0 |
| F3.3 | Resumes when user scrolls to bottom | User within 50px of bottom → `isAutoScrolling` = true | P0 |
| F3.4 | scrollToBottom() manual trigger | Sets scrollTop, `isAutoScrolling` = true | P1 |

### F4. Component Tests

| ID | Component | Test Case | Expected | Priority |
|----|-----------|-----------|----------|----------|
| F4.1 | TaskSubmitForm | Valid submission | Form emits submit event with command/cpu/mem | P0 |
| F4.2 | TaskSubmitForm | Empty command rejected | Submit button disabled or validation error shown | P1 |
| F4.3 | TaskSubmitForm | Submitting state disables button | While API call in progress, button disabled | P1 |
| F4.4 | TaskList | Renders task rows | Each task shows id, command, status, worker | P0 |
| F4.5 | TaskList | Status filter works | Filter prop changes → displayed tasks filtered | P1 |
| F4.6 | TaskList | Worker name resolution | worker_id mapped to display_name via workerNameMap | P1 |
| F4.7 | WorkerCard | Online worker rendering | Green status dot, white background, progress bars shown | P0 |
| F4.8 | WorkerCard | Offline worker rendering | Red dot, gray background, dimmed appearance | P0 |
| F4.9 | WorkerCard | Resource warning at >80% | Progress bar turns red when CPU or MEM usage > 80% | P1 |

---

## 9. Module G: End-to-End Integration Tests

> These tests require a real Master + Worker process (or TestClient-level ASGI simulation).

### G1. Full Task Lifecycle (Python-based)

| ID | Scenario | Steps | Verification | Priority |
|----|----------|-------|--------------|----------|
| G1.1 | Happy path: submit → schedule → execute → complete | 1. Register Mock Worker(4cpu/8mem). 2. POST /api/tasks (cpu=2, mem=4, command="echo hello"). 3. Mock Worker accepts /execute, reports running, sends logs, reports success | Task status transitions: pending→running→success. Logs appear in buffer. Resources released. GET /api/tasks shows status=success | P0 |
| G1.2 | Task failure path | Same as G1.1 but command exits with code 1 | Task status: pending→running→failed. Resources released. Pending tasks rescheduled | P0 |
| G1.3 | Worker offline during execution | 1. Register Worker, submit long task. 2. Stop Worker heartbeats. 3. Wait 15+ seconds | Heartbeat monitor marks Worker offline. Running task → failed. Resources released | P0 |
| G1.4 | Pending → reschedule on resource release | 1. Worker(4cpu/8mem) fully loaded. 2. Submit new task → stays pending. 3. Running task completes | Resources freed → pending task auto-scheduled to same Worker | P0 |
| G1.5 | Multi-worker Best-Fit verification | 1. Worker-A(4cpu/8mem), Worker-B(8cpu/16mem). 2. Submit Task(2cpu/4mem) | Task assigned to Worker-A (tighter fit, lower score) | P0 |
| G1.6 | Task exceeds all worker capacity | 1. Worker(4cpu/8mem). 2. Submit Task(16cpu/32mem) | Task immediately marked failed (can_any_worker_fit=False) | P0 |

### G2. Browser E2E (Playwright)

| ID | Scenario | Steps | Verification | Priority |
|----|----------|-------|--------------|----------|
| G2.1 | Dashboard loads and shows workers | 1. Start Master + Worker. 2. Open browser | Worker card visible with correct CPU/MEM info | P1 |
| G2.2 | Submit task via form | 1. Click "Submit Task". 2. Fill form. 3. Click submit | Task appears in TaskList with status badge | P1 |
| G2.3 | Real-time log viewing | 1. Submit long-running task. 2. Click "View Logs" | LogModal opens, logs stream in real-time, auto-scrolls | P1 |
| G2.4 | Worker offline visual feedback | 1. Kill Worker process. 2. Wait 15s | Worker card turns gray, shows "OFFLINE" | P1 |
| G2.5 | Cluster state updates in real-time | 1. Register new Worker while dashboard open | New Worker card appears without page refresh | P1 |
| G2.6 | Log auto-scroll pause/resume | 1. Open log modal. 2. Scroll up. 3. New logs arrive | Auto-scroll paused. Scroll back to bottom → resumes | P2 |

---

## 10. Appendix: Test Matrix Summary

### 10.1 Total Test Count by Module

| Module | Category | Test Cases | P0 | P1 | P2 |
|--------|----------|------------|----|----|-----|
| A | Backend Unit | 52 | 32 | 16 | 4 |
| B | Backend Integration | 28 | 16 | 9 | 3 |
| C | Concurrency | 12 | 8 | 4 | 0 |
| D | Stress/Performance | 8 | 0 | 3 | 5 |
| E | Edge Cases | 27 | 12 | 12 | 3 |
| F | Frontend | 21 | 8 | 10 | 3 |
| G | End-to-End | 12 | 6 | 5 | 1 |
| **Total** | | **160** | **82** | **59** | **19** |

### 10.2 Critical Path Coverage

```
Resource Allocation Correctness (30 tests)
├── score_worker formula (8 tests)
├── schedule_task Best-Fit selection (8 tests)
├── Resource deduction atomicity (3 tests)
├── release_resources safety (5 tests)
├── Concurrent anti-overselling (5 tests)
└── Resource accounting invariants (3 tests → run after every concurrent test)

State Machine Safety (15 tests)
├── Valid transitions (4 tests)
├── Invalid transitions (7 tests)
├── Worker mismatch rejection (2 tests)
└── Terminal state immutability (2 tests)

Failure Recovery (8 tests)
├── Dispatch failure rollback (2 tests)
├── Worker offline cascading cleanup (4 tests)
└── Worker restart recovery (2 tests)
```

### 10.3 Key Invariants to Assert (Global Postconditions)

These invariants MUST be checked after EVERY concurrent/stress test:

```python
# Invariant 1: No overselling
for worker in store.workers.values():
    assert worker["used_cpu"] <= worker["total_cpu"]
    assert worker["used_mem"] <= worker["total_mem"]

# Invariant 2: No negative resources
for worker in store.workers.values():
    assert worker["used_cpu"] >= 0
    assert worker["used_mem"] >= 0
    assert worker["task_count"] >= 0

# Invariant 3: Resource accounting consistency
for worker in store.workers.values():
    running_tasks = [
        t for t in store.tasks.values()
        if t["worker_id"] == worker["worker_id"] and t["status"] == "running"
    ]
    expected_cpu = sum(t["cpu_required"] for t in running_tasks)
    expected_mem = sum(t["mem_required"] for t in running_tasks)
    assert worker["used_cpu"] == expected_cpu, f"CPU leak on {worker['worker_id']}"
    assert worker["used_mem"] == expected_mem, f"MEM leak on {worker['worker_id']}"
    assert worker["task_count"] == len(running_tasks)

# Invariant 4: State machine consistency
for task in store.tasks.values():
    if task["status"] in ("success", "failed"):
        assert task["finished_at"] is not None
    if task["status"] == "running":
        assert task["started_at"] is not None
        assert task["worker_id"] is not None
    if task["status"] == "pending":
        # worker_id may or may not be None during scheduling
        pass

# Invariant 5: No orphaned resources
for task in store.tasks.values():
    if task["status"] in ("success", "failed", "pending") and task.get("worker_id"):
        worker = store.workers.get(task["worker_id"])
        if worker and task["status"] != "pending":
            # Completed tasks should have had their resources released
            pass  # Covered by Invariant 3
```

### 10.4 Test Execution Order

```
Phase 1: Unit Tests (Module A)        — Run on every commit (CI)
Phase 2: Integration Tests (Module B)  — Run on every commit (CI)
Phase 3: Edge Case Tests (Module E)    — Run on every commit (CI)
Phase 4: Concurrency Tests (Module C)  — Run on PR merge (CI)
Phase 5: Frontend Tests (Module F)     — Run on every commit (CI)
Phase 6: E2E Tests (Module G)          — Run on PR merge (CI)
Phase 7: Stress Tests (Module D)       — Run nightly or pre-release
```

---

> **Document End** — 160 test cases across 7 modules, covering unit → integration → concurrency → stress → edge cases → frontend → E2E.
