<template>
  <div class="p-6 max-w-7xl mx-auto space-y-6">
    <div class="flex items-center justify-between bg-slate-900/80 backdrop-blur p-4 rounded-2xl border border-slate-800 shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30">
          <span class="text-2xl">📊</span>
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-100">Live Task Queue</h1>
          <p class="text-xs text-slate-400">Monitor active downloads, conversion jobs, ETA and speed metrics</p>
        </div>
      </div>

      <div class="flex gap-2">
        <button @click="pauseQueue" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 rounded-xl border border-slate-700">
          Pause Queue
        </button>
        <button @click="resumeQueue" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white rounded-xl shadow-lg shadow-indigo-600/30">
          Resume Queue
        </button>
      </div>
    </div>

    <!-- Active Tasks List -->
    <div class="bg-slate-900/60 backdrop-blur p-6 rounded-2xl border border-slate-800 space-y-4">
      <div v-if="store.tasks.length === 0" class="text-center py-12 text-slate-500">
        No active tasks in queue.
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="task in store.tasks"
          :key="task.id"
          class="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3"
        >
          <div class="flex justify-between items-center text-sm">
            <span class="font-semibold text-slate-200 truncate max-w-lg">{{ task.name }}</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase">
                {{ task.status }}
              </span>
            </div>
          </div>

          <div class="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden">
            <div class="bg-indigo-500 h-full transition-all duration-300" :style="{ width: `${task.progress || 0}%` }"></div>
          </div>

          <div class="flex justify-between text-xs text-slate-400 font-mono">
            <span>{{ task.progress_message || 'Processing stream...' }}</span>
            <span>{{ task.progress }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDownloadStore } from '../stores/downloadStore'

const store = useDownloadStore()

async function pauseQueue() {
  await fetch('http://127.0.0.1:7842/api/v1/queue/pause', { method: 'POST' })
}

async function resumeQueue() {
  await fetch('http://127.0.0.1:7842/api/v1/queue/resume', { method: 'POST' })
}
</script>
