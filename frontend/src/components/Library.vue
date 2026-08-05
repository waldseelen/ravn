<template>
  <div class="p-6 max-w-6xl mx-auto space-y-6">
    <div class="flex justify-between items-center border-b border-slate-700 pb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-100">Media Library</h1>
        <p class="text-sm text-slate-400">Browse and manage your downloaded and converted media files.</p>
      </div>
      <button @click="fetchHistory" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm font-medium">
        Refresh
      </button>
    </div>

    <!-- Search & Filter -->
    <div class="flex gap-4">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search title, format, or path..."
        class="flex-1 px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-indigo-500"
      />
    </div>

    <!-- Media Table -->
    <div class="bg-slate-800/60 rounded-xl border border-slate-700 overflow-hidden">
      <table class="w-full text-left text-sm text-slate-300">
        <thead class="bg-slate-800 text-slate-400 font-semibold border-b border-slate-700">
          <tr>
            <th class="p-4">Title / Source</th>
            <th class="p-4">Format</th>
            <th class="p-4">Quality</th>
            <th class="p-4">Date</th>
            <th class="p-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-700/50">
          <tr v-if="filteredRecords.length === 0">
            <td colspan="5" class="p-8 text-center text-slate-500">
              No media records found.
            </td>
          </tr>
          <tr v-for="item in filteredRecords" :key="item.id" class="hover:bg-slate-800/40">
            <td class="p-4 font-medium text-slate-200">
              <div class="truncate max-w-md">{{ item.title || item.url }}</div>
              <div class="text-xs text-slate-500 truncate max-w-md">{{ item.file_path }}</div>
            </td>
            <td class="p-4 font-mono text-xs uppercase">{{ item.format || 'N/A' }}</td>
            <td class="p-4 font-mono text-xs">{{ item.quality || 'N/A' }}</td>
            <td class="p-4 text-xs text-slate-400">{{ item.download_date || 'N/A' }}</td>
            <td class="p-4 text-right">
              <button
                @click="deleteRecord(item.id)"
                class="px-3 py-1 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 rounded text-xs"
              >
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiClient } from '../services/apiClient'

const records = ref<any[]>([])
const searchQuery = ref('')

const filteredRecords = computed(() => {
  if (!searchQuery.value) return records.value
  const q = searchQuery.value.toLowerCase()
  return records.value.filter(
    r =>
      (r.title && r.title.toLowerCase().includes(q)) ||
      (r.url && r.url.toLowerCase().includes(q)) ||
      (r.file_path && r.file_path.toLowerCase().includes(q))
  )
})

async function fetchHistory() {
  try {
    records.value = await apiClient.getHistory()
  } catch (e) {
    console.error('Failed to load history:', e)
  }
}

async function deleteRecord(recordId: number) {
  if (!confirm(`Remove record #${recordId} from history?`)) return
  try {
    await fetchHistory()
  } catch (e) {
    console.error('Failed to delete record:', e)
  }
}

onMounted(() => {
  fetchHistory()
})
</script>
