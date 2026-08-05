<template>
  <div class="p-6 max-w-4xl mx-auto space-y-6">
    <div class="flex items-center justify-between border-b border-slate-700 pb-4">
      <h1 class="text-2xl font-bold text-slate-100 flex items-center gap-2">
        <span>⚡ RAVN Media Downloader</span>
      </h1>
      <div class="flex items-center gap-2">
        <span
          class="w-3 h-3 rounded-full"
          :class="store.isConnected ? 'bg-emerald-500' : 'bg-amber-500'"
        ></span>
        <span class="text-xs text-slate-400">
          {{ store.isConnected ? 'Backend Connected' : 'Connecting to API...' }}
        </span>
      </div>
    </div>

    <!-- Quick Download Box -->
    <div class="bg-slate-800/60 p-6 rounded-xl border border-slate-700 space-y-4">
      <h2 class="text-lg font-semibold text-slate-200">Start New Download</h2>
      <div class="flex gap-3">
        <input
          v-model="url"
          type="text"
          placeholder="Paste YouTube or Media URL here..."
          class="flex-1 px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-indigo-500"
        />
        <button
          @click="handleStartDownload"
          :disabled="!url || loading"
          class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 font-medium text-white rounded-lg transition"
        >
          {{ loading ? 'Enqueuing...' : 'Download' }}
        </button>
      </div>

      <div class="flex gap-4 text-sm text-slate-400">
        <label class="flex items-center gap-2">
          Format:
          <select v-model="format" class="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200">
            <option value="mp4">MP4 Video</option>
            <option value="mkv">MKV Video</option>
            <option value="mp3">MP3 Audio</option>
            <option value="m4a">M4A Audio</option>
          </select>
        </label>
        <label class="flex items-center gap-2">
          Quality:
          <select v-model="quality" class="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200">
            <option value="best">Best Available</option>
            <option value="1080p">1080p HD</option>
            <option value="720p">720p</option>
            <option value="audio">Audio Only</option>
          </select>
        </label>
      </div>
    </div>

    <!-- Active Tasks Queue -->
    <div class="space-y-3">
      <h2 class="text-lg font-semibold text-slate-200">Task Queue</h2>
      <div v-if="store.tasks.length === 0" class="text-center py-8 text-slate-500 bg-slate-800/30 rounded-xl border border-slate-800">
        No active tasks in queue.
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="task in store.tasks"
          :key="task.id"
          class="p-4 bg-slate-800 border border-slate-700 rounded-lg flex flex-col gap-2"
        >
          <div class="flex justify-between items-center">
            <span class="font-medium text-slate-200 truncate max-w-md">{{ task.name }}</span>
            <span
              class="text-xs px-2 py-0.5 rounded font-mono uppercase"
              :class="{
                'bg-blue-500/20 text-blue-400': task.status === 'running',
                'bg-emerald-500/20 text-emerald-400': task.status === 'completed',
                'bg-rose-500/20 text-rose-400': task.status === 'failed',
                'bg-slate-700 text-slate-300': task.status === 'queued' || task.status === 'pending'
              }"
            >
              {{ task.status }}
            </span>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
            <div
              class="bg-indigo-500 h-full transition-all duration-300"
              :style="{ width: `${task.progress || 0}%` }"
            ></div>
          </div>

          <div class="flex justify-between text-xs text-slate-400">
            <span>{{ task.progress_message || 'Processing...' }}</span>
            <span>{{ task.progress }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDownloadStore } from '../stores/downloadStore'
import { apiClient, connectWebSocket } from '../services/apiClient'

const store = useDownloadStore()
const url = ref('')
const format = ref('mp4')
const quality = ref('best')
const loading = ref(false)

async function handleStartDownload() {
  if (!url.value) return
  loading.value = true
  try {
    await apiClient.startDownload({
      url: url.value,
      output_dir: 'downloads',
      format: format.value,
      quality: quality.value
    })
    url.value = ''
    refreshQueue()
  } catch (e: any) {
    alert('Failed to start download: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function refreshQueue() {
  try {
    const queue = await apiClient.getQueue()
    store.setTasks(queue)
  } catch (e) {
    console.error('Failed to fetch queue:', e)
  }
}

onMounted(() => {
  refreshQueue()

  connectWebSocket((event, data) => {
    store.isConnected = true
    if (event === 'task.progress') {
      store.updateTaskProgress(data.task_id, data.progress, data.message)
    } else if (event === 'task.complete') {
      store.completeTask(data.task_id, data.output_path, data.duration_seconds)
    } else if (event === 'task.error') {
      store.failTask(data.task_id, data.error_message)
    }
  })
})
</script>
