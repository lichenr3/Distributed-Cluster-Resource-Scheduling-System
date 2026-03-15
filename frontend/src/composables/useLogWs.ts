import { ref } from 'vue'
import type { LogLine, LogWsFrame } from '@/types'

const MAX_LOG_LINES = 1000

/**
 * On-demand WebSocket connection to /ws/logs/{task_id}.
 * Call `connect(taskId)` when the log modal opens, `disconnect()` when it closes.
 */
export function useLogWs() {
  const logs = ref<LogLine[]>([])
  const isConnected = ref(false)
  const isCompleted = ref(false)
  const taskStatus = ref<string | null>(null)

  let ws: WebSocket | null = null

  function getWsUrl(taskId: string): string {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${proto}://${location.host}/ws/logs/${taskId}`
  }

  function connect(taskId: string) {
    disconnect()
    logs.value = []
    isCompleted.value = false
    taskStatus.value = null

    ws = new WebSocket(getWsUrl(taskId))

    ws.onopen = () => {
      isConnected.value = true
    }

    ws.onmessage = (event: MessageEvent) => {
      const frame = JSON.parse(event.data as string) as LogWsFrame
      handleFrame(frame)
    }

    ws.onclose = () => {
      isConnected.value = false
      ws = null
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function handleFrame(frame: LogWsFrame) {
    switch (frame.type) {
      case 'connected':
        // connection acknowledged
        break
      case 'history':
        logs.value = frame.lines.slice()
        break
      case 'log':
        logs.value.push({
          line_no: frame.line_no,
          content: frame.content,
          timestamp: frame.timestamp,
        })
        // Cap at MAX_LOG_LINES to prevent DOM explosion
        if (logs.value.length > MAX_LOG_LINES) {
          logs.value = logs.value.slice(-MAX_LOG_LINES)
        }
        break
      case 'task_completed':
        isCompleted.value = true
        taskStatus.value = frame.status
        break
    }
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
    isConnected.value = false
  }

  return { logs, isConnected, isCompleted, taskStatus, connect, disconnect }
}
