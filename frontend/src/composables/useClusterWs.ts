import { ref, onMounted, onUnmounted } from 'vue'
import type { WorkerInfo, TasksSummary, ClusterStateFrame } from '@/types'

/**
 * Maintains a WebSocket connection to /ws/cluster.
 * Provides reactive `workers` and `tasksSummary` updated every ~1 s.
 * Auto-reconnects with exponential back-off (max 5 attempts).
 */
export function useClusterWs() {
  const workers = ref<WorkerInfo[]>([])
  const tasksSummary = ref<TasksSummary>({
    pending: 0,
    running: 0,
    success: 0,
    failed: 0,
    total: 0,
  })
  const wsStatus = ref<'connecting' | 'connected' | 'disconnected'>('disconnected')

  let ws: WebSocket | null = null
  let retryCount = 0
  let retryTimer: ReturnType<typeof setTimeout> | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null
  const MAX_RETRIES = 5

  function getWsUrl(): string {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${proto}://${location.host}/ws/cluster`
  }

  function connect() {
    if (ws) return
    wsStatus.value = 'connecting'

    ws = new WebSocket(getWsUrl())

    ws.onopen = () => {
      wsStatus.value = 'connected'
      retryCount = 0
      // Send ping every 30 s to keep alive
      pingTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30_000)
    }

    ws.onmessage = (event: MessageEvent) => {
      const frame = JSON.parse(event.data as string) as ClusterStateFrame
      if (frame.type === 'cluster_state') {
        workers.value = frame.data.workers
        tasksSummary.value = frame.data.tasks_summary
      }
    }

    ws.onclose = () => {
      cleanup()
      wsStatus.value = 'disconnected'
      scheduleReconnect()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function cleanup() {
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
    ws = null
  }

  function scheduleReconnect() {
    if (retryCount >= MAX_RETRIES) return
    const delay = Math.min(1000 * 2 ** retryCount, 16_000)
    retryCount++
    retryTimer = setTimeout(connect, delay)
  }

  function disconnect() {
    if (retryTimer) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
    retryCount = MAX_RETRIES // prevent reconnect
    if (ws) {
      ws.close()
      cleanup()
    }
    wsStatus.value = 'disconnected'
  }

  onMounted(connect)
  onUnmounted(disconnect)

  return { workers, tasksSummary, wsStatus, connect, disconnect }
}
