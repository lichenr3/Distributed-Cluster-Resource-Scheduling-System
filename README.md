# Mini-Scheduler — 轻量级分布式任务调度系统

一个基于 Master-Worker 架构的分布式任务调度系统，支持 Bin Packing 智能调度、实时资源监控和任务日志流。

## 核心功能

- **节点注册** — Worker 启动后自动向 Master 注册，上报 CPU 核数与内存
- **Bin Packing 调度** — Master 根据 Worker 剩余资源智能分配任务，支持资源切分
- **任务状态追踪** — Pending → Running → Success / Failed 全生命周期管理
- **集群资源热力图** — 卡片式展示各 Worker 实时 CPU / 内存占用率
- **任务日志流** — 点击运行中任务实时查看 stdout 输出，自动滚动到底部
- **离线感知** — Worker 心跳丢失时卡片标灰显示 OFFLINE

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 (Composition API) + TypeScript + Element Plus + Vite |
| 后端 | Python 3.13 + FastAPI + Uvicorn |
| 通信 | REST API + WebSocket (集群状态推送 & 日志流) |

## 系统架构

```
┌─────────────┐     REST / WS     ┌─────────────┐
│   Frontend   │ ◄──────────────► │   Master     │
│  Vue 3 SPA   │                  │  :8000       │
└─────────────┘                   └──────┬───────┘
                                    │  调度 & 心跳
                          ┌─────────┼─────────┐
                          ▼                   ▼
                   ┌─────────────┐     ┌─────────────┐
                   │  Worker-1   │     │  Worker-2   │
                   │  :8001      │     │  :8002      │
                   │  cpu=4 mem=8│     │  cpu=2 mem=4│
                   └─────────────┘     └─────────────┘
```

通信方向：

- **注册 / 心跳：** Worker → Master（Worker 主动发起，依赖 `--master-url`）
- **派发任务：** Master → Worker（Master 回调 Worker，依赖注册时记录的 `host:port`）

## 环境要求

- **Python** ≥ 3.13
- **Node.js** ≥ 20.19.0
- **uv** (Python 包管理器) — [安装指南](https://docs.astral.sh/uv/getting-started/installation/)

## 快速启动

### 方式一：一键启动 (Windows)

双击 `start.bat` 即可启动全部服务，脚本会自动检测并安装依赖。

启动内容：**1 个 Master + 2 个 Worker + 1 个前端开发服务器**

| 服务 | 端口 | CPU | 内存 |
|------|------|-----|------|
| Master | 8000 | — | — |
| Worker-1 | 8001 | 4 核 | 8 GB |
| Worker-2 | 8002 | 2 核 | 4 GB |
| Frontend | 5173 | — | — |

```bash
# 启动
start.bat

# 停止
stop.bat
```

### 方式二：手动启动

适用于所有操作系统（Windows / macOS / Linux），按顺序执行以下步骤。

**启动顺序：Master → Worker(s) → Frontend**，Master 必须先于 Worker 启动，前端随时可启。

**1. 安装依赖**

```bash
# 后端
cd backend
uv sync

# 前端
cd ../frontend
npm install
```

**2. 启动 Master（必须最先启动）**

```bash
cd backend
uv run python run_master.py
# Master 监听 http://0.0.0.0:8000

# 也可以自定义参数启动
uv run python run_master.py --port 9000 --heartbeat-timeout 20
```

Master 启动参数一览：

| 参数 | 说明 | 默认值 | 是否必填 |
|------|------|--------|----------|
| `--host` | 监听地址 | `0.0.0.0` | 可选 |
| `--port` | 监听端口 | `8000` | 可选 |
| `--heartbeat-interval` | 心跳扫描间隔（秒） | `5` | 可选 |
| `--heartbeat-timeout` | Worker 超时阈值（秒） | `15` | 可选 |
| `--broadcast-interval` | 集群状态广播间隔（秒） | `1` | 可选 |
| `--log-buffer-size` | 每任务日志缓冲行数 | `1000` | 可选 |

**3. 启动 Worker（新开终端，可启动任意数量）**

每个 Worker 需要指定端口、CPU 核数和内存大小：

```bash
cd backend

# Worker 1 — 4核 8G
uv run python run_worker.py --port 8001 --cpu 4 --mem 8

# Worker 2 — 2核 4G（新终端）
uv run python run_worker.py --port 8002 --cpu 2 --mem 4
```

Worker 启动后会自动向 Master 注册，无需额外配置。

Worker 启动参数一览：

| 参数 | 说明 | 默认值 | 是否必填 |
|------|------|--------|----------|
| `--port` | Worker 监听端口 | — | 必填 |
| `--cpu` | 声明的 CPU 核数 | — | 必填 |
| `--mem` | 声明的内存 (GB) | — | 必填 |
| `--master-url` | Master 的完整地址（含端口） | `http://localhost:8000` | 跨网址时必填 |
| `--host` | 手动指定 Worker 的回调 IP | `0.0.0.0` | 可选 |
| `--worker-id` | 自定义 Worker ID | 自动生成 | 可选 |

**4. 启动前端（新开终端）**

```bash
cd frontend
npm run dev
# 前端访问 http://localhost:5173
```

## 跨网址部署

当 Worker 和 Master 不在同一台机器时，通过 `--master-url` 指定 Master 的地址即可注册：

```bash
# Master 运行在 192.168.1.100:8000，Worker 在另一台机器上
uv run python run_worker.py \
  --port 8001 --cpu 4 --mem 8 \
  --master-url http://192.168.1.100:8000
```

**`--host` 的自动识别逻辑：**

Master 派发任务时需要回调 Worker，因此需要知道 Worker 的 IP 地址。这个地址按以下规则确定：

1. 如果 Worker 指定了 `--host`（如 `--host 192.168.1.200`），Master 直接使用该地址
2. 如果没有指定 `--host`（默认 `0.0.0.0`），Master 自动从注册请求的来源 IP 中提取 Worker 的真实地址

大多数情况下**不需要手动填写** `--host`。只有在网络环境复杂（多网卡、NAT、代理）导致自动识别的 IP 不正确时，才需要手动指定。

## 项目结构

```
├── backend/
│   ├── master/              # Master 节点
│   │   ├── core/            # 配置、状态存储、生命周期事件
│   │   ├── routers/         # REST API 路由
│   │   ├── schemas/         # Pydantic 数据模型
│   │   ├── services/        # 调度器 (Bin Packing)、心跳检测
│   │   └── ws/              # WebSocket 处理 (集群广播 & 日志流)
│   ├── worker/              # Worker 节点
│   ├── tests/               # 单元 / 集成 / 压力测试
│   ├── run_master.py        # Master 启动入口
│   ├── run_worker.py        # Worker 启动入口
│   └── pyproject.toml       # Python 依赖声明
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios API 封装
│   │   ├── components/      # Vue 组件 (WorkerCard, TaskList, LogModal 等)
│   │   ├── composables/     # 组合式函数 (useClusterWs, useLogWs, useAutoScroll)
│   │   ├── types/           # TypeScript 类型定义
│   │   └── views/           # 页面视图
│   └── package.json         # 前端依赖声明
├── docs/                    # 设计文档 (需求分析、系统设计、接口契约)
├── start.bat                # Windows 一键启动 (1 Master + 2 Workers + Frontend)
└── stop.bat                 # Windows 一键停止
```
