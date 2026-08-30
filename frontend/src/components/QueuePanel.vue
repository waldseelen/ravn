<template>
  <div class="p-6 max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <div
      class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl border shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex items-center gap-3">
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center text-2xl font-bold border"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
        >
          <span>☰</span>
        </div>
        <div>
          <h1 class="text-base font-bold uppercase tracking-wider" style="color: var(--text-primary);">
            {{ t.title }}
          </h1>
          <p class="text-xs" style="color: var(--text-muted);">
            {{ t.active }}: <strong style="color: var(--status-running);">{{ activeCount }}</strong> •
            {{ t.queued }}: <strong style="color: var(--status-queued);">{{ queuedCount }}</strong> •
            {{ t.completed }}: <strong style="color: var(--status-done);">{{ completedCount }}</strong>
          </p>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center gap-2 flex-wrap">
        <button
          v-if="!isPaused"
          @click="pauseQueue"
          class="px-4 py-2 text-xs font-semibold rounded-xl border transition hover:opacity-90 cursor-pointer flex items-center gap-1.5"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          <span>⏸</span> {{ t.pauseQueue }}
        </button>
        <button
          v-else
          @click="resumeQueue"
          class="px-4 py-2 text-xs font-bold rounded-xl border transition hover:opacity-90 cursor-pointer flex items-center gap-1.5"
          style="background-color: var(--accent-brass); color: var(--bg-primary); border-color: var(--accent-brass);"
        >
          <span>▶</span> {{ t.resumeQueue }}
        </button>
        <button
          @click="clearCompleted"
          :disabled="completedCount === 0"
          class="px-4 py-2 text-xs font-semibold rounded-xl border transition hover:opacity-90 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
          style="background-color: var(--bg-card); color: var(--text-secondary); border-color: var(--border-subtle);"
        >
          <span>🗑</span> {{ t.clearCompleted }}
        </button>
        <button
          @click="refreshQueue"
          class="px-3 py-2 text-xs font-semibold rounded-xl border transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-muted); border-color: var(--border-subtle);"
          :title="t.refresh"
        >
          ↻
        </button>
      </div>
    </div>

    <!-- Task List Container -->
    <div
      class="p-6 rounded-2xl border space-y-4 shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <!-- Empty State Widget (MIC-05) -->
      <div
        v-if="store.tasks.length === 0"
        class="text-center py-20 space-y-3 rounded-xl border border-dashed"
        style="background-color: var(--bg-card); border-color: var(--border-subtle);"
      >
        <div class="text-4xl">📭</div>
        <p class="text-sm font-bold" style="color: var(--text-primary);">{{ t.queueEmpty }}</p>
        <p class="text-xs max-w-sm mx-auto" style="color: var(--text-muted);">{{ t.queueEmptyHint }}</p>
      </div>

      <!-- Task Items List (P7-T1: QueueItemWidget) -->
      <div v-else class="space-y-3">
        <div
          v-for="task in store.tasks"
          :key="task.id"
          class="p-4 rounded-xl border flex flex-col gap-3 transition shadow-sm relative overflow-hidden"
          style="background-color: var(--bg-card); border-color: var(--border-subtle);"
        >
          <!-- Left Status Accent Bar -->
          <div
            class="absolute left-0 top-0 bottom-0 w-1.5"
            :style="{ backgroundColor: getStatusColor(task.status) }"
          ></div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pl-2">
            <!-- Task Info & Animated Status Icon -->
            <div class="flex items-start sm:items-center gap-3 min-w-0 flex-1">
              <!-- Animated State Icon -->
              <div
                class="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0"
                :style="{
                  backgroundColor: getStatusBg(task.status),
                  color: getStatusColor(task.status)
                }"
              >
                <span v-if="task.status === 'running'" class="animate-spin text-base">⟳</span>
                <span v-else-if="task.status === 'completed'" class="text-base font-bold">✓</span>
                <span v-else-if="task.status === 'failed'" class="text-base font-bold animate-pulse">✕</span>
                <span v-else-if="task.status === 'paused'" class="text-xs">⏸</span>
                <span v-else-if="task.status === 'cancelled'" class="text-xs">🚫</span>
                <span v-else class="text-xs">⏳</span>
              </div>

              <!-- Task Name and Status Message -->
              <div class="min-w-0 flex-1 space-y-0.5">
                <div class="text-xs font-bold truncate" style="color: var(--text-primary);">
                  {{ task.name || task.id }}
                </div>
                <div class="text-[11px] font-mono flex flex-wrap items-center gap-2" style="color: var(--text-muted);">
                  <span>{{ getStatusMessage(task) }}</span>
                  <span v-if="task.status === 'completed' && getDurationText(task)">
                    • {{ getDurationText(task) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Status Badge & Action Buttons -->
            <div class="flex items-center gap-2 flex-shrink-0 self-end sm:self-auto">
              <span
                class="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded border"
                :style="{
                  color: getStatusColor(task.status),
                  borderColor: getStatusColor(task.status),
                  backgroundColor: getStatusBg(task.status)
                }"
              >
                {{ task.status }}
              </span>

              <!-- Cancel Button for running/queued tasks -->
              <button
                v-if="task.status === 'running' || task.status === 'queued' || task.status === 'pending'"
                @click="cancelTask(task.id)"
                class="text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition hover:opacity-90 cursor-pointer"
                style="background-color: var(--error-bg); color: var(--status-error); border-color: var(--status-error);"
                :title="t.cancel"
              >
                ✕ {{ t.cancel }}
              </button>

              <!-- Open Folder Button for completed tasks with output path -->
              <button
                v-if="task.status === 'completed' && (task.output_path || task.result?.output_path)"
                @click="openFolder(task.output_path || task.result?.output_path)"
                class="text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition hover:opacity-90 cursor-pointer"
                style="background-color: var(--bg-surface); color: var(--text-primary); border-color: var(--border-subtle);"
                :title="t.openFolder"
              >
                📂 {{ t.openFolder }}
              </button>
            </div>
          </div>

          <!-- Running Progress Bar -->
          <div
            v-if="task.status === 'running'"
            class="w-full h-1.5 rounded-full overflow-hidden ml-2"
            style="background-color: var(--bg-input);"
          >
            <div
              class="h-full transition-all duration-300 rounded-full"
              :style="{
                width: `${task.progress || 0}%`,
                backgroundColor: 'var(--accent-brass)'
              }"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDownloadStore } from '../stores/downloadStore'
import { useToastStore } from '../stores/toastStore'
import { apiClient } from '../services/apiClient'

const store = useDownloadStore()
const toast = useToastStore()

const isPaused = ref(false)

const t = {
  title: 'İşlem ve Görev Kuyruğu',
  active: 'Çalışıyor',
  queued: 'Kuyrukta',
  completed: 'Tamamlandı',
  pauseQueue: 'Kuyruğu Duraklat',
  resumeQueue: 'Kuyruğu Devam Ettir',
  clearCompleted: 'Tamamlananları Temizle',
  refresh: 'Yenile',
  queueEmpty: 'Kuyruk Boş',
  queueEmptyHint: 'Aktif veya kuyruktaki indirme ve işleme görevleri burada gerçek zamanlı olarak listelenir.',
  cancel: 'İptal',
  openFolder: 'Klasörü Aç',
  processing: 'İşleniyor...',
  completedStatus: 'Tamamlandı',
  failedStatus: 'Başarısız'
}

const activeCount = computed(() => store.tasks.filter(t => t.status === 'running').length)
const queuedCount = computed(() => store.tasks.filter(t => t.status === 'queued' || t.status === 'pending').length)
const completedCount = computed(() => store.tasks.filter(t => t.status === 'completed').length)

function getStatusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'running': return 'var(--status-running)'
    case 'completed': return 'var(--status-done)'
    case 'failed': return 'var(--status-error)'
    case 'cancelled': return 'var(--status-cancelled)'
    case 'paused': return 'var(--status-paused)'
    default: return 'var(--status-queued)'
  }
}

function getStatusBg(status: string): string {
  switch (status?.toLowerCase()) {
    case 'running': return 'var(--info-bg)'
    case 'completed': return 'var(--success-bg)'
    case 'failed': return 'var(--error-bg)'
    case 'cancelled': return 'var(--warning-bg)'
    default: return 'var(--bg-input)'
  }
}

function getStatusMessage(task: any): string {
  if (task.status === 'running') {
    return task.progress_message || `${task.progress || 0}% • ${t.processing}`
  }
  if (task.status === 'completed') {
    return t.completedStatus
  }
  if (task.status === 'failed') {
    return task.error_message || task.result?.error_message || t.failedStatus
  }
  return task.status || 'queued'
}

function getDurationText(task: any): string {
  if (task.started_at && task.completed_at) {
    try {
      const start = new Date(task.started_at).getTime()
      const end = new Date(task.completed_at).getTime()
      const delta = Math.max(0, (end - start) / 1000)
      return `${delta.toFixed(1)}s`
    } catch {
      return ''
    }
  }
  return ''
}

async function refreshQueue() {
  try {
    const queueData = await apiClient.getQueue()
    if (queueData && Array.isArray(queueData.tasks)) {
      store.tasks = queueData.tasks
    }
  } catch {
    // Handling
  }
}

async function cancelTask(taskId: string) {
  try {
    await fetch(`http://127.0.0.1:7842/api/v1/queue/${taskId}/cancel`, { method: 'POST' })
    toast.info('Görev iptal talebi gönderildi')
    await refreshQueue()
  } catch (err: any) {
    toast.error(err.message || 'İptal işlemi başarısız')
  }
}

async function clearCompleted() {
  try {
    const res = await fetch('http://127.0.0.1:7842/api/v1/queue/completed', { method: 'DELETE' })
    if (res.ok) {
      store.tasks = store.tasks.filter(t => t.status !== 'completed')
      toast.success('Tamamlanan görevler temizlendi')
    }
  } catch (err: any) {
    toast.error(err.message || 'Temizleme başarısız')
  }
}

function pauseQueue() {
  isPaused.value = true
  toast.info('Kuyruk duraklatıldı')
}

function resumeQueue() {
  isPaused.value = false
  toast.success('Kuyruk devam ettiriliyor')
}

async function openFolder(path?: string) {
  if (!path) return
  try {
    await apiClient.openFolder(path)
  } catch (err: any) {
    toast.error(err.message || 'Klasör açılamadı')
  }
}
</script>
