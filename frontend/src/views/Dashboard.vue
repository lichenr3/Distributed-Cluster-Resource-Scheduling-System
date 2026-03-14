<script setup lang="ts">
import { ref, computed } from 'vue'
import { useClusterWs } from '@/composables/useClusterWs'
import ClusterHeatmap from '@/components/ClusterHeatmap.vue'
import TaskList from '@/components/TaskList.vue'
import TaskSubmitForm from '@/components/TaskSubmitForm.vue'
import LogModal from '@/components/LogModal.vue'

// ── Cluster WebSocket ──
const { workers, tasksSummary, wsStatus } = useClusterWs()

const onlineWorkersCount = computed(() => {
  return workers.value.filter(w => w.status === 'online').length
})

// ── Task list ref ──
const taskListRef = ref<InstanceType<typeof TaskList> | null>(null)
const currentFilter = ref('ALL')

// ── Submit form ──
const submitFormRef = ref<InstanceType<typeof TaskSubmitForm> | null>(null)

function handleTaskSubmitted() {
  taskListRef.value?.fetchTasks()
}

// ── Log modal ──
const logVisible = ref(false)
const logTaskId = ref('')

function openLog(taskId: string) {
  logTaskId.value = taskId
  logVisible.value = true
}

// ── Navigation ──
const activeNav = ref('overview')

function scrollToSection(id: string) {
  activeNav.value = id
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
}
</script>

<template>
  <div class="dashboard-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="logo">MINI—SCHEDULER</div>
      
      <nav class="nav-menu">
        <div 
          class="nav-item" 
          :class="{ active: activeNav === 'overview' }"
          @click="scrollToSection('overview')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
          Overview
        </div>
        
        <div class="nav-group">CLUSTER</div>
        <div 
          class="nav-item" 
          :class="{ active: activeNav === 'cluster' }"
          @click="scrollToSection('cluster')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>
          Workers & Heatmap
        </div>
        
        <div class="nav-group">TASKS</div>
        <div 
          class="nav-item" 
          :class="{ active: activeNav === 'tasks' }"
          @click="scrollToSection('tasks')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
          All Tasks
        </div>
        <div class="nav-item" @click="submitFormRef?.open()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          Submit New
        </div>
      </nav>

      <div class="ws-status">
        <div class="status-dot" :class="wsStatus"></div>
        <span>{{ wsStatus === 'connected' ? 'Connected' : 'Disconnected' }}</span>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content" id="overview">
      <div class="content-wrapper">
        
        <!-- Section 1: Top Header Bar -->
        <header class="dashboard-header">
          <div class="header-left">
            <h1 class="page-title">Cluster Overview</h1>
            <p class="page-subtitle">Real-time cluster monitoring</p>
          </div>
          <div class="header-right">
            <div class="task-counters">
              <span class="counter-badge"><span class="status-dot pending"></span> Pending {{ tasksSummary.pending }}</span>
              <span class="counter-badge"><span class="status-dot running"></span> Running {{ tasksSummary.running }}</span>
              <span class="counter-badge"><span class="status-dot success"></span> Success {{ tasksSummary.success }}</span>
              <span class="counter-badge"><span class="status-dot failed"></span> Failed {{ tasksSummary.failed }}</span>
            </div>
            <div class="ws-status-inline">
              <div class="status-dot" :class="wsStatus"></div>
              <span>{{ wsStatus === 'connected' ? 'Connected' : 'Disconnected' }}</span>
            </div>
            <button class="btn-solid" @click="submitFormRef?.open()">SUBMIT TASK</button>
          </div>
        </header>

        <!-- Section 2: Cluster Nodes -->
        <section class="section" id="cluster">
          <div class="card-container">
            <div class="card-header">
              <h2 class="section-title">CLUSTER NODES</h2>
              <div class="online-badge">
                <span class="status-dot connected"></span> ONLINE {{ onlineWorkersCount }} / {{ workers.length }}
              </div>
            </div>
            <div class="card-content">
              <ClusterHeatmap :workers="workers" />
            </div>
          </div>
        </section>

        <!-- Section 3: Recent Tasks -->
        <section class="section" id="tasks">
          <div class="card-container">
            <div class="card-header">
              <h2 class="section-title">RECENT TASKS</h2>
              <div class="task-filters">
                <div class="filter-tabs">
                  <button 
                    v-for="tab in ['ALL', 'PENDING', 'RUNNING', 'SUCCESS', 'FAILED']" 
                    :key="tab"
                    class="filter-tab"
                    :class="{ active: currentFilter === tab }"
                    @click="currentFilter = tab"
                  >
                    {{ tab }}
                  </button>
                </div>
                <button class="ghost-btn icon-btn" @click="taskListRef?.fetchTasks()" title="Refresh">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
                </button>
              </div>
            </div>
            <div class="card-content no-padding">
              <TaskList ref="taskListRef" :filter="currentFilter" @view-log="openLog" />
            </div>
          </div>
        </section>

        <!-- Section 5: Bottom Spacer -->
        <div class="bottom-spacer"></div>
      </div>
    </main>

    <!-- Dialogs -->
    <TaskSubmitForm ref="submitFormRef" @submitted="handleTaskSubmitted" />
    <LogModal v-model:visible="logVisible" :task-id="logTaskId" />
  </div>
</template>

<style scoped>
.dashboard-layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-page);
}

/* Sidebar */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: 220px;
  height: 100vh;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.logo {
  padding: 24px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.1em;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
}

.nav-menu {
  flex: 1;
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-group {
  padding: 16px 24px 8px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
}

.nav-item {
  padding: 8px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 2px solid transparent;
}

.nav-item svg {
  width: 16px;
  height: 16px;
  opacity: 0.7;
}

.nav-item:hover {
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.02);
}

.nav-item.active {
  color: var(--text-primary);
  border-left-color: var(--text-primary);
  background: rgba(255, 255, 255, 0.03);
}

.nav-item.active svg {
  opacity: 1;
}

.ws-status {
  padding: 24px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
}

/* Main Content */
.main-content {
  flex: 1;
  margin-left: 220px;
  padding: 32px 40px;
  min-height: 100vh;
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 48px;
}

/* Dashboard Header */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.task-counters {
  display: flex;
  gap: 16px;
}

.counter-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.pending { background: var(--status-pending-text); }
.status-dot.running { background: var(--status-running-text); }
.status-dot.success { background: var(--status-success-text); }
.status-dot.failed { background: var(--status-failed-text); }
.status-dot.connected { background: var(--status-success-text); }
.status-dot.disconnected { background: var(--status-failed-text); }

.ws-status-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
  padding-left: 24px;
  border-left: 1px solid var(--border-subtle);
}

.btn-solid {
  background: var(--text-primary);
  color: var(--bg-page);
  border: none;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.btn-solid:hover {
  opacity: 0.9;
}

/* Card Containers */
.card-container {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
}

.card-content {
  padding: 24px;
}

.card-content.no-padding {
  padding: 0;
}

.online-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
}

.task-filters {
  display: flex;
  align-items: center;
  gap: 16px;
}

.filter-tabs {
  display: flex;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  padding: 4px;
  border: 1px solid var(--border-subtle);
}

.filter-tab {
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  font-size: 11px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-tab:hover {
  color: var(--text-secondary);
}

.filter-tab.active {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.icon-btn {
  padding: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-btn svg {
  width: 16px;
  height: 16px;
}

/* Sections */
.section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
  margin: 0;
  white-space: nowrap;
}

.header-line {
  flex: 1;
  height: 1px;
  background: var(--border-subtle);
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
}

.ghost-btn:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}

.bottom-spacer {
  height: 120px;
}
</style>
