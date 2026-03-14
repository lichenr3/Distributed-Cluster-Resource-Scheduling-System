<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getTasks } from '@/api'
import type { TaskInfo } from '@/types'

const props = defineProps<{
  filter?: string
}>()

const emit = defineEmits<{
  (e: 'view-log', taskId: string): void
}>()

const tasks = ref<TaskInfo[]>([])
const loading = ref(false)

async function fetchTasks() {
  loading.value = true
  try {
    const { data } = await getTasks()
    tasks.value = data.data.tasks
  } finally {
    loading.value = false
  }
}

const filteredTasks = computed(() => {
  if (!props.filter || props.filter === 'ALL') {
    return tasks.value
  }
  return tasks.value.filter(t => t.status.toUpperCase() === props.filter)
})

onMounted(fetchTasks)

defineExpose({ fetchTasks })
</script>

<template>
  <div class="task-list-container" v-loading="loading" element-loading-background="rgba(10, 10, 10, 0.8)">
    <table class="custom-table">
      <thead>
        <tr>
          <th class="col-id">TASK ID</th>
          <th class="col-cmd">COMMAND</th>
          <th class="col-res">RESOURCES</th>
          <th class="col-status">STATUS</th>
          <th class="col-worker">WORKER</th>
          <th class="col-actions">ACTIONS</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="filteredTasks.length === 0">
          <td colspan="6" class="empty-row">NO TASKS FOUND</td>
        </tr>
        <tr v-for="row in filteredTasks" :key="row.task_id">
          <td class="col-id">
            <div class="truncate mono">{{ row.task_id }}</div>
          </td>
          <td class="col-cmd">
            <div class="truncate mono">{{ row.command }}</div>
          </td>
          <td class="col-res mono">C:{{ row.cpu_required }} M:{{ row.mem_required }}</td>
          <td class="col-status">
            <span class="status-pill" :class="row.status">{{ row.status.toUpperCase() }}</span>
          </td>
          <td class="col-worker">
            <div class="truncate mono">{{ row.worker_id || '-' }}</div>
          </td>
          <td class="col-actions">
            <button class="ghost-btn" @click="emit('view-log', row.task_id)">View Logs</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.task-list-container {
  width: 100%;
  overflow-x: auto;
}

.custom-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

th {
  background: var(--bg-sidebar);
  color: var(--text-tertiary);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.05em;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: transparent;
  transition: background-color 0.2s ease;
}

tr:hover td {
  background: var(--bg-card);
}

.empty-row {
  text-align: center;
  padding: 48px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  letter-spacing: 0.1em;
}

.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mono {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
}

.col-id {
  width: 20%;
  max-width: 150px;
}

.col-cmd {
  width: 30%;
  max-width: 250px;
}

.col-res {
  width: 10%;
  white-space: nowrap;
}

.col-status {
  width: 10%;
  text-align: center;
}

.col-worker {
  width: 15%;
  max-width: 120px;
}

.col-actions {
  width: 15%;
  text-align: right;
}

.status-pill {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 8px;
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

.status-pill.running {
  background: var(--status-running-bg);
  color: var(--status-running-text);
}

.status-pill.pending {
  background: var(--status-pending-bg);
  color: var(--status-pending-text);
}

.ghost-btn {
  background: transparent;
  border: 1px solid var(--border-hover);
  color: var(--text-secondary);
  padding: 6px 12px;
  font-size: 12px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 4px;
}

.ghost-btn:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}
</style>
