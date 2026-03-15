<script setup lang="ts">
import { computed } from 'vue'
import type { WorkerInfo } from '@/types'

const props = defineProps<{
  worker: WorkerInfo
}>()

const cpuPercent = computed(() =>
  props.worker.total_cpu ? Math.round((props.worker.used_cpu / props.worker.total_cpu) * 100) : 0,
)
const memPercent = computed(() =>
  props.worker.total_mem ? Math.round((props.worker.used_mem / props.worker.total_mem) * 100) : 0,
)

function formatTime(isoString: string) {
  if (!isoString) return 'Never'
  const date = new Date(isoString)
  return date.toLocaleTimeString([], { hour12: false })
}

function formatRes(val: number) {
  return Number.isInteger(val) ? val : Number(val.toFixed(2))
}
</script>

<template>
  <div :class="['worker-card', { 'worker-offline': worker.status === 'offline' }]">
    <div v-if="worker.status === 'offline'" class="offline-badge">离线</div>
    
    <div class="card-header">
      <span class="worker-name">{{ worker.display_name }}</span>
      <span class="status-pill" :class="worker.status">
        {{ worker.status.toUpperCase() }}
      </span>
    </div>

    <div class="resources">
      <div class="resource-row">
        <span class="label">CPU</span>
        <div class="bar-container">
          <div class="bar-fill" :style="{ width: `${cpuPercent}%` }"></div>
        </div>
        <span class="value">{{ formatRes(worker.used_cpu) }}/{{ worker.total_cpu }}</span>
      </div>
      
      <div class="resource-row">
        <span class="label">MEM</span>
        <div class="bar-container">
          <div class="bar-fill" :style="{ width: `${memPercent}%` }"></div>
        </div>
        <span class="value">{{ formatRes(worker.used_mem) }}/{{ worker.total_mem }}</span>
      </div>
    </div>

    <div class="meta">
      <div class="meta-item">
        <span class="meta-label">运行任务</span>
        <span class="meta-value">{{ worker.task_count }}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">心跳时间</span>
        <span class="meta-value">{{ formatTime(worker.last_heartbeat) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.worker-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  transition: all 0.2s ease;
}

.worker-card:hover {
  border-color: var(--border-hover);
  transform: translateY(-1px);
}

.worker-offline {
  opacity: 0.35;
}

.offline-badge {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.8);
  color: var(--text-primary);
  padding: 4px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.1em;
  z-index: 10;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.worker-name {
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 14px;
  color: var(--text-primary);
}

.status-pill {
  font-size: 10px;
  font-family: var(--font-mono);
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.05em;
}

.status-pill.online {
  background: var(--status-success-bg);
  color: var(--status-success-text);
}

.status-pill.offline {
  background: var(--status-failed-bg);
  color: var(--status-failed-text);
}

.resources {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.resource-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.label {
  width: 24px;
  font-size: 10px;
  color: var(--text-tertiary);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.bar-container {
  flex: 1;
  height: 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #555555, #cccccc);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.value {
  width: 50px;
  min-width: 50px;
  text-align: right;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.meta {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--border-subtle);
  padding-top: 12px;
  margin-top: auto;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 9px;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
  font-weight: 600;
}

.meta-value {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
</style>
