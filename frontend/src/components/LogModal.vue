<script setup lang="ts">
import { ref, watch } from 'vue'
import { useLogWs } from '@/composables/useLogWs'
import { useAutoScroll } from '@/composables/useAutoScroll'

const props = defineProps<{
  visible: boolean
  taskId: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
}>()

const logContainerRef = ref<HTMLElement | null>(null)
const { logs, isConnected, isCompleted, taskStatus, connect, disconnect } = useLogWs()
const { isAutoScrolling, onScroll, scrollToBottom } = useAutoScroll(logs, logContainerRef)

watch(
  () => props.visible,
  (val) => {
    if (val && props.taskId) {
      connect(props.taskId)
    } else {
      disconnect()
    }
  },
)

function handleClose() {
  emit('update:visible', false)
}

function formatTime(isoStr: string) {
  if (!isoStr) return ''
  const date = new Date(isoStr)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="terminal-overlay" @click.self="handleClose">
        <div class="terminal-window">
          <div class="terminal-header">
            <div class="header-left">
              <div class="status-dot" :class="{ connected: isConnected }"></div>
              <span class="task-id">{{ taskId }}</span>
              <span v-if="isCompleted && taskStatus" class="status-pill" :class="taskStatus">{{ taskStatus.toUpperCase() }}</span>
            </div>
            
            <div class="header-right">
              <button v-if="!isAutoScrolling" class="scroll-btn" @click="scrollToBottom">
                ↓ 回到底部
              </button>
              <span class="log-count">{{ logs.length }} LINES</span>
              <button class="close-btn" @click="handleClose">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>
          </div>

          <div ref="logContainerRef" class="terminal-content" @scroll="onScroll">
            <div v-for="line in logs" :key="line.line_no" class="log-line">
              <span class="timestamp">[{{ formatTime(line.timestamp) }}]</span>
              <span class="line-no">{{ line.line_no }}</span>
              <span class="line-content">{{ line.content }}</span>
            </div>
            <div v-if="logs.length === 0" class="log-empty">
              <span class="cursor">_</span> 等待日志输出...
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.terminal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.9);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4vh 5vw;
}

.terminal-window {
  width: 100%;
  height: 100%;
  background: #0a0a0a;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-subtle);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
}

.terminal-header {
  height: 48px;
  background: #111111;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
}

.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-failed-text);
}

.status-dot.connected {
  background: var(--status-success-text);
}

.task-id {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-primary);
}

.status-pill {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.05em;
}

.status-pill.success {
  background: var(--status-success-bg);
  color: var(--status-success-text);
}

.status-pill.failed {
  background: var(--status-failed-bg);
  color: var(--status-failed-text);
}

.scroll-btn {
  background: transparent;
  border: 1px solid var(--border-hover);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 4px 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.scroll-btn:hover {
  color: var(--text-primary);
  border-color: var(--text-primary);
}

.log-count {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
}

.close-btn {
  background: transparent;
  border: none;
  color: #555555;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s ease;
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

.close-btn:hover {
  color: #ffffff;
}

.terminal-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
}

/* Custom scrollbar for terminal */
.terminal-content::-webkit-scrollbar {
  width: 8px;
}
.terminal-content::-webkit-scrollbar-track {
  background: #222222;
}
.terminal-content::-webkit-scrollbar-thumb {
  background: #444444;
}
.terminal-content::-webkit-scrollbar-thumb:hover {
  background: #555555;
}

.log-line {
  display: flex;
  padding: 0 16px;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.02);
}

.timestamp {
  color: #555555;
  user-select: none;
  margin-right: 12px;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
}

.line-no {
  color: #333333;
  user-select: none;
  width: 48px;
  min-width: 48px;
  text-align: right;
  padding-right: 16px;
  font-variant-numeric: tabular-nums;
}

.line-content {
  color: #a0a0a0;
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}

.log-empty {
  color: #555555;
  padding: 32px 16px 32px 64px;
  letter-spacing: 0.05em;
}

.cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
