// ── Task ──

export type TaskStatus = 'pending' | 'running' | 'success' | 'failed'

export interface TaskInfo {
  task_id: string
  command: string
  cpu_required: number
  mem_required: number
  status: TaskStatus
  worker_id: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface TaskSubmitPayload {
  task_id?: string
  command: string
  cpu_required: number
  mem_required: number
}

// ── Worker ──

export type WorkerStatus = 'online' | 'offline'

export interface WorkerInfo {
  worker_id: string
  display_name: string
  host: string
  port: number
  total_cpu: number
  total_mem: number
  used_cpu: number
  used_mem: number
  status: WorkerStatus
  task_count: number
  last_heartbeat: string
  registered_at: string
}

// ── API Response ──

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface TaskListData {
  tasks: TaskInfo[]
  total: number
}

export interface WorkerListData {
  workers: WorkerInfo[]
  total: number
}

// ── WebSocket: /ws/cluster ──

export interface TasksSummary {
  pending: number
  running: number
  success: number
  failed: number
  total: number
}

export interface ClusterStateFrame {
  type: 'cluster_state'
  timestamp: string
  data: {
    workers: WorkerInfo[]
    tasks_summary: TasksSummary
  }
}

// ── WebSocket: /ws/logs/{task_id} ──

export interface LogLine {
  line_no: number
  content: string
  timestamp: string
}

export interface LogConnectedFrame {
  type: 'connected'
  task_id: string
  timestamp: string
}

export interface LogHistoryFrame {
  type: 'history'
  task_id: string
  lines: LogLine[]
}

export interface LogLineFrame {
  type: 'log'
  task_id: string
  line_no: number
  content: string
  timestamp: string
}

export interface TaskCompletedFrame {
  type: 'task_completed'
  task_id: string
  status: string
  exit_code: number | null
  timestamp: string
}

export type LogWsFrame =
  | LogConnectedFrame
  | LogHistoryFrame
  | LogLineFrame
  | TaskCompletedFrame
