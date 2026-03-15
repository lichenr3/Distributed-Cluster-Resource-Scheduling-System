import { ref } from 'vue'
import type { LogLine, LogWsFrame } from '@/types'

const MAX_LOG_LINES = 1000
const MAX_RETRIES = 3

/**
 * On-demand WebSocket connection to /ws/logs/{task_id}.
 * Call `connect(taskId)` when the log modal opens, `disconnect()` when it closes.
 * Auto-reconnects with exponential back-off (1s → 2s → 4s, max 3 attempts).
 * Existing logs are preserved across reconnects; history is de-duped by line_no.
 */
export function useLogWs() {
  const logs = ref<LogLine[]>([])
  const isConnected = ref(false)
  const isCompleted = ref(false)
  const taskStatus = ref<string | null>(null)

  let ws: WebSocket | null = null
  let currentTaskId: string | null = null
  let retryCount = 0
  let retryTimer: ReturnType<typeof setTimeout> | null = null
  let intentionalClose = false

  function getWsUrl(taskId: string): string {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${proto}://${location.host}/ws/logs/${taskId}`
  }

  function connect(taskId: string) {
    disconnect()
    logs.value = []
    isCompleted.value = false
    taskStatus.value = null
    retryCount = 0
    intentionalClose = false
    currentTaskId = taskId
    openSocket(taskId)
  }

  function openSocket(taskId: string) {
    ws = new WebSocket(getWsUrl(taskId))

    ws.onopen = () => {
      isConnected.value = true
      retryCount = 0
    }

    ws.onmessage = (event: MessageEvent) => {
      const frame = JSON.parse(event.data as string) as LogWsFrame
      handleFrame(frame)
    }

    ws.onclose = () => {
      isConnected.value = false
      ws = null
      if (!intentionalClose && !isCompleted.value) {
        scheduleReconnect()
      }
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function scheduleReconnect() {
    if (retryCount >= MAX_RETRIES || !currentTaskId) return
    const delay = 1000 * 2 ** retryCount
    retryCount++
    retryTimer = setTimeout(() => {
      if (currentTaskId) openSocket(currentTaskId)
    }, delay)
  }

  function handleFrame(frame: LogWsFrame) {
    switch (frame.type) {
      case 'connected':
        break
      case 'history': {
        const maxExisting = logs.value.length > 0
          ? Math.max(...logs.value.map(l => l.line_no))
          : -1
        const newLines = frame.lines.filter(l => l.line_no > maxExisting)
        if (logs.value.length === 0) {
          logs.value = frame.lines.slice()
        } else if (newLines.length > 0) {
          logs.value.push(...newLines)
        }
        break
      }
      case 'log':
        logs.value.push({
          line_no: frame.line_no,
          content: frame.content,
          timestamp: frame.timestamp,
        })
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
    intentionalClose = true
    if (retryTimer) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    isConnected.value = false
    currentTaskId = null
  }

  return { logs, isConnected, isCompleted, taskStatus, connect, disconnect }
}
