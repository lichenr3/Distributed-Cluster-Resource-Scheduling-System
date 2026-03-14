import axios from 'axios'
import type {
  ApiResponse,
  TaskInfo,
  TaskListData,
  TaskSubmitPayload,
  WorkerListData,
} from '@/types'

const api = axios.create({
  baseURL: '',          // proxied via vite dev server
  timeout: 10_000,
})

// ── Tasks ──

export function submitTask(payload: TaskSubmitPayload) {
  return api.post<ApiResponse<TaskInfo>>('/api/tasks', payload)
}

export function getTasks(status?: string) {
  return api.get<ApiResponse<TaskListData>>('/api/tasks', {
    params: status ? { status } : undefined,
  })
}

export function getTask(taskId: string) {
  return api.get<ApiResponse<TaskInfo>>(`/api/tasks/${taskId}`)
}

// ── Workers ──

export function getWorkers() {
  return api.get<ApiResponse<WorkerListData>>('/api/workers')
}

export default api
