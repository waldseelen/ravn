<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center bg-[#1E1E1E] p-4 rounded-2xl border border-[#3A3330] shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-[#C99A5B]/10 text-[#C99A5B] rounded-xl border border-[#C99A5B]/20">
          <span class="text-xl">▦</span>
        </div>
        <div>
          <h1 class="text-lg font-bold text-[#E8E0D8]">Media Library</h1>
          <p class="text-xs text-[#A09080]">Browse, search, and manage your local media history</p>
        </div>
      </div>
      <button @click="fetchHistory" class="px-4 py-2 bg-[#252525] hover:bg-[#2A2A2A] border border-[#3A3330] rounded-xl text-xs font-semibold text-[#E8E0D8]">
        Refresh Library
      </button>
    </div>

    <!-- Search & Filter Bar -->
    <div class="flex gap-4">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search by title, format, or file path..."
        class="flex-1 px-4 py-3 bg-[#141414] border border-[#3A3330] rounded-xl text-[#E8E0D8] text-xs focus:outline-none focus:border-[#C99A5B]"
      />
    </div>

    <!-- Media Table -->
    <div class="bg-[#1E1E1E] rounded-2xl border border-[#3A3330] overflow-hidden shadow-xl">
      <table class="w-full text-left text-xs text-[#B8A99A]">
        <thead class="bg-[#141414] text-[#A09080] font-bold uppercase tracking-wider border-b border-[#3A3330]">
          <tr>
            <th class="p-4">Title / Source</th>
            <th class="p-4">Format</th>
            <th class="p-4">Quality</th>
            <th class="p-4">Date</th>
            <th class="p-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[#3A3330]/50">
          <tr v-if="filteredRecords.length === 0">
            <td colspan="5" class="p-8 text-center text-[#A09080]">
              No media records found in local library.
            </td>
          </tr>
          <tr v-for="item in filteredRecords" :key="item.id" class="hover:bg-[#252525]">
            <td class="p-4 font-semibold text-[#E8E0D8]">
              <div class="truncate max-w-md">{{ item.title || item.url }}</div>
              <div class="text-[10px] text-[#A09080] font-mono truncate max-w-md">{{ item.file_path }}</div>
            </td>
            <td class="p-4 font-mono text-xs uppercase text-[#C99A5B]">{{ item.format || 'N/A' }}</td>
            <td class="p-4 font-mono text-xs">{{ item.quality || 'N/A' }}</td>
            <td class="p-4 text-xs text-[#A09080]">{{ item.download_date || 'N/A' }}</td>
            <td class="p-4 text-right">
              <button
                @click="deleteRecord(item.id)"
                class="px-3 py-1 bg-[#ef4444]/10 text-[#ef4444] hover:bg-[#ef4444]/20 rounded text-[11px] font-semibold border border-[#ef4444]/20"
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
