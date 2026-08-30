<template>
  <div class="space-y-6">
    <!-- Main Content Layout (Left: Import/Search/Results, Right: Sidebar) -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <!-- Left Column (8 cols on large screens) -->
      <div class="lg:col-span-8 space-y-6">
        <!-- Import Card -->
        <div
          class="p-5 rounded-2xl border shadow-xl space-y-4"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
              📥 {{ t.importTitle }}
            </h3>
            <span class="text-[11px]" style="color: var(--text-muted);">{{ t.importSubtitle }}</span>
          </div>

          <!-- File Picker (DND supported) -->
          <div
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            class="p-4 rounded-xl border-2 border-dashed transition flex flex-col sm:flex-row items-center gap-3 cursor-pointer"
            :style="{
              backgroundColor: isDragging ? 'var(--bg-hover)' : 'var(--bg-card)',
              borderColor: isDragging ? 'var(--accent-brass)' : 'var(--border-strong)'
            }"
            @click="browseFile"
          >
            <div
              class="w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold flex-shrink-0"
              style="background-color: var(--bg-surface); color: var(--accent-brass);"
            >
              📂
            </div>
            <div class="flex-1 min-w-0 text-center sm:text-left">
              <div class="text-xs font-semibold truncate" style="color: var(--text-primary);">
                {{ importFilePath || t.dndPrompt }}
              </div>
              <div class="text-[10px]" style="color: var(--text-muted);">
                {{ importFilePath ? t.clickToChange : t.dndSubPrompt }}
              </div>
            </div>
            <button
              type="button"
              class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition flex-shrink-0"
              style="background-color: var(--bg-surface); color: var(--text-primary); border-color: var(--border-subtle);"
              @click.stop="browseFile"
            >
              {{ t.browse }}
            </button>
          </div>

          <!-- Metadata Fields -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
                {{ t.mediaTitle }}
              </label>
              <input
                v-model="importTitle"
                type="text"
                :placeholder="t.titlePlaceholder"
                class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              />
            </div>
            <div>
              <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
                {{ t.tagsLabel }}
              </label>
              <input
                v-model="importTags"
                type="text"
                :placeholder="t.tagsPlaceholder"
                class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              />
            </div>
          </div>

          <div class="flex justify-end pt-1">
            <button
              @click="addMedia"
              :disabled="!importFilePath || isImporting"
              class="px-5 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              style="background-color: var(--accent-brass); color: var(--bg-primary);"
            >
              <span v-if="isImporting">⏳ {{ t.importing }}</span>
              <span v-else>➕ {{ t.addToLibrary }}</span>
            </button>
          </div>
        </div>

        <!-- Search & Filter Card -->
        <div
          class="p-5 rounded-2xl border shadow-xl space-y-4"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
              🔍 {{ t.searchSection }}
            </h3>
            <!-- Export Buttons -->
            <div class="flex items-center gap-2">
              <button
                @click="exportCatalog('json')"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
                style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
              >
                📥 {{ t.exportJson }}
              </button>
              <button
                @click="exportCatalog('csv')"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
                style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
              >
                📄 {{ t.exportCsv }}
              </button>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-12 gap-3">
            <div class="sm:col-span-6">
              <input
                v-model="searchQuery"
                @keyup.enter="performSearch"
                type="text"
                :placeholder="t.searchPlaceholder"
                class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              />
            </div>
            <div class="sm:col-span-4">
              <input
                v-model="searchTags"
                @keyup.enter="performSearch"
                type="text"
                :placeholder="t.searchTagsPlaceholder"
                class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              />
            </div>
            <div class="sm:col-span-2">
              <select
                v-model="searchFormat"
                @change="performSearch"
                class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              >
                <option value="All">{{ t.allFormats }}</option>
                <option value="mp4">MP4</option>
                <option value="mp3">MP3</option>
                <option value="mkv">MKV</option>
                <option value="webm">WebM</option>
                <option value="wav">WAV</option>
                <option value="flac">FLAC</option>
                <option value="aac">AAC</option>
                <option value="mov">MOV</option>
              </select>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              @click="performSearch"
              class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer"
              style="background-color: var(--accent-brass); color: var(--bg-primary);"
            >
              <span>🔍</span> {{ t.searchBtn }}
            </button>
            <button
              @click="resetSearch"
              class="px-4 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
              style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
            >
              ↺ {{ t.resetBtn }}
            </button>
          </div>
        </div>

        <!-- Error Panel -->
        <ErrorPanel
          :show="Boolean(errorMessage)"
          :message="errorMessage"
          @retry="performSearch"
        />

        <!-- Media Results List Card -->
        <div
          class="p-5 rounded-2xl border shadow-xl space-y-4"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
              📁 {{ t.resultsTitle }}
            </h3>
            <span class="text-xs font-mono" style="color: var(--accent-brass);">
              {{ mediaItems.length }} {{ t.itemsFound }}
            </span>
          </div>

          <!-- Empty State -->
          <div
            v-if="mediaItems.length === 0"
            class="p-12 text-center rounded-xl border border-dashed space-y-2"
            style="background-color: var(--bg-card); border-color: var(--border-subtle);"
          >
            <div class="text-3xl">📭</div>
            <div class="text-xs font-bold" style="color: var(--text-primary);">{{ t.noMediaFound }}</div>
            <div class="text-[11px]" style="color: var(--text-muted);">{{ t.noMediaSubtext }}</div>
          </div>

          <!-- Result Items -->
          <div v-else class="space-y-3">
            <div
              v-for="item in mediaItems"
              :key="item.id"
              class="p-4 rounded-xl border transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
              style="background-color: var(--bg-card); border-color: var(--border-subtle);"
            >
              <!-- Thumbnail & Media Details -->
              <div class="flex items-start gap-3 min-w-0 flex-1">
                <div
                  class="w-14 h-14 rounded-lg flex items-center justify-center font-mono font-bold text-xs flex-shrink-0 border uppercase"
                  style="background-color: var(--bg-surface); color: var(--accent-brass); border-color: var(--border-brass);"
                >
                  {{ item.format || 'FILE' }}
                </div>
                <div class="min-w-0 flex-1 space-y-1">
                  <div class="text-xs font-bold truncate" style="color: var(--text-primary);">
                    {{ item.title || getFilename(item.file_path) }}
                  </div>
                  <!-- Metrics row -->
                  <div class="flex flex-wrap items-center gap-2 text-[10px] font-mono" style="color: var(--text-muted);">
                    <span
                      class="px-1.5 py-0.5 rounded font-bold uppercase"
                      style="background-color: var(--bg-surface); color: var(--accent-brass);"
                    >
                      {{ item.format || 'N/A' }}
                    </span>
                    <span>•</span>
                    <span>{{ formatDuration(item.duration) }}</span>
                    <span>•</span>
                    <span>{{ formatSize(item.size) }}</span>
                    <span v-if="item.width && item.height">• {{ item.width }}x{{ item.height }}</span>
                    <span v-else-if="item.sample_rate">• {{ item.sample_rate }} Hz</span>
                  </div>
                  <!-- Tags -->
                  <div v-if="item.tags && item.tags.length > 0" class="flex flex-wrap gap-1 pt-1">
                    <span
                      v-for="tag in item.tags"
                      :key="tag"
                      class="text-[9px] px-1.5 py-0.2 rounded"
                      style="background-color: var(--bg-surface); color: var(--text-secondary);"
                    >
                      #{{ tag }}
                    </span>
                  </div>
                  <!-- Path preview -->
                  <div class="text-[9px] font-mono truncate" style="color: var(--text-muted);">
                    {{ item.file_path }}
                  </div>
                </div>
              </div>

              <!-- Item Actions -->
              <div class="flex items-center gap-1.5 flex-wrap flex-shrink-0 w-full sm:w-auto justify-end">
                <button
                  @click="openFile(item.file_path)"
                  class="px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border transition hover:opacity-90 cursor-pointer"
                  style="background-color: var(--bg-surface); color: var(--text-primary); border-color: var(--border-subtle);"
                  :title="t.openFile"
                >
                  ▶ {{ t.open }}
                </button>
                <button
                  @click="openFolder(item.file_path)"
                  class="px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border transition hover:opacity-90 cursor-pointer"
                  style="background-color: var(--bg-surface); color: var(--text-primary); border-color: var(--border-subtle);"
                  :title="t.openFolder"
                >
                  📂
                </button>
                <button
                  v-if="selectedCollectionId"
                  @click="addToCollection(item.id, selectedCollectionId)"
                  class="px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border transition hover:opacity-90 cursor-pointer"
                  style="background-color: var(--bg-surface); color: var(--accent-brass); border-color: var(--border-brass);"
                  :title="t.addToCollection"
                >
                  ＋
                </button>
                <button
                  @click="deleteMedia(item.id)"
                  class="px-2 py-1.5 rounded-lg text-[11px] font-semibold border transition hover:opacity-90 cursor-pointer"
                  style="background-color: var(--error-bg); color: var(--status-error); border-color: var(--status-error);"
                  :title="t.delete"
                >
                  ✕
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Sidebar (4 cols on large screens) -->
      <div class="lg:col-span-4 space-y-6">
        <!-- Stats Card -->
        <div
          class="p-5 rounded-2xl border shadow-xl space-y-4"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
              📊 {{ t.statsTitle }}
            </h3>
            <button
              @click="loadStats"
              class="text-xs px-2 py-1 rounded border transition hover:opacity-80 cursor-pointer"
              style="background-color: var(--bg-card); color: var(--text-muted); border-color: var(--border-subtle);"
            >
              ↻
            </button>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
              <div class="text-[10px] uppercase font-bold" style="color: var(--text-muted);">{{ t.totalItems }}</div>
              <div class="text-base font-bold font-mono mt-0.5" style="color: var(--accent-brass);">
                {{ stats.total_items ?? 0 }}
              </div>
            </div>
            <div class="p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
              <div class="text-[10px] uppercase font-bold" style="color: var(--text-muted);">{{ t.totalSize }}</div>
              <div class="text-base font-bold font-mono mt-0.5" style="color: var(--accent-brass);">
                {{ formatSize(stats.total_size ?? 0) }}
              </div>
            </div>
            <div class="p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
              <div class="text-[10px] uppercase font-bold" style="color: var(--text-muted);">{{ t.collectionsCount }}</div>
              <div class="text-base font-bold font-mono mt-0.5" style="color: var(--text-primary);">
                {{ collections.length }}
              </div>
            </div>
            <div class="p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
              <div class="text-[10px] uppercase font-bold" style="color: var(--text-muted);">{{ t.duplicatesCount }}</div>
              <div class="text-base font-bold font-mono mt-0.5" style="color: var(--status-warning);">
                {{ stats.duplicate_groups ?? 0 }}
              </div>
            </div>
          </div>
        </div>

        <!-- Collections Card -->
        <div
          class="p-5 rounded-2xl border shadow-xl space-y-4"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
              🗂 {{ t.collectionsTitle }}
            </h3>
            <span class="text-xs font-mono" style="color: var(--text-muted);">{{ collections.length }}</span>
          </div>

          <!-- Create Collection Input -->
          <div class="flex gap-2">
            <input
              v-model="newCollectionName"
              @keyup.enter="createCollection"
              type="text"
              :placeholder="t.newCollectionPlaceholder"
              class="flex-1 px-3 py-2 rounded-xl text-xs border focus:outline-none"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
            <button
              @click="createCollection"
              :disabled="!newCollectionName.trim()"
              class="px-3 py-2 rounded-xl text-xs font-bold transition cursor-pointer disabled:opacity-50"
              style="background-color: var(--accent-brass); color: var(--bg-primary);"
            >
              ➕
            </button>
          </div>

          <!-- Target Collection Selector for Add Actions -->
          <div class="space-y-1.5">
            <label class="block text-[10px] uppercase font-bold" style="color: var(--text-muted);">
              {{ t.targetCollection }}
            </label>
            <select
              v-model="selectedCollectionId"
              class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option :value="null">{{ t.noCollectionSelected }}</option>
              <option v-for="c in collections" :key="c.id" :value="c.id">
                📁 {{ c.name }}
              </option>
            </select>
          </div>

          <!-- Collection List -->
          <div class="space-y-2 max-h-56 overflow-y-auto pr-1">
            <div
              v-if="collections.length === 0"
              class="p-4 text-center text-xs rounded-xl"
              style="color: var(--text-muted); background-color: var(--bg-card);"
            >
              {{ t.noCollections }}
            </div>
            <div
              v-for="c in collections"
              :key="c.id"
              class="p-3 rounded-xl border flex items-center justify-between gap-2 transition"
              style="background-color: var(--bg-card); border-color: var(--border-subtle);"
            >
              <div class="min-w-0 flex-1 cursor-pointer" @click="filterByCollection(c.id)">
                <div class="text-xs font-bold truncate" style="color: var(--text-primary);">📁 {{ c.name }}</div>
                <div class="text-[10px] truncate" style="color: var(--text-muted);">
                  {{ c.description || t.collectionEmptyDescription }}
                </div>
              </div>
              <button
                @click="deleteCollection(c.id)"
                class="p-1 rounded text-xs transition hover:opacity-80 cursor-pointer"
                style="color: var(--status-error);"
                title="Delete Collection"
              >
                ✕
              </button>
            </div>
          </div>
        </div>

        <!-- Recent Searches Card -->
        <div
          class="p-5 rounded-2xl border shadow-xl space-y-3"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
              🕒 {{ t.recentSearchesTitle }}
            </h3>
          </div>

          <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
            <div
              v-if="recentSearches.length === 0"
              class="p-4 text-center text-xs rounded-xl"
              style="color: var(--text-muted); background-color: var(--bg-card);"
            >
              {{ t.noRecentSearches }}
            </div>
            <button
              v-for="(s, idx) in recentSearches"
              :key="idx"
              @click="applyRecentSearch(s.query_text)"
              class="w-full px-3 py-2 rounded-xl text-left text-xs border transition hover:opacity-90 flex items-center justify-between cursor-pointer"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-secondary);"
            >
              <span class="truncate">🔎 {{ s.query_text || t.allMedia }}</span>
              <span class="text-[10px] font-mono flex-shrink-0" style="color: var(--accent-brass);">
                {{ s.result_count }}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiClient } from '../services/apiClient'
import { useToastStore } from '../stores/toastStore'
import ErrorPanel from './ErrorPanel.vue'

const toast = useToastStore()

const t = {
  importTitle: 'Medya İçe Aktar',
  importSubtitle: 'Yerel dosyayı tarayıp kütüphaneye ekleyin',
  dndPrompt: 'Dosyayı buraya sürükleyip bırakın veya seçmek için tıklayın',
  dndSubPrompt: 'MP4, MKV, MP3, WAV, FLAC vb. medya dosyaları',
  clickToChange: 'Farklı bir dosya seçmek için tıklayın',
  browse: 'Gözat',
  mediaTitle: 'Başlık (İsteğe bağlı)',
  titlePlaceholder: 'Otomatik dosya adını kullan',
  tagsLabel: 'Etiketler (Virgülle ayrılmış)',
  tagsPlaceholder: 'video, podcast, klip, eğitim',
  importing: 'İçe Aktarılıyor...',
  addToLibrary: 'Kütüphaneye Ekle',
  searchSection: 'Arama ve Filtreleme',
  exportJson: 'JSON Dışa Aktar',
  exportCsv: 'CSV Dışa Aktar',
  searchPlaceholder: 'Başlık veya dosya yolu ile ara...',
  searchTagsPlaceholder: 'Etiket ile ara...',
  allFormats: 'Tüm Formatlar',
  searchBtn: 'Ara',
  resetBtn: 'Sıfırla',
  resultsTitle: 'Kütüphane Kayıtları',
  itemsFound: 'öğe bulundu',
  noMediaFound: 'Kayıt bulunamadı',
  noMediaSubtext: 'Arama filtrenizi değiştirin veya yeni bir medya dosyası içe aktarın.',
  openFile: 'Varsayılan oynatıcıda aç',
  open: 'Aç',
  openFolder: 'Dosya klasörünü aç',
  addToCollection: 'Hedef koleksiyona ekle',
  delete: 'Sil',
  statsTitle: 'Kütüphane İstatistikleri',
  totalItems: 'Toplam Öğe',
  totalSize: 'Toplam Boyut',
  collectionsCount: 'Koleksiyonlar',
  duplicatesCount: 'Yinelenen Gruplar',
  collectionsTitle: 'Koleksiyonlar',
  newCollectionPlaceholder: 'Yeni koleksiyon adı...',
  targetCollection: 'Hedef Koleksiyon (Öğe Ekleme İçin)',
  noCollectionSelected: 'Koleksiyon seçilmedi',
  noCollections: 'Henüz koleksiyon oluşturulmadı.',
  collectionEmptyDescription: 'Açıklama yok',
  recentSearchesTitle: 'Son Aramalar',
  noRecentSearches: 'Henüz arama geçmişi yok.',
  allMedia: 'Tüm Medyalar'
}

// State
const isDragging = ref(false)
const isImporting = ref(false)
const importFilePath = ref('')
const importTitle = ref('')
const importTags = ref('')

const searchQuery = ref('')
const searchTags = ref('')
const searchFormat = ref('All')

const mediaItems = ref<any[]>([])
const stats = ref<any>({})
const collections = ref<any[]>([])
const recentSearches = ref<any[]>([])
const selectedCollectionId = ref<number | null>(null)
const newCollectionName = ref('')
const errorMessage = ref('')

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDuration(seconds: number): string {
  if (!seconds) return '0:00'
  const sec = Math.floor(seconds)
  const min = Math.floor(sec / 60)
  const remSec = sec % 60
  return `${min}:${remSec < 10 ? '0' : ''}${remSec}`
}

function getFilename(filePath: string): string {
  if (!filePath) return ''
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

async function browseFile() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Media', extensions: ['mp4', 'mkv', 'webm', 'mov', 'avi', 'mp3', 'wav', 'flac', 'aac', 'm4a'] }]
    })
    if (selected && typeof selected === 'string') {
      importFilePath.value = selected
      if (!importTitle.value) {
        importTitle.value = getFilename(selected).replace(/\.[^/.]+$/, '')
      }
    }
  } catch {
    const manual = prompt('Dosya yolunu girin:', importFilePath.value)
    if (manual) importFilePath.value = manual
  }
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer && e.dataTransfer.files.length > 0) {
    const file = e.dataTransfer.files[0]
    importFilePath.value = (file as any).path || file.name
    if (!importTitle.value) {
      importTitle.value = file.name.replace(/\.[^/.]+$/, '')
    }
  }
}

async function addMedia() {
  if (!importFilePath.value) return
  isImporting.value = true
  errorMessage.value = ''
  try {
    const tags = importTags.value.split(',').map(t => t.trim()).filter(Boolean)
    await apiClient.addMediaToLibrary({
      file_path: importFilePath.value,
      title: importTitle.value || undefined,
      tags
    })
    toast.success('Medya başarıyla kütüphaneye eklendi')
    importFilePath.value = ''
    importTitle.value = ''
    importTags.value = ''
    await loadMedia()
    await loadStats()
  } catch (err: any) {
    errorMessage.value = err.message || 'Medya içe aktarılamadı'
    toast.error(errorMessage.value)
  } finally {
    isImporting.value = false
  }
}

async function loadMedia() {
  errorMessage.value = ''
  try {
    mediaItems.value = await apiClient.searchLibrary({
      q: searchQuery.value || undefined,
      tags: searchTags.value || undefined,
      format: searchFormat.value !== 'All' ? searchFormat.value : undefined
    })
  } catch (err: any) {
    errorMessage.value = err.message || 'Kütüphane verileri yüklenemedi'
  }
}

async function performSearch() {
  await loadMedia()
  await loadRecentSearches()
}

async function resetSearch() {
  searchQuery.value = ''
  searchTags.value = ''
  searchFormat.value = 'All'
  await loadMedia()
}

async function applyRecentSearch(query: string) {
  searchQuery.value = query || ''
  await performSearch()
}

async function deleteMedia(id: number) {
  if (!confirm('Bu medyayı kütüphaneden silmek istediğinize emin misiniz?')) return
  try {
    await apiClient.deleteMediaFromLibrary(id)
    toast.success('Medya kütüphaneden silindi')
    await loadMedia()
    await loadStats()
  } catch (err: any) {
    toast.error(err.message || 'Silme başarısız')
  }
}

async function openFile(path: string) {
  try {
    await apiClient.openFile(path)
  } catch (err: any) {
    toast.error(err.message || 'Dosya açılamadı')
  }
}

async function openFolder(path: string) {
  try {
    await apiClient.openFolder(path)
  } catch (err: any) {
    toast.error(err.message || 'Klasör açılamadı')
  }
}

async function loadStats() {
  try {
    stats.value = await apiClient.getLibraryStats()
  } catch {
    // Handling
  }
}

async function loadCollections() {
  try {
    collections.value = await apiClient.getCollections()
  } catch {
    // Handling
  }
}

async function createCollection() {
  if (!newCollectionName.value.trim()) return
  try {
    await apiClient.createCollection({ name: newCollectionName.value.trim() })
    toast.success(`Koleksiyon oluşturuldu: ${newCollectionName.value}`)
    newCollectionName.value = ''
    await loadCollections()
    await loadStats()
  } catch (err: any) {
    toast.error(err.message || 'Koleksiyon oluşturulamadı')
  }
}

async function deleteCollection(id: number) {
  if (!confirm('Koleksiyonu silmek istediğinize emin misiniz?')) return
  try {
    await apiClient.deleteCollection(id)
    toast.success('Koleksiyon silindi')
    await loadCollections()
    await loadStats()
  } catch (err: any) {
    toast.error(err.message || 'Silme başarısız')
  }
}

async function addToCollection(mediaId: number, collectionId: number) {
  try {
    await apiClient.addItemToCollection(collectionId, mediaId)
    toast.success('Öğe koleksiyona eklendi')
  } catch (err: any) {
    toast.error(err.message || 'Koleksiyona eklenemedi')
  }
}

async function filterByCollection(collectionId: number) {
  try {
    mediaItems.value = await apiClient.getCollectionItems(collectionId)
    toast.info('Koleksiyon öğeleri listelendi')
  } catch (err: any) {
    toast.error(err.message || 'Koleksiyon öğeleri alınamadı')
  }
}

async function loadRecentSearches() {
  try {
    recentSearches.value = await apiClient.getRecentLibrarySearches()
  } catch {
    // Handling
  }
}

async function exportCatalog(fmt: 'json' | 'csv') {
  try {
    const res = await apiClient.exportLibrary({ format: fmt })
    toast.success(`Dışa aktarma tamamlandı: ${res.output_file}`)
  } catch (err: any) {
    toast.error(err.message || 'Dışa aktarma başarısız')
  }
}

onMounted(async () => {
  await Promise.all([loadMedia(), loadStats(), loadCollections(), loadRecentSearches()])
})
</script>
