<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div
      class="flex justify-between items-center p-4 rounded-2xl border shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex items-center gap-3">
        <div
          class="p-3 rounded-xl border text-xl"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
        >
          <span>▦</span>
        </div>
        <div>
          <h1 class="text-lg font-bold" style="color: var(--text-primary);">{{ t.title }}</h1>
          <p class="text-xs" style="color: var(--text-muted);">{{ t.subtitle }}</p>
        </div>
      </div>
      <button
        @click="fetchHistory"
        class="px-4 py-2 border rounded-xl text-xs font-semibold transition hover:opacity-90 cursor-pointer"
        style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-strong);"
      >
        ↻ {{ t.refresh }}
      </button>
    </div>

    <!-- Search & Filter Bar -->
    <div class="flex gap-4">
      <input
        v-model="searchQuery"
        type="text"
        :placeholder="t.searchPlaceholder"
        class="flex-1 px-4 py-3 rounded-xl text-xs border focus:outline-none"
        style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
      />
    </div>

    <!-- Media Table -->
    <div
      class="rounded-2xl border overflow-hidden shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <table class="w-full text-left text-xs" style="color: var(--text-secondary);">
        <thead
          class="font-bold uppercase tracking-wider border-b"
          style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-muted);"
        >
          <tr>
            <th class="p-4">{{ t.colTitle }}</th>
            <th class="p-4">{{ t.colFormat }}</th>
            <th class="p-4">{{ t.colQuality }}</th>
            <th class="p-4">{{ t.colDate }}</th>
            <th class="p-4 text-right">{{ t.colActions }}</th>
          </tr>
        </thead>
        <tbody class="divide-y" style="border-color: var(--border-subtle);">
          <tr v-if="filteredRecords.length === 0">
            <td colspan="5" class="p-8 text-center" style="color: var(--text-muted);">
              {{ t.empty }}
            </td>
          </tr>
          <tr
            v-for="item in filteredRecords"
            :key="item.id"
            class="transition"
            style="border-color: var(--border-subtle);"
          >
            <td class="p-4 font-semibold" style="color: var(--text-primary);">
              <div class="truncate max-w-md">{{ item.title || item.url }}</div>
              <div class="text-[10px] font-mono truncate max-w-md" style="color: var(--text-muted);">
                {{ item.file_path }}
              </div>
            </td>
            <td class="p-4 font-mono text-xs uppercase" style="color: var(--accent-brass);">
              {{ item.format || 'N/A' }}
            </td>
            <td class="p-4 font-mono text-xs">{{ item.quality || 'N/A' }}</td>
            <td class="p-4 text-xs" style="color: var(--text-muted);">{{ item.download_date || 'N/A' }}</td>
            <td class="p-4 text-right">
              <button
                @click="deleteRecord(item.id)"
                class="px-3 py-1 rounded text-[11px] font-semibold border transition hover:opacity-80"
                style="background-color: var(--error-bg); color: var(--status-error); border-color: var(--status-error);"
              >
                ✕ {{ t.delete }}
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

const t = {
  title: 'Media Library',
  subtitle: 'Browse, search, and manage your local media history',
  refresh: 'Refresh Library',
  searchPlaceholder: 'Search by title, format, or file path...',
  colTitle: 'Title / Source',
  colFormat: 'Format',
  colQuality: 'Quality',
  colDate: 'Date',
  colActions: 'Actions',
  empty: 'No media records found in local library.',
  delete: 'Delete'
}

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

async function deleteRecord(_recordId: number) {
  try {
    // API deletion call
    await fetchHistory()
  } catch (e) {
    console.error('Failed to delete record:', e)
  }
}

onMounted(() => {
  fetchHistory()
})
</script>
