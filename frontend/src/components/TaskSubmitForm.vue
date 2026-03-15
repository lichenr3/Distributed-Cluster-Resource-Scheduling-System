<script setup lang="ts">
import { reactive, ref } from 'vue'
import { submitTask } from '@/api'

const emit = defineEmits<{
  (e: 'submitted'): void
}>()

const visible = ref(false)
const submitting = ref(false)

const form = reactive({
  task_id: '',
  command: '',
  cpu_required: 1,
  mem_required: 1,
})

function open() {
  form.task_id = ''
  form.command = ''
  form.cpu_required = 1
  form.mem_required = 1
  visible.value = true
}

async function handleSubmit() {
  if (!form.command.trim()) return
  submitting.value = true
  try {
    const payload: any = {
      command: form.command,
      cpu_required: form.cpu_required,
      mem_required: form.mem_required,
    }
    if (form.task_id.trim()) {
      payload.task_id = form.task_id.trim()
    }
    await submitTask(payload)
    visible.value = false
    emit('submitted')
  } catch (error: any) {
    if (error.response?.data?.detail) {
      alert(error.response.data.detail)
    } else {
      console.error(error)
    }
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<template>
    <el-dialog v-model="visible" title="提交新任务" width="480px" destroy-on-close class="custom-dialog">
    <el-form :model="form" label-position="top" class="custom-form">
      <el-form-item label="TASK ID (Optional)" class="command-field">
        <el-input v-model="form.task_id" placeholder="Leave empty to auto-generate UUID" />
      </el-form-item>
      <el-form-item label="COMMAND" class="command-field">
        <el-input v-model="form.command" type="textarea" :rows="3" resize="none" placeholder="e.g. python train.py --epochs 10" />
      </el-form-item>
      <div class="form-row">
        <el-form-item label="CPU (CORES)">
          <el-input-number v-model="form.cpu_required" :min="1" :max="64" />
        </el-form-item>
        <el-form-item label="MEM (GB)">
          <el-input-number v-model="form.mem_required" :min="1" :max="256" />
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <button class="btn-ghost" @click="visible = false">取消</button>
        <button class="btn-solid" :class="{ 'is-loading': submitting }" :disabled="submitting" @click="handleSubmit">
          {{ submitting ? '提交中...' : '提交任务' }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.custom-form {
  margin-top: 8px;
}

.form-row {
  display: flex;
  gap: 24px;
}

.form-row .el-form-item {
  flex: 1;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-ghost {
  background: transparent;
  border: 1px solid var(--border-hover);
  color: var(--text-secondary);
  padding: 8px 16px;
  border-radius: 4px;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-ghost:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}

.btn-solid {
  background: var(--text-primary);
  border: 1px solid var(--text-primary);
  color: #000000;
  padding: 8px 16px;
  border-radius: 4px;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-solid:hover:not(:disabled) {
  background: #e0e0e0;
  border-color: #e0e0e0;
}

.btn-solid:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* Command input — terminal / geek style */
.command-field :deep(.el-textarea__inner) {
  background-color: #0a0a0a !important;
  border: 1px solid #1a3a1a !important;
  box-shadow: none !important;
  color: #00ff41 !important;
  font-family: var(--font-mono);
  font-size: 14px !important;
  line-height: 1.8 !important;
  padding: 16px !important;
}
.command-field :deep(.el-textarea__inner:focus) {
  border-color: #2a6a2a !important;
  box-shadow: 0 0 8px rgba(0, 255, 65, 0.08) !important;
}
.command-field :deep(.el-textarea__inner::placeholder) {
  color: #1a4a1a !important;
}
</style>
