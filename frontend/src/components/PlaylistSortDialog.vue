<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    style="background-color: rgba(0, 0, 0, 0.75); backdrop-filter: blur(4px);"
  >
    <div
      class="w-full max-w-4xl max-h-[85vh] rounded-2xl border shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <!-- Header -->
      <div
        class="p-4 border-b flex items-center justify-between shrink-0"
        style="background-color: var(--bg-card); border-color: var(--border-subtle);"
      >
        <div class="flex items-center gap-3">
          <span class="text-lg font-bold" style="color: var(--accent-brass);">≡</span>
          <div>
            <h2 class="text-sm font-bold" style="color: var(--text-primary);">
              {{ t.title }}
            </h2>
            <p class="text-[11px]" style="color: var(--text-muted);">
              {{ filteredRows.length }} / {{ rows.length }} {{ t.itemsFound }} • {{ selectedCount }} {{ t.selected }}
            </p>
          </div>
        </div>

        <button
          @click="closeModal"
          class="w-8 h-8 rounded-lg flex items-center justify-center border transition hover:opacity-80 cursor-pointer"
          style="background-color: var(--bg-input); color: var(--text-muted); border-color: var(--border-subtle);"
        >
          ✕
        </button>
      </div>

      <!-- Filter Controls Bar -->
      <div
        class="p-4 border-b space-y-3 shrink-0"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <!-- Title Filter -->
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
              🔍 {{ t.filterTitle }}
            </label>
            <input
              v-model="titleFilter"
              type="text"
              :placeholder="t.filterTitlePlaceholder"
              class="w-full px-3 py-1.5 rounded-xl border text-xs outline-none focus:ring-1"
              style="background-color: var(--bg-input); color: var(--text-primary); border-color: var(--border-subtle);"
            />
          </div>

          <!-- Duration Range Filter -->
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
              ◷ {{ t.filterDuration }}
            </label>
            <div class="flex items-center gap-2">
              <input
                v-model.number="minDuration"
                type="number"
                placeholder="Min s"
                class="w-1/2 px-2 py-1.5 rounded-xl border text-xs outline-none"
                style="background-color: var(--bg-input); color: var(--text-primary); border-color: var(--border-subtle);"
              />
              <span style="color: var(--text-muted);">-</span>
              <input
                v-model.number="maxDuration"
                type="number"
                placeholder="Max s"
                class="w-1/2 px-2 py-1.5 rounded-xl border text-xs outline-none"
                style="background-color: var(--bg-input); color: var(--text-primary); border-color: var(--border-subtle);"
              />
            </div>
          </div>

          <!-- Popularity Filter -->
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
              ★ {{ t.filterPopularity }}
            </label>
            <select
              v-model="popularityFilter"
              class="w-full px-3 py-1.5 rounded-xl border text-xs outline-none"
              style="background-color: var(--bg-input); color: var(--text-primary); border-color: var(--border-subtle);"
            >
              <option value="all">{{ t.popularityAll }}</option>
              <option value="top25">{{ t.popularityTop25 }}</option>
              <option value="top50">{{ t.popularityTop50 }}</option>
              <option value="top75">{{ t.popularityTop75 }}</option>
            </select>
          </div>
        </div>

        <!-- Quick Selection Buttons -->
        <div class="flex items-center justify-between text-xs pt-1">
          <div class="flex items-center gap-2">
            <button
              @click="selectAll"
              class="px-2.5 py-1 rounded-lg border text-[11px] font-semibold hover:opacity-90 cursor-pointer"
              style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
            >
              ✓ {{ t.selectAll }}
            </button>
            <button
              @click="clearSelection"
              class="px-2.5 py-1 rounded-lg border text-[11px] font-semibold hover:opacity-90 cursor-pointer"
              style="background-color: var(--bg-card); color: var(--text-muted); border-color: var(--border-subtle);"
            >
              ✕ {{ t.clearSelection }}
            </button>
            <button
              @click="invertSelection"
              class="px-2.5 py-1 rounded-lg border text-[11px] font-semibold hover:opacity-90 cursor-pointer"
              style="background-color: var(--bg-card); color: var(--text-secondary); border-color: var(--border-subtle);"
            >
              ⇄ {{ t.invertSelection }}
            </button>
          </div>

          <div class="text-[11px] font-mono" style="color: var(--text-muted);">
            {{ t.totalSize }}: ~{{ formattedTotalSize }}
          </div>
        </div>
      </div>

      <!-- Sortable 7-Column Table -->
      <div class="flex-1 overflow-y-auto min-h-[300px]">
        <table class="w-full text-left text-xs border-collapse">
          <thead
            class="sticky top-0 z-10 select-none text-[11px] uppercase font-bold"
            style="background-color: var(--bg-card); color: var(--text-secondary);"
          >
            <tr class="border-b" style="border-color: var(--border-subtle);">
              <th class="p-3 w-10 text-center">
                <input
                  type="checkbox"
                  :checked="isAllSelected"
                  @change="toggleSelectAll"
                  class="cursor-pointer rounded"
                />
              </th>
              <th class="p-3 w-16 text-center">{{ t.colCover }}</th>
              <th
                @click="sortBy('title')"
                class="p-3 cursor-pointer hover:opacity-80"
              >
                {{ t.colTitle }}
                <span v-if="sortKey === 'title'">{{ sortDesc ? '↓' : '↑' }}</span>
              </th>
              <th
                @click="sortBy('channel')"
                class="p-3 w-36 cursor-pointer hover:opacity-80 hidden md:table-cell"
              >
                {{ t.colChannel }}
                <span v-if="sortKey === 'channel'">{{ sortDesc ? '↓' : '↑' }}</span>
              </th>
              <th
                @click="sortBy('duration')"
                class="p-3 w-20 text-right cursor-pointer hover:opacity-80"
              >
                {{ t.colDuration }}
                <span v-if="sortKey === 'duration'">{{ sortDesc ? '↓' : '↑' }}</span>
              </th>
              <th
                @click="sortBy('size')"
                class="p-3 w-24 text-right cursor-pointer hover:opacity-80"
              >
                {{ t.colSize }}
                <span v-if="sortKey === 'size'">{{ sortDesc ? '↓' : '↑' }}</span>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y" style="border-color: var(--border-subtle);">
            <tr
              v-for="row in filteredRows"
              :key="row.id"
              class="transition hover:opacity-95"
              :style="{
                backgroundColor: row.selected ? 'var(--bg-card)' : 'transparent',
                borderColor: 'var(--border-subtle)'
              }"
            >
              <td class="p-3 text-center">
                <input
                  type="checkbox"
                  v-model="row.selected"
                  class="cursor-pointer rounded"
                />
              </td>
              <td class="p-3 text-center">
                <img
                  v-if="row.thumbnail"
                  :src="row.thumbnail"
                  alt="cover"
                  class="w-12 h-8 object-cover rounded border mx-auto"
                  style="border-color: var(--border-subtle);"
                />
                <div
                  v-else
                  class="w-12 h-8 rounded border flex items-center justify-center text-xs mx-auto"
                  style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-muted);"
                >
                  ▶
                </div>
              </td>
              <td class="p-3 min-w-0">
                <div class="font-bold truncate max-w-sm sm:max-w-md" style="color: var(--text-primary);">
                  {{ row.title }}
                </div>
                <div class="text-[10px] truncate max-w-sm sm:max-w-md" style="color: var(--text-muted);">
                  {{ row.url }}
                </div>
              </td>
              <td class="p-3 truncate hidden md:table-cell" style="color: var(--text-secondary);">
                {{ row.channel || '—' }}
              </td>
              <td class="p-3 text-right font-mono" style="color: var(--text-secondary);">
                {{ formatDuration(row.duration) }}
              </td>
              <td class="p-3 text-right font-mono" style="color: var(--text-muted);">
                {{ formatSize(row.size_mb) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Footer / Action Bar -->
      <div
        class="p-4 border-t flex items-center justify-between shrink-0"
        style="background-color: var(--bg-card); border-color: var(--border-subtle);"
      >
        <div class="text-xs" style="color: var(--text-muted);">
          {{ selectedCount }} {{ t.itemsSelectedForDownload }}
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="closeModal"
            class="px-4 py-2 rounded-xl border text-xs font-semibold hover:opacity-80 cursor-pointer"
            style="background-color: var(--bg-surface); color: var(--text-secondary); border-color: var(--border-subtle);"
          >
            {{ t.cancel }}
          </button>
          <button
            @click="confirmDownload"
            :disabled="selectedCount === 0"
            class="px-5 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-lg cursor-pointer disabled:opacity-50"
            style="background-color: var(--accent-brass); color: var(--bg-primary);"
          >
            <span>↓</span>
            <span>{{ t.downloadSelected }} ({{ selectedCount }})</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

export interface PlaylistEntryRow {
  id: string | number
  url: string
  title: string
  thumbnail?: string
  channel?: string
  duration?: number
  size_mb?: number
  view_count?: number
  selected: boolean
}

const props = defineProps<{
  isOpen: boolean
  entries: any[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'confirm', selectedUrls: string[]): void
}>()

const t = {
  title: 'Playlist Items & Order Review',
  itemsFound: 'items',
  selected: 'selected',
  filterTitle: 'Filter by Title',
  filterTitlePlaceholder: 'Search tracks / videos...',
  filterDuration: 'Duration (sec)',
  filterPopularity: 'Popularity',
  popularityAll: 'All Items',
  popularityTop25: 'Top 25% Most Viewed',
  popularityTop50: 'Top 50% Most Viewed',
  popularityTop75: 'Top 75% Most Viewed',
  selectAll: 'Select All',
  clearSelection: 'Clear',
  invertSelection: 'Invert',
  totalSize: 'Estimated Total Size',
  colCover: 'Cover',
  colTitle: 'Title',
  colChannel: 'Uploader / Channel',
  colDuration: 'Duration',
  colSize: 'Est. Size',
  itemsSelectedForDownload: 'items selected for acquisition',
  cancel: 'Cancel',
  downloadSelected: 'Download Selected'
}

const rows = ref<PlaylistEntryRow[]>([])
const titleFilter = ref('')
const minDuration = ref<number | null>(null)
const maxDuration = ref<number | null>(null)
const popularityFilter = ref('all')
const sortKey = ref('index')
const sortDesc = ref(false)

watch(() => props.entries, (newEntries) => {
  if (Array.isArray(newEntries)) {
    rows.value = newEntries.map((e, index) => ({
      id: e.id || index,
      url: e.url || (e.id ? `https://www.youtube.com/watch?v=${e.id}` : ''),
      title: e.title || `Item #${index + 1}`,
      thumbnail: e.thumbnail || e.thumbnails?.[0]?.url || '',
      channel: e.channel || e.uploader || '',
      duration: Number(e.duration) || 0,
      size_mb: Number(e.size_mb || e.filesize_approx_mb) || (Number(e.duration) ? (Number(e.duration) * 0.4) : 15),
      view_count: Number(e.view_count) || 0,
      selected: true
    }))
  }
}, { immediate: true })

const filteredRows = computed(() => {
  let list = rows.value.filter(row => {
    // Title filter
    if (titleFilter.value.trim()) {
      if (!row.title.toLowerCase().includes(titleFilter.value.toLowerCase().trim())) {
        return false
      }
    }
    // Duration filter
    if (minDuration.value !== null && minDuration.value > 0) {
      if ((row.duration || 0) < minDuration.value) return false
    }
    if (maxDuration.value !== null && maxDuration.value > 0) {
      if ((row.duration || 0) > maxDuration.value) return false
    }
    return true
  })

  // Popularity filter
  if (popularityFilter.value !== 'all' && list.length > 0) {
    const sortedByViews = [...list].sort((a, b) => (b.view_count || 0) - (a.view_count || 0))
    let cutoff = list.length
    if (popularityFilter.value === 'top25') cutoff = Math.ceil(list.length * 0.25)
    else if (popularityFilter.value === 'top50') cutoff = Math.ceil(list.length * 0.50)
    else if (popularityFilter.value === 'top75') cutoff = Math.ceil(list.length * 0.75)
    const allowedIds = new Set(sortedByViews.slice(0, cutoff).map(r => r.id))
    list = list.filter(r => allowedIds.has(r.id))
  }

  // Sorting
  list.sort((a, b) => {
    let cmp = 0
    if (sortKey.value === 'title') {
      cmp = a.title.localeCompare(b.title)
    } else if (sortKey.value === 'channel') {
      cmp = (a.channel || '').localeCompare(b.channel || '')
    } else if (sortKey.value === 'duration') {
      cmp = (a.duration || 0) - (b.duration || 0)
    } else if (sortKey.value === 'size') {
      cmp = (a.size_mb || 0) - (b.size_mb || 0)
    }
    return sortDesc.value ? -cmp : cmp
  })

  return list
})

const selectedCount = computed(() => rows.value.filter(r => r.selected).length)
const isAllSelected = computed(() => filteredRows.value.length > 0 && filteredRows.value.every(r => r.selected))

const formattedTotalSize = computed(() => {
  const total = rows.value.filter(r => r.selected).reduce((acc, r) => acc + (r.size_mb || 0), 0)
  if (total >= 1024) return `${(total / 1024).toFixed(1)} GB`
  return `${total.toFixed(0)} MB`
})

function sortBy(key: string) {
  if (sortKey.value === key) {
    sortDesc.value = !sortDesc.value
  } else {
    sortKey.value = key
    sortDesc.value = false
  }
}

function selectAll() {
  filteredRows.value.forEach(r => r.selected = true)
}

function clearSelection() {
  filteredRows.value.forEach(r => r.selected = false)
}

function invertSelection() {
  filteredRows.value.forEach(r => r.selected = !r.selected)
}

function toggleSelectAll() {
  const target = !isAllSelected.value
  filteredRows.value.forEach(r => r.selected = target)
}

function formatDuration(sec?: number): string {
  if (!sec || sec <= 0) return '—'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  const h = Math.floor(m / 60)
  if (h > 0) {
    return `${h}:${String(m % 60).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatSize(sizeMb?: number): string {
  if (!sizeMb || sizeMb <= 0) return '—'
  if (sizeMb >= 1024) return `${(sizeMb / 1024).toFixed(1)} GB`
  return `${sizeMb.toFixed(1)} MB`
}

function closeModal() {
  emit('close')
}

function confirmDownload() {
  const selectedUrls = rows.value.filter(r => r.selected).map(r => r.url)
  emit('confirm', selectedUrls)
}
</script>