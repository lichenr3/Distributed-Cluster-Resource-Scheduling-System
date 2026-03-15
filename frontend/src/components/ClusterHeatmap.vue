<script setup lang="ts">
import { ref } from 'vue'
import type { WorkerInfo } from '@/types'
import WorkerCard from './WorkerCard.vue'

const props = defineProps<{
  workers: WorkerInfo[]
}>()

const isExpanded = ref(false)

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

function getCpuPercent(w: WorkerInfo) {
  return w.total_cpu ? Math.round((w.used_cpu / w.total_cpu) * 100) : 0
}

function getMemPercent(w: WorkerInfo) {
  return w.total_mem ? Math.round((w.used_mem / w.total_mem) * 100) : 0
}

function getHeatmapColor(percent: number) {
  if (percent >= 100) return '#ffffff'
  if (percent >= 75) return '#cccccc'
  if (percent >= 50) return '#888888'
  if (percent >= 25) return '#555555'
  return '#2a2a2a'
}
</script>

<template>
  <div class="cluster-heatmap">
    <div v-if="workers.length === 0" class="empty-state">
      暂无已注册的 Worker 节点
    </div>
    <template v-else>
      <!-- Expandable Heatmap Card -->
      <div class="heatmap-card" :class="{ expanded: isExpanded }">
        <div class="heatmap-header" @click="toggleExpand">
          <span class="heatmap-title">资源热力图</span>
          <svg class="expand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        
        <div class="heatmap-content">
          <div class="detailed-grid">
            <div class="grid-row">
              <div class="row-label">CPU</div>
              <div class="cells">
                <div 
                  v-for="w in workers" 
                  :key="`cpu-${w.worker_id}`" 
                  class="detail-cell"
                  :style="{ backgroundColor: getHeatmapColor(getCpuPercent(w)) }"
                  :title="`${w.display_name}: ${getCpuPercent(w)}% CPU`"
                ></div>
              </div>
            </div>
            <div class="grid-row">
              <div class="row-label">MEM</div>
              <div class="cells">
                <div 
                  v-for="w in workers" 
                  :key="`mem-${w.worker_id}`" 
                  class="detail-cell"
                  :style="{ backgroundColor: getHeatmapColor(getMemPercent(w)) }"
                  :title="`${w.display_name}: ${getMemPercent(w)}% MEM`"
                ></div>
              </div>
            </div>
            <div class="grid-row labels-row">
              <div class="row-label"></div>
              <div class="cells">
                <div v-for="w in workers" :key="`label-${w.worker_id}`" class="col-label" :title="w.display_name">
                  {{ w.display_name.replace('worker-', 'w') }}
                </div>
              </div>
            </div>
          </div>
          
          <div class="legend">
            <span class="legend-label">0%</span>
            <div class="legend-scale">
              <div class="legend-step" style="background: #2a2a2a"></div>
              <div class="legend-step" style="background: #555555"></div>
              <div class="legend-step" style="background: #888888"></div>
              <div class="legend-step" style="background: #cccccc"></div>
              <div class="legend-step" style="background: #ffffff"></div>
            </div>
            <span class="legend-label">100%</span>
          </div>
        </div>
      </div>

      <!-- Worker Grid -->
      <div class="worker-grid">
        <WorkerCard 
          v-for="w in workers" 
          :key="w.worker_id" 
          :worker="w" 
          :class="{ 'span-2': getCpuPercent(w) > 80 || getMemPercent(w) > 80 }"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.cluster-heatmap {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.empty-state {
  padding: 48px;
  text-align: center;
  font-family: var(--font-mono);
  color: var(--text-tertiary);
  letter-spacing: 0.1em;
  border: 1px dashed var(--border-subtle);
  border-radius: 8px;
}

/* Expandable Heatmap Card */
.heatmap-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease-in-out;
}

.heatmap-header {
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.heatmap-header:hover {
  background-color: rgba(255, 255, 255, 0.02);
}

.heatmap-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.expand-icon {
  width: 16px;
  height: 16px;
  color: var(--text-tertiary);
  transition: transform 0.3s ease;
}

.heatmap-card.expanded .expand-icon {
  transform: rotate(180deg);
}

.heatmap-content {
  max-height: 0;
  opacity: 0;
  padding: 0 24px;
  transition: all 0.3s ease-in-out;
  overflow: hidden;
}

.heatmap-card.expanded .heatmap-content {
  max-height: 400px;
  opacity: 1;
  padding: 16px 24px 24px;
  border-top: 1px solid var(--border-subtle);
}

.detailed-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.grid-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.row-label {
  width: 40px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-tertiary);
  text-align: right;
}

.cells {
  display: flex;
  gap: 2px;
}

.detail-cell {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  transition: background-color 0.3s ease;
}

.detail-cell:hover {
  outline: 1px solid var(--text-secondary);
  outline-offset: 1px;
}

.labels-row {
  margin-top: 4px;
}

.col-label {
  width: 32px;
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-tertiary);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
}

.legend {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}

.legend-label {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-tertiary);
}

.legend-scale {
  display: flex;
  gap: 2px;
}

.legend-step {
  width: 24px;
  height: 8px;
  border-radius: 2px;
}

/* Worker Grid */
.worker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.span-2 {
  grid-column: span 2;
}

@media (max-width: 1200px) {
  .span-2 {
    grid-column: span 1;
  }
}
</style>
