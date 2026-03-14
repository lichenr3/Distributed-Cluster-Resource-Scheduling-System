# Distributed Task Scheduler Architecture Knowledge Base

**Last Updated**: 2026-03-14
**Project**: Mini-Scheduler — 轻量级分布式任务调度系统 (Python FastAPI + Vue 3)
**Purpose**: Architecture knowledge base + design document index

---

## Project Documents

| 文档 | 路径 | 说明 |
|------|------|------|
| 需求原文提取 | `docs/requirement-pdf-extracted.md` | 睿思芯科AI挑战题 PDF 全文提取 |
| 需求分析文档 | `docs/需求分析文档.md` | 功能清单、难点、风险、MVP 范围 |
| 系统设计文档 | `docs/系统设计文档.md` | 架构、调度算法、通信、生命周期 |
| 接口契约文档 | `docs/接口契约文档.md` | REST/WS API、JSON 示例、字段命名 |
| 开发任务书 | `docs/开发任务书.md` | 前后端开发文档、任务拆分、里程碑 |

## Key Architecture Decisions

- **单 Master + 多 Worker**，纯 HTTP/WebSocket 通信，无 RPC
- **内存存储**（Dict），无数据库依赖，重启丢失可接受
- **Bin Packing**: Best-Fit 策略，二维资源评分（CPU + MEM 归一化），asyncio.Lock 保证原子调度
- **心跳**: Worker 每 5s HTTP POST 心跳，Master 每 5s 扫描，15s 超时标记 OFFLINE
- **日志流**: Worker → HTTP POST 逐行上报 → Master RingBuffer(1000行) → WebSocket 广播给前端
- **前端实时**: /ws/cluster 每秒全量推送集群状态；/ws/logs/{task_id} 即时推送日志
- **JSON 命名**: 前后端统一 snake_case 传输

## Current Progress

- [x] PDF 需求提取与分析
- [x] 需求分析文档
- [x] 系统设计文档
- [x] 接口契约文档
- [x] 开发任务书
- [x] Phase 1: 骨架搭建（后端）
- [x] Phase 2: 核心后端
- [x] Phase 3.0: 前端骨架搭建（Vite + Vue 3 + TS + Element Plus，types/api/composables/components/views 全部就位，build 通过）
- [ ] Phase 3: 核心前端（组件功能完善、样式打磨）
- [ ] Phase 4: 实时通信（后端 WebSocket 已就绪，前端 composables 骨架已写，待联调）
- [ ] Phase 5: 打磨联调

---

## 1. FastAPI Project Structure for Distributed Systems

### 1.1 Recommended Directory Layout

Based on production-ready FastAPI patterns from 2026. Master uses enterprise 3-layer architecture (Router / Service / Core) with standalone `schemas/` module as single source of truth for all API contracts.

```
distributed_task_scheduler/
├── backend/
│   ├── master/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI application entry, mount routers, register lifespan
│   │   │
│   │   ├── core/                      # Infrastructure layer
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # Configuration constants
│   │   │   ├── store.py               # In-memory storage (Dict + RingBuffer)
│   │   │   ├── events.py              # Startup/shutdown lifecycle events
│   │   │   └── dependencies.py        # FastAPI dependency injection
│   │   │
│   │   ├── schemas/                   # Data contract layer (Single Source of Truth)
│   │   │   ├── __init__.py
│   │   │   ├── task.py                # TaskSubmitRequest, TaskInfo, TaskStatusReport, TaskLogReport
│   │   │   ├── worker.py              # WorkerRegisterRequest, WorkerHeartbeatRequest, WorkerInfo
│   │   │   ├── response.py            # ApiResponse[T] generic wrapper
│   │   │   └── ws.py                  # WebSocket frame schemas
│   │   │
│   │   ├── routers/                   # Thin controller layer
│   │   │   ├── __init__.py
│   │   │   ├── tasks.py               # /api/tasks endpoints
│   │   │   ├── workers.py             # /api/workers endpoints
│   │   │   └── internal.py            # /internal/* worker communication
│   │   │
│   │   ├── services/                  # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── task_service.py        # Task CRUD + state transitions
│   │   │   ├── worker_service.py      # Worker registration + heartbeat
│   │   │   ├── scheduler.py           # Bin Packing (Best-Fit + asyncio.Lock)
│   │   │   └── heartbeat.py           # Background heartbeat monitor
│   │   │
│   │   └── ws/                        # WebSocket management
│   │       ├── __init__.py
│   │       ├── cluster.py             # /ws/cluster broadcast
│   │       └── logs.py                # /ws/logs/{task_id} streaming
│   │
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── main.py                    # Worker FastAPI entry + CLI args
│   │   ├── config.py                  # Worker configuration
│   │   ├── schemas.py                 # Worker-side Pydantic models
│   │   ├── executor.py                # Subprocess executor
│   │   └── reporter.py                # Master communication (register, heartbeat, log, status)
│   │
│   ├── requirements.txt
│   ├── run_master.py                  # Launch script: python run_master.py
│   └── run_worker.py                  # Launch script: python run_worker.py --port 8001 --cpu 4 --mem 8
│
├── frontend/                          # (unchanged — see 开发任务书.md 2.2)
│   └── ...
└── docs/
    └── ...
```

**Key Principles**:
- **3-layer Master architecture**: Router (thin) → Service (logic) → Core (infra), strict separation of concerns
- **Standalone schemas/**: Single source of truth for all Pydantic request/response models, shared by routers, services, and WS modules
- **Feature-based routing**: Separate routers for tasks, workers, internal communication
- **Service layer**: Isolate business logic from HTTP handlers; routers never touch store directly
- **Dependency injection**: `core/dependencies.py` provides service instances via FastAPI `Depends()`
- **Composables pattern**: Vue 3 reusable logic in `composables/` (frontend unchanged)

**Reference**: 
- [FastAPI Best Practices 2026](https://fastlaunchapi.dev/blog/fastapi-best-practices-production-2026)
- [Production-Ready FastAPI](https://oneuptime.com/blog/post/2026-01-27-fastapi-production/view)

---

## 2. Worker Heartbeat Protocol Design

### 2.1 HTTP Polling vs WebSocket Persistent Connection

**Research Findings**:

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **HTTP Polling** | Simple, stateless, works through firewalls | Higher latency (45-60s intervals), more bandwidth | Worker-to-Master heartbeats |
| **WebSocket** | Real-time (<1s), bidirectional, efficient | Requires connection management, firewall issues | Master-to-Frontend notifications |

**Recommended Architecture**: **Hybrid Approach**
- **Worker → Master**: HTTP POST heartbeats (simpler for worker crash recovery)
- **Master → Frontend**: WebSocket (real-time dashboard updates)

### 2.2 Heartbeat Implementation Pattern

**Evidence from FastChat** ([controller.py](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/serve/controller.py#L58-L61)):

```python
# Master: Background thread checks for stale workers
def heart_beat_controller(controller):
    while True:
        time.sleep(CONTROLLER_HEART_BEAT_EXPIRATION)  # 90 seconds
        controller.remove_stale_workers_by_expiration()
```

**Evidence from FastChat** ([base_model_worker.py](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/serve/base_model_worker.py#L21-L24)):

```python
# Worker: Background thread sends periodic heartbeats
def heart_beat_worker(obj):
    while True:
        time.sleep(WORKER_HEART_BEAT_INTERVAL)  # 45 seconds
        obj.send_heart_beat()
```

**Evidence from FastChat** ([constants.py](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/constants.py#L58-L61)):

```python
# Timeout Configuration
CONTROLLER_HEART_BEAT_EXPIRATION = int(
    os.getenv("FASTCHAT_CONTROLLER_HEART_BEAT_EXPIRATION", 90)
)
WORKER_HEART_BEAT_INTERVAL = int(os.getenv("FASTCHAT_WORKER_HEART_BEAT_INTERVAL", 45))
```

### 2.3 Heartbeat Interval & Timeout Thresholds

**Industry Standard Pattern** (from research):

```
HEARTBEAT_INTERVAL = 30-60 seconds       # Worker sends heartbeat
HEARTBEAT_TIMEOUT = 3 × INTERVAL         # Master marks worker offline
                  = 90-180 seconds
```

**Why 3x multiplier?**
- Tolerates 2 missed heartbeats (network hiccups)
- Balances false positives (premature offline detection) vs detection speed

**From Production Systems**:
- **FastChat**: 45s interval, 90s timeout (2x multiplier)
- **Dramatiq Redis**: 60s timeout
- **Dagster Cloud**: 120s timeout (hybrid agents), 900s (serverless)
- **Discord.py**: 60s max timeout with ping/pong frames

**Recommendation for Task Scheduler**:
```python
# Configuration
WORKER_HEARTBEAT_INTERVAL = 30   # seconds (worker sends)
MASTER_CHECK_INTERVAL = 30       # seconds (master checks)
HEARTBEAT_TIMEOUT = 90           # seconds (3x interval)
```

**Reference**:
- [Heartbeat Pattern in Distributed Systems](https://singhajit.com/distributed-systems/heartbeat)
- [WebSocket Ping-Pong Implementation](https://oneuptime.com/blog/post/2026-01-27-websocket-heartbeat-ping-pong/view)

---

## 3. Worker Registration Flow

### 3.1 Registration Data Structure

**Evidence from FastChat** ([base_model_worker.py#L89-L100](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/serve/base_model_worker.py#L89-L100)):

```python
def register_to_controller(self):
    url = self.controller_addr + "/register_worker"
    data = {
        "worker_name": self.worker_addr,        # Unique identifier (e.g., "http://worker1:8000")
        "check_heart_beat": True,               # Enable heartbeat monitoring
        "worker_status": self.get_status(),     # Initial status payload
        "multimodal": self.multimodal,          # Worker capabilities
    }
    r = requests.post(url, json=data)
```

**Worker Status Payload** ([base_model_worker.py#L145-L150](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/serve/base_model_worker.py#L145-L150)):

```python
def get_status(self):
    return {
        "model_names": self.model_names,        # Tasks this worker can handle
        "speed": 1,                             # Performance weight (for load balancing)
        "queue_length": self.get_queue_length() # Current workload
    }
```

### 3.2 Master-Side Worker Tracking

**Evidence from FastChat** ([controller.py#L48-L55](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/serve/controller.py#L48-L55)):

```python
@dataclasses.dataclass
class WorkerInfo:
    model_names: List[str]      # Worker capabilities
    speed: int                  # Performance weight
    queue_length: int           # Current load
    check_heart_beat: bool      # Monitoring enabled?
    last_heart_beat: str        # Timestamp of last heartbeat
    multimodal: bool            # Addi
