<template>
  <div class="p-6 max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl border shadow-xl" style="background-color: var(--bg-surface); border-color: var(--border-subtle);">
      <div class="flex items-center gap-3">
        <div class="p-3 rounded-xl border text-xl" style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);">
          <span>☰</span>
        </div>
        <div>
          <h1 class="text-xl font-bold" style="color: var(--text-primary);">{{ t.title }}</h1>
          <p class="text-xs" style="color: var(--text-muted);">
            {{ t.active }}: <strong style="color: var(--accent-brass);">{{ activeCount }}</strong> •
            {{ t.queued }}: <strong style="color: var(--text-secondary);">{{ queuedCount }}</strong> •
            {{ t.completed }}: <strong style="color: var(--status-success);">{{ completedCount }}</strong>
          </p>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center gap-2">
        <button
          v-if="!isPaused"
          @click="pauseQueue"
          class="px-4 py-2 text-xs font-semibold rounded-xl border transition hover:opacity-90"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-strong);"
        >
          ⏸ {{ t.pauseQueue }}
        </button>
        <button
          v-else
          @click="resumeQueue"
          class="px-4 py-2 text-xs font-semibold rounded-xl border transition hover:opacity-90 font-bold"
          style="background-color: var(--accent-brass); color: var(--bg-primary); border-color: var(--accent-brass);"
        >
          ▶ {{ t.resumeQueue }}
        </button>
        <button
          @click="clearCompleted"
          :disabled="completedCount === 0"
          class="px-4 py-2 text-xs font-semibold rounded-xl border transition disabled:opacity-40"
          style="background-color: var(--bg-card); color: var(--text-muted); border-color: var(--border-subtle);"
        >
          🗑 {{ t.clearCompleted }}
        </button>
      </div>
    </div>

    <!-- Task List Container -->
    <div class="p-6 rounded-2xl border space-y-4 shadow-lg" style="background-color: var(--bg-surface); border-color: var(--border-subtle);">
      <!-- Empty State -->
      <div v-if="store.tasks.length === 0" class="text-center py-16 space-y-2">
        <div class="text-3xl">📂</div>
        <p class="text-sm font-semibold" style="color: var(--text-primary);">{{ t.queueEmpty }}</p>
        <p class="text-xs" style="color: var(--text-muted);">{{ t.queueEmptyHint }}</p>
      </div>

      <!-- Task Items -->
      <div v-else class="space-y-3">
        <div
          v-for="task in store.tasks"
          :key="task.id"
          class="p-4 rounded-xl border flex flex-col gap-3 transition shadow-sm"
          style="background-color: var(--bg-card); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-3 min-w-0">
              <!-- Status Color Indicator Dot -->
              <span
                class="w-2.5 h-2.5 rounded-full shrink-0"
                :style="{ backgroundColor: getStatusColor(task.status) }"
              ></span>
              <span class="text-xs font-bold truncate" style="color: var(--text-primary);">
                {{ task.name }}
              </span>
            </div>

            <div class="flex items-center gap-3 shrink-0">
              <span
                class="text-[10px] uppercase font-mono px-2 py-0.5 rounded border"
                :style="{ color: getStatusColor(task.status), borderColor: getStatusColor(task.status) }"
              >
                {{ task.status }}
              </span>

              <button
                v-if="task.status === 'running'"
                @click="cancelTask(task.id)"
                class="text-[11px] font-semibold px-2.5 py-1 rounded-lg transition"
                style="background-color: var(--error-bg); color: var(--status-error);"
              >
                ✕ {{ t.cancel }}
              </button>
            </div>
          </div>

          <!-- Progress Bar -->
          <div
            v-if="task.status === 'running'"
            class="w-full h-1.5 rounded-full overflow-hidden"
            style="background-color: var(--bg-input);"
          >
            <div
              class="h-full transition-all duration-300 rounded-full"
              :style="{ width: `${task.progress || 0}%`, backgroundColor: 'var(--accent-brass)' }"
            ></div>
          </div>

          <!-- Progress Details -->
          <div class="flex items-center justify-between text-[11px] font-mono" style="color: var(--text-muted);">
            <span>{{ task.progress_message || t.processing }}</span>
            <span v-if="task.progress !== undefined">{{ task.progress }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDownloadStore } from '../stores/downloadStore'

const t = {
  title: 'Task Queue Manager',
  active: 'Active',
  queued: 'Queued',
  completed: 'Completed',
  pauseQueue: 'Pause Queue',
  resumeQueue: 'Resume Queue',
  clearCompleted: 'Clear Completed',
  queueEmpty: 'Task queue is empty',
  queueEmptyHint: 'Downloads and media conversions will appear here in real-time.',
  cancel: 'Cancel',
  processing: 'Processing...'
}

const store = useDownloadStore()
const isPaused = ref(false)

const activeCount = computed(() => store.tasks.filter(t => t.status === 'running').length)
const queuedCount = computed(() => store.tasks.filter(t => t.status === 'queued' || t.status === 'pending').length)
const completedCount = computed(() => store.tasks.filter(t => t.status === 'completed').length)

function getStatusColor(status: string): string {
  switch (status) {
    case 'running': return 'var(--status-running)'
    case 'completed': return 'var(--status-done)'
    case 'failed': return 'var(--status-error)'
    case 'cancelled': return 'var(--status-cancelled)'
    case 'paused': return 'var(--status-paused)'
    default: return 'var(--status-queued)'
  }
}

async function pauseQueue() {
  try {
    const res = await fetch('http://127.0.0.1:7842/api/v1/queue/pause', { method: 'POST' })
    if (res.ok) isPaused.value = true
  } catch {
    // API handling
  }
}

async function resumeQueue() {
  try {
    const res = await fetch('http://127.0.0.1:7842/api/v1/queue/resume', { method: 'POST' })
    if (res.ok) isPaused.value = false
  } catch {
    // API handling
  }
}

async function clearCompleted() {
  try {
    const res = await fetch('http://127.0.0.1:7842/api/v1/queue/completed', { method: 'DELETE' })
    if (res.ok) {
      store.tasks = store.tasks.filter(t => t.status !== 'completed')
    }
  } catch {
    // API handling
  }
}

async function cancelTask(taskId: string) {
  try {
    await fetch(`http://127.0.0.1:7842/api/v1/queue/${taskId}/cancel`, { method: 'POST' })
  } catch {
    // API handling
  }
}
</script>
