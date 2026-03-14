# Mini-Scheduler 分布式任务调度系统 - 全面测试计划

## 1. 测试概述
本项目为一个轻量级的分布式任务调度系统（单 Master + 多 Worker），包含自定义的 Best-Fit Bin Packing 二维资源调度算法、实时基于 WebSocket 的心跳与日志推送机制。为了保证系统在极端条件下的高可用性与资源分配的严格正确性，本测试计划涵盖了功能测试、边界测试、并发测试以及压力测试。

---

## 2. 测试环境与工具准备
*   **负载生成工具**：`locust` 或 `k6`（用于高并发 API 压测与 WebSocket 订阅压测）。
*   **网络模拟工具**：`toxiproxy` 或 `tc` (Linux Traffic Control)（用于模拟网络延迟、丢包、断网等极端心跳情况）。
*   **模拟测试脚本**：编写基于 `httpx` 和 `websockets` 的异步 Python 测试脚本。
*   **Mock Worker**：定制化 Mock Worker，能自由控制响应延迟、故意上报错误状态、或触发 OOM/Crash。

---

## 3. Bin Packing 算法专项测试 (严格资源验证)

### 3.1 二维资源最佳适配 (Best-Fit) 验证
*   **场景 1：精准匹配**
    *   **设置**：Worker-A (4核/8G), Worker-B (2核/4G)。
    *   **操作**：提交一个需 2核/4G 的任务。
    *   **预期**：严格分配给 Worker-B（剩余资源完全耗尽，Score为 0，比 Worker-A 的剩余得分更小）。
*   **场景 2：碎片最小化**
    *   **设置**：Worker-A (剩余 3核/6G), Worker-B (剩余 4核/8G)。
    *   **操作**：提交需 2核/4G 的任务。
    *   **预期**：分配给 Worker-A，因为 (3-2)/总 + (6-4)/总 的分数低于 Worker-B。
*   **场景 3：单维度匮乏**
    *   **设置**：Worker-A (8核/2G)。
    *   **操作**：提交需 2核/4G 的任务。
    *   **预期**：尽管 CPU 充裕，但内存不足，拒绝分配给 Worker-A，任务应保持 `pending`。

### 3.2 资源并发超卖防范 (高并发调度测试)
*   **场景**：验证 `asyncio.Lock` 在调度循环中的严格性。
*   **设置**：仅启动一个 Worker (4核/8G)。
*   **操作**：使用异步脚本在 10 毫秒内并发提交 **10 个** 需 2核/4G 的任务。
*   **预期**：
    *   系统只能将 **2 个** 任务状态变更为 `running` 并分配到该 Worker。
    *   其余 8 个任务必须保持 `pending` 状态，`used_cpu` 严格等于 4，`used_mem` 严格等于 8，绝对不能出现超过总容量的超分配（超卖）。

### 3.3 资源回收与重调度 (Reschedule)
*   **场景 1：任务正常结束回收**
    *   **操作**：Worker 满载，任务队列有 `pending` 任务。当运行中的任务成功结束 (`status=success`)。
    *   **预期**：资源原子释放，并立即触发重调度，`pending` 任务状态变更为 `running`。
*   **场景 2：Worker 下线异常回收**
    *   **操作**：强杀满载的 Worker 进程。
    *   **预期**：15秒后 Master 标记 Worker 为 `offline`，将运行中的任务置为 `failed`，并释放该 Worker 的虚拟资源占用。

---

## 4. 边界情况测试 (Edge Cases)

### 4.1 Schema 与 API 边界输入
*   **超大请求**：提交 `cpu_required = 9999` 或 `mem_required = 9999` 的任务。
    *   **预期**：请求合法，被 Master 接收为 `pending`，但 `try_reschedule_pending` 中的 `can_any_worker_fit` 检测到所有注册节点都无法满足，任务直接标记为 `failed`。
*   **非法数值**：`cpu_required = 0` 或 `mem_required = -1`。
    *   **预期**：Pydantic Schema (Field `ge=1`) 直接在 Router 层拦截，返回 400 错误。
*   **非法状态流转**：Worker 尝试恶意调用 POST `/internal/task/{id}/status`，将 `success` 状态改为 `running`。
    *   **预期**：触发 `TaskService.update_status` 中的防误改逻辑，抛出 `ValueError: Task already in terminal state`。
*   **身份伪造**：Worker B 尝试更新分配给 Worker A 的任务状态。
    *   **预期**：触发 `Worker mismatch for task status report`，拒绝更新。

### 4.2 调度回调失败 (Dispatch Failure)
*   **场景**：Master 在调度锁内扣减了资源，但在调用 `dispatch_to_worker` 时，Worker HTTP 接口超时或返回 500。
*   **预期**：`scheduler.py` 捕获失败，重新获取锁，执行资源回滚（回滚 `used_cpu`, `used_mem`, `task_count`），并将任务重置为 `pending`。

---

## 5. 极端与异常场景测试 (Extreme Scenarios)

### 5.1 日志洪峰压测 (Log Flood)
*   **背景**：Worker 每秒产生上千行 `stdout`。
*   **操作**：提交一个 `while true; do echo "flood"; done` 的恶意任务。
*   **预期**：
    *   **Worker 端**：能够持续发送日志而不 OOM（可能因为 HTTP 延迟堆积，需观察 Worker 内存）。
    *   **Master 端**：`store.get_or_create_log_buffer` 使用了 `maxlen=1000` 的 `collections.deque`，内存应保持稳定。
    *   **前端 / WebSocket**：大量 `LogLineFrame` 广播。慢客户端可能导致积压，Master 会在发送异常时触发 `try...except` 并主动切断死连接 (`dead_connections` 逻辑)。

### 5.2 心跳监控边界 (Heartbeat Boundaries)
*   **场景 1：网络抖动 (Jitter)**
    *   **操作**：使用工具让 Worker 的 `/internal/heartbeat` 随机延迟 6-10 秒到达。
    *   **预期**：由于 `HEARTBEAT_TIMEOUT` 设为 15 秒（3倍于发送间隔 5s），Master 应容忍此类抖动，不触发 `offline`。
*   **场景 2：Worker 重启 (重复注册)**
    *   **操作**：Worker 崩溃，此时 Master 尚未超时。Worker 立即以相同的 `worker_id` 重启并调用 `/internal/register`。
    *   **预期**：Master 清理该 Worker ID 名下之前的 `pending`/`running` 任务（置为 `failed`），并将 Worker 的 `used_cpu`/`used_mem` 清零，恢复为全新的 `online` 状态。

### 5.3 慢速 WebSocket 客户端 (Slow Client)
*   **操作**：使用脚本建立对 `/ws/logs/{task_id}` 的订阅，但不读取底层 TCP 缓冲区，故意制造反压 (Backpressure)。
*   **预期**：Uvicorn/FastAPI 会在发送缓冲区满后抛出异常，Master 代码的 `broadcast_log` 中的 `try...except` 应当捕获该异常，并将该 WebSocket 加入 `dead_connections` 丢弃，而**不会阻塞**其他正常客户端的日志推送，也**不会阻塞**主事件循环。

---

## 6. 性能与压力测试 (Stress & Load Tests)

### 6.1 高并发任务调度吞吐量
*   **设置**：集群包含 100 个模拟 Worker（仅注册不实际执行子进程，Mock `/execute` 接口返回 200）。
*   **操作**：通过 Load Generator 持续以 1000 QPS 提交轻量任务（1核/1G）。
*   **监控指标**：
    *   Master API 的 99th 百分位响应时间 (P99 Latency)。
    *   Master 的 CPU 占用率（`SchedulerService` 为 CPU 密集型的遍历算分，需验证 100 个 Worker 的遍历在单线程下的耗时是否成为瓶颈）。
    *   是否存在请求堆积导致 Uvicorn 报错。

### 6.2 大规模 WebSocket 集群广播压力
*   **设置**：Master 运行，建立 5000 个前端客户端连接到 `/ws/cluster`。
*   **操作**：Master 每秒触发一次 `broadcast_cluster_state`。
*   **监控指标**：
    *   Master 的内存占用，验证是否存在 WebSocket 对象泄露。
    *   Master 广播一次完整帧的总耗时。由于是循环 `await websocket.send_json()`，需验证在 5000 客户端时，广播耗时是否超过了发送间隔（1秒），若超过需考虑改进为 `asyncio.gather` 并发发送。

---

## 7. 持续压测与稳定性测试 (1小时)
*   **高负载稳定性压测 (1小时)**：
    *   保持系统运行 1 小时，高并发不间断地提交不同资源大小、不同耗时的随机任务。
    *   同时设定 5% 的任务会随机报错退出，1% 的 Worker 会随机崩溃重启。
    *   **验收标准**：
        1.  `store.workers` 中的 `used_cpu` 和 `used_mem` 没有出现负数或永远不归零的"泄漏"现象。
        2.  Python 进程无明显的 Memory Leak（内存平稳）。
        3.  系统始终能正确完成新的任务调度。