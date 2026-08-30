<template>
  <div class="space-y-6">
    <!-- Header with Quick Actions -->
    <div
      class="flex flex-col sm:flex-row sm:items-center justify-between p-5 rounded-2xl border shadow-xl gap-4"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 rounded-xl flex items-center justify-center text-xl font-bold border"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
        >
          📜
        </div>
        <div>
          <h2 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
            {{ t.historyTitle }}
          </h2>
          <p class="text-xs" style="color: var(--text-muted);">{{ t.historySubtitle }}</p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="showStatsModal = true"
          class="px-4 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          📊 {{ t.statsBtn }}
        </button>
        <button
          @click="showClearModal = true"
          class="px-4 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--error-bg); color: var(--status-error); border-color: var(--status-error);"
        >
          🗑 {{ t.clearBtn }}
        </button>
        <button
          @click="fetchHistory"
          class="px-3 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-muted); border-color: var(--border-subtle);"
          :title="t.refreshBtn"
        >
          ↻
        </button>
      </div>
    </div>

    <!-- Search & Filter Controls -->
    <div
      class="p-5 rounded-2xl border shadow-xl space-y-4"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="grid grid-cols-1 sm:grid-cols-12 gap-3">
        <!-- Live Search Input -->
        <div class="sm:col-span-6">
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t.searchPlaceholder"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
        </div>

        <!-- Format Filter -->
        <div class="sm:col-span-3">
          <select
            v-model="formatFilter"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="All">{{ t.allFormats }}</option>
            <option value="MP4">MP4</option>
            <option value="MP3">MP3</option>
            <option value="MKV">MKV</option>
            <option value="AVI">AVI</option>
            <option value="WEBM">WEBM</option>
            <option value="FLAC">FLAC</option>
          </select>
        </div>

        <!-- Status Filter -->
        <div class="sm:col-span-3">
          <select
            v-model="statusFilter"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="All">{{ t.allStatuses }}</option>
            <option value="completed">{{ t.statusCompleted }}</option>
            <option value="failed">{{ t.statusFailed }}</option>
            <option value="cancelled">{{ t.statusCancelled }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Error Panel -->
    <ErrorPanel
      :show="Boolean(errorMessage)"
      :message="errorMessage"
      @retry="fetchHistory"
    />

    <!-- History List Card -->
    <div
      class="p-5 rounded-2xl border shadow-xl space-y-4"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
          📥 {{ t.recordsTitle }}
        </h3>
        <span class="text-xs font-mono" style="color: var(--accent-brass);">
          {{ filteredRecords.length }} {{ t.recordsFound }}
        </span>
      </div>

      <!-- Empty State -->
      <div
        v-if="filteredRecords.length === 0"
        class="p-12 text-center rounded-xl border border-dashed space-y-2"
        style="background-color: var(--bg-card); border-color: var(--border-subtle);"
      >
        <div class="text-3xl">📭</div>
        <div class="text-xs font-bold" style="color: var(--text-primary);">{{ t.noHistory }}</div>
        <div class="text-[11px]" style="color: var(--text-muted);">{{ t.noHistorySub }}</div>
      </div>

      <!-- Records List -->
      <div v-else class="space-y-3">
        <div
          v-for="record in filteredRecords"
          :key="record.id"
          class="p-4 rounded-xl border transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
          style="background-color: var(--bg-card); border-color: var(--border-subtle);"
        >
          <!-- Info Details -->
          <div class="flex items-start gap-3 min-w-0 flex-1">
            <div
              class="w-12 h-12 rounded-lg flex items-center justify-center font-mono font-bold text-xs flex-shrink-0 border uppercase"
              style="background-color: var(--bg-surface); color: var(--accent-brass); border-color: var(--border-brass);"
            >
              {{ record.format || 'DL' }}
            </div>
            <div class="min-w-0 flex-1 space-y-1">
              <div class="text-xs font-bold truncate" style="color: var(--text-primary);">
                {{ record.title || record.url || t.noTitle }}
              </div>
              <div class="flex flex-wrap items-center gap-2 text-[10px] font-mono" style="color: var(--text-muted);">
                <span class="uppercase font-bold" style="color: var(--accent-brass);">{{ record.format || 'N/A' }}</span>
                <span>•</span>
                <span>{{ record.quality || 'Best' }}</span>
                <span>•</span>
                <span>{{ formatSize(record.file_size) }}</span>
                <span>•</span>
                <span>🕒 {{ formatDate(record.download_date) }}</span>
              </div>
              <div class="text-[9px] font-mono truncate" style="color: var(--text-muted);">
                {{ record.file_path || record.url }}
              </div>
            </div>
          </div>

          <!-- Status Badge & Action Buttons -->
          <div class="flex items-center gap-2 flex-shrink-0 w-full sm:w-auto justify-end">
            <span
              class="px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider font-mono"
              :style="{
                backgroundColor: getStatusBg(record.status),
                color: getStatusColor(record.status)
              }"
            >
              {{ record.status || 'unknown' }}
            </span>

            <button
              v-if="record.file_path"
              @click="openFile(record.file_path)"
              class="px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition hover:opacity-90 cursor-pointer"
              style="background-color: var(--bg-surface); color: var(--text-primary); border-color: var(--border-subtle);"
              :title="t.openFile"
            >
              ▶ {{ t.open }}
            </button>

            <button
              @click="deleteRecord(record.id)"
              class="px-2 py-1 rounded-lg text-[11px] font-semibold border transition hover:opacity-90 cursor-pointer"
              style="background-color: var(--error-bg); color: var(--status-error); border-color: var(--status-error);"
              :title="t.delete"
            >
              ✕
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Statistics Modal Dialog -->
    <div
      v-if="showStatsModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      style="background-color: rgba(0,0,0,0.6);"
      @click.self="showStatsModal = false"
    >
      <div
        class="max-w-md w-full p-6 rounded-2xl border shadow-2xl space-y-4"
        style="background-color: var(--bg-surface); border-color: var(--border-brass);"
      >
        <div class="flex items-center justify-between border-b pb-3" style="border-color: var(--border-subtle);">
          <h3 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
            📊 {{ t.statsModalTitle }}
          </h3>
          <button
            @click="showStatsModal = false"
            class="text-xs p-1 rounded transition hover:opacity-80 cursor-pointer"
            style="color: var(--text-muted);"
          >
            ✕
          </button>
        </div>

        <div class="space-y-2.5 text-xs">
          <div class="flex justify-between p-2.5 rounded-xl" style="background-color: var(--bg-card);">
            <span style="color: var(--text-muted);">{{ t.statTotalDownloads }}:</span>
            <span class="font-bold font-mono" style="color: var(--text-primary);">{{ dbStats.total_downloads ?? 0 }}</span>
          </div>
          <div class="flex justify-between p-2.5 rounded-xl" style="background-color: var(--bg-card);">
            <span style="color: var(--text-muted);">{{ t.statSuccessDownloads }}:</span>
            <span class="font-bold font-mono" style="color: var(--status-done);">{{ dbStats.successful_downloads ?? 0 }}</span>
          </div>
          <div class="flex justify-between p-2.5 rounded-xl" style="background-color: var(--bg-card);">
            <span style="color: var(--text-muted);">{{ t.statTotalSize }}:</span>
            <span class="font-bold font-mono" style="color: var(--accent-brass);">{{ formatSize(dbStats.total_size ?? 0) }}</span>
          </div>
          <div class="flex justify-between p-2.5 rounded-xl" style="background-color: var(--bg-card);">
            <span style="color: var(--text-muted);">{{ t.statTotalConversions }}:</span>
            <span class="font-bold font-mono" style="color: var(--text-primary);">{{ dbStats.total_conversions ?? 0 }}</span>
          </div>
          <div class="flex justify-between p-2.5 rounded-xl" style="background-color: var(--bg-card);">
            <span style="color: var(--text-muted);">{{ t.statTotalOperations }}:</span>
            <span class="font-bold font-mono" style="color: var(--text-primary);">{{ dbStats.total_operations ?? 0 }}</span>
          </div>
        </div>

        <div class="flex justify-end pt-2">
          <button
            @click="showStatsModal = false"
            class="px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer"
            style="background-color: var(--accent-brass); color: var(--bg-primary);"
          >
            {{ t.closeModal }}
          </button>
        </div>
      </div>
    </div>

    <!-- Clear Confirmation Modal Dialog -->
    <div
      v-if="showClearModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      style="background-color: rgba(0,0,0,0.6);"
      @click.self="showClearModal = false"
    >
      <div
        class="max-w-sm w-full p-6 rounded-2xl border shadow-2xl space-y-4 text-center"
        style="background-color: var(--bg-surface); border-color: var(--status-error);"
      >
        <div class="text-3xl">⚠️</div>
        <h3 class="text-sm font-bold" style="color: var(--text-primary);">
          {{ t.confirmClearTitle }}
        </h3>
        <p class="text-xs" style="color: var(--text-muted);">
          {{ t.confirmClearSubtitle }}
        </p>

        <div class="flex items-center justify-center gap-3 pt-2">
          <button
            @click="showClearModal = false"
            class="px-4 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
            style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
          >
            {{ t.cancel }}
          </button>
          <button
            @click="executeClearHistory"
            class="px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer"
            style="background-color: var(--error-bg); color: var(--status-error); border: 1px solid var(--status-error);"
          >
            {{ t.confirmClearBtn }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiClient } from '../services/apiClient'
import { useToastStore } from '../stores/toastStore'
import ErrorPanel from './ErrorPanel.vue'

const toast = useToastStore()

const t = {
  historyTitle: 'İndirme Geçmişi',
  historySubtitle: 'Tamamlanan, devam eden ve başarısız indirmelerin listesi',
  statsBtn: 'İstatistikler',
  clearBtn: 'Geçmişi Temizle',
  refreshBtn: 'Yenile',
  searchPlaceholder: 'Başlık, URL veya dosya yolu ile canlı ara...',
  allFormats: 'Tüm Formatlar',
  allStatuses: 'Tüm Durumlar',
  statusCompleted: 'Tamamlandı (Completed)',
  statusFailed: 'Başarısız (Failed)',
  statusCancelled: 'İptal Edildi (Cancelled)',
  recordsTitle: 'Geçmiş Kayıtları',
  recordsFound: 'kayıt listeleniyor',
  noHistory: 'Geçmiş kaydı bulunamadı',
  noHistorySub: 'Arama kriterlerinizi değiştirin veya yeni bir indirme başlatın.',
  noTitle: 'İsimsiz İndirme',
  openFile: 'Varsayılan oynatıcıda aç',
  open: 'Aç',
  delete: 'Sil',
  statsModalTitle: 'Detaylı İstatistikler',
  statTotalDownloads: 'Toplam İndirme',
  statSuccessDownloads: 'Başarılı İndirme',
  statTotalSize: 'Toplam İndirilen Boyut',
  statTotalConversions: 'Toplam Dönüştürme',
  statTotalOperations: 'Toplam Studio İşlemi',
  closeModal: 'Kapat',
  confirmClearTitle: 'Geçmişi Temizlemek İstiyor musunuz?',
  confirmClearSubtitle: 'Tüm indirme geçmişi kayıtları kalıcı olarak silinecektir. Dosyalarınız etkilenmez.',
  cancel: 'İptal',
  confirmClearBtn: 'Evet, Tümünü Temizle'
}

// State
const records = ref<any[]>([])
const dbStats = ref<any>({})
const searchQuery = ref('')
const formatFilter = ref('All')
const statusFilter = ref('All')
const errorMessage = ref('')

const showStatsModal = ref(false)
const showClearModal = ref(false)

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDate(dateStr: string): string {
  if (!dateStr) return 'N/A'
  return String(dateStr).replace('T', ' ').slice(0, 19)
}

function getStatusBg(status: string): string {
  switch (status?.toLowerCase()) {
    case 'completed': return 'var(--success-bg)'
    case 'failed': return 'var(--error-bg)'
    case 'cancelled': return 'var(--warning-bg)'
    default: return 'var(--info-bg)'
  }
}

function getStatusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'completed': return 'var(--status-done)'
    case 'failed': return 'var(--status-error)'
    case 'cancelled': return 'var(--status-cancelled)'
    default: return 'var(--accent-brass)'
  }
}

const filteredRecords = computed(() => {
  let list = records.value
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(r =>
      (r.title && r.title.toLowerCase().includes(q)) ||
      (r.url && r.url.toLowerCase().includes(q)) ||
      (r.file_path && r.file_path.toLowerCase().includes(q))
    )
  }
  if (formatFilter.value !== 'All') {
    list = list.filter(r => (r.format || '').toUpperCase() === formatFilter.value.toUpperCase())
  }
  if (statusFilter.value !== 'All') {
    list = list.filter(r => (r.status || '').toLowerCase() === statusFilter.value.toLowerCase())
  }
  return list
})

async function fetchHistory() {
  errorMessage.value = ''
  try {
    records.value = await apiClient.getHistory()
  } catch (err: any) {
    errorMessage.value = err.message || 'Geçmiş kayıtları alınamadı'
  }
}

async function loadStats() {
  try {
    dbStats.value = await apiClient.getStats()
  } catch {
    // Handling
  }
}

async function deleteRecord(id: number) {
  try {
    await apiClient.deleteDownloadHistory(id)
    toast.success('Kayıt silindi')
    records.value = records.value.filter(r => r.id !== id)
    await loadStats()
  } catch (err: any) {
    toast.error(err.message || 'Kayıt silinemedi')
  }
}

async function executeClearHistory() {
  showClearModal.value = false
  try {
    await apiClient.clearDownloadHistory()
    toast.success('Tüm indirme geçmişi temizlendi')
    records.value = []
    await loadStats()
  } catch (err: any) {
    toast.error(err.message || 'Geçmiş temizlenemedi')
  }
}

async function openFile(path: string) {
  try {
    await apiClient.openFile(path)
  } catch (err: any) {
    toast.error(err.message || 'Dosya açılamadı')
  }
}

onMounted(async () => {
  await Promise.all([fetchHistory(), loadStats()])
})
</script>
