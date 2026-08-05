<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header / Mode Switcher -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#1E1E1E] p-4 rounded-2xl border border-[#3A3330] shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-[#C99A5B]/10 text-[#C99A5B] rounded-xl border border-[#C99A5B]/20">
          <span class="text-xl">↓</span>
        </div>
        <div>
          <h1 class="text-lg font-bold text-[#E8E0D8]">Media Acquisition</h1>
          <p class="text-xs text-[#A09080]">Single URL, Playlist Review, Batch Links & Torrent/Magnet</p>
        </div>
      </div>

      <!-- Mode Selector (Orijinal CustomTkinter Modes) -->
      <div class="flex bg-[#141414] p-1 rounded-xl border border-[#3A3330]">
        <button
          v-for="mode in modes"
          :key="mode.id"
          @click="activeMode = mode.id"
          class="px-4 py-2 text-xs font-semibold rounded-lg transition-all"
          :class="activeMode === mode.id ? 'bg-[#C99A5B] text-[#141414] shadow-md' : 'text-[#B8A99A] hover:text-[#E8E0D8]'"
        >
          {{ mode.label }}
        </button>
      </div>
    </div>

    <!-- Mode 1: Single URL & Playlist -->
    <div v-if="activeMode === 'single'" class="space-y-6">
      <div class="bg-[#1E1E1E] p-6 rounded-2xl border border-[#3A3330] space-y-4">
        <label class="block text-xs font-semibold uppercase tracking-wider text-[#A09080]">Target Media URL or Playlist Link</label>
        <div class="flex gap-3">
          <input
            v-model="singleUrl"
            type="text"
            placeholder="https://www.youtube.com/watch?v=... or playlist link"
            class="flex-1 px-4 py-3 bg-[#141414] border border-[#3A3330] rounded-xl text-[#E8E0D8] placeholder-[#7A6B60] text-xs focus:outline-none focus:border-[#C99A5B]"
          />
          <button
            @click="fetchInfo"
            :disabled="!singleUrl || loadingInfo"
            class="px-5 py-3 bg-[#252525] hover:bg-[#2A2A2A] text-[#E8E0D8] text-xs font-semibold rounded-xl border border-[#3A3330] transition disabled:opacity-50"
          >
            {{ loadingInfo ? 'Analyzing...' : 'Fetch Info' }}
          </button>
          <button
            @click="startSingleDownload"
            :disabled="!singleUrl || downloading"
            class="px-8 py-3 bg-[#C99A5B] hover:bg-[#A87C42] text-[#141414] text-xs font-bold rounded-xl shadow-lg shadow-[#C99A5B]/20 transition disabled:opacity-50"
          >
            {{ downloading ? 'Starting...' : 'Download Now' }}
          </button>
        </div>

        <!-- Single Options Grid -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2 border-t border-[#3A3330]/50">
          <div>
            <span class="block text-[11px] font-semibold text-[#A09080] mb-1">Format</span>
            <select v-model="selectedFormat" class="w-full bg-[#141414] border border-[#3A3330] rounded-lg px-3 py-2 text-xs text-[#E8E0D8]">
              <option value="mp4">MP4 (Video)</option>
              <option value="mkv">MKV (Video)</option>
              <option value="webm">WebM (Video)</option>
              <option value="mp3">MP3 (Audio Only)</option>
              <option value="m4a">M4A (Audio Only)</option>
              <option value="flac">FLAC (Lossless Audio)</option>
            </select>
          </div>
          <div>
            <span class="block text-[11px] font-semibold text-[#A09080] mb-1">Quality Preset</span>
            <select v-model="selectedQuality" class="w-full bg-[#141414] border border-[#3A3330] rounded-lg px-3 py-2 text-xs text-[#E8E0D8]">
              <option value="best">Best Available (Highest)</option>
              <option value="2160p">4K Ultra HD (2160p)</option>
              <option value="1080p">Full HD (1080p)</option>
              <option value="720p">HD (720p)</option>
              <option value="480p">SD (480p)</option>
            </select>
          </div>
          <div>
            <span class="block text-[11px] font-semibold text-[#A09080] mb-1">Naming Template</span>
            <select v-model="namingTemplate" class="w-full bg-[#141414] border border-[#3A3330] rounded-lg px-3 py-2 text-xs text-[#E8E0D8]">
              <option value="default">{title} [{id}]</option>
              <option value="clean">{title}</option>
              <option value="numbered">{playlist_index} - {title}</option>
              <option value="artist_title">{artist} - {title}</option>
            </select>
          </div>
          <div class="flex flex-col justify-end space-y-2">
            <label class="flex items-center gap-2 text-xs text-[#B8A99A]">
              <input v-model="embedMetadata" type="checkbox" class="rounded bg-[#141414] border-[#3A3330] text-[#C99A5B]" />
              Embed Metadata & Cover
            </label>
            <label class="flex items-center gap-2 text-xs text-[#B8A99A]">
              <input v-model="embedSubtitles" type="checkbox" class="rounded bg-[#141414] border-[#3A3330] text-[#C99A5B]" />
              Download Subtitles (.srt)
            </label>
          </div>
        </div>
      </div>

      <!-- Playlist Preview / Extracted Info Panel -->
      <div v-if="mediaInfo" class="bg-[#1E1E1E] p-6 rounded-2xl border border-[#3A3330] space-y-4">
        <div class="flex items-center justify-between border-b border-[#3A3330] pb-3">
          <h3 class="text-xs font-bold uppercase tracking-wider text-[#E8E0D8]">Media Preview & Metadata</h3>
          <span class="text-[10px] text-[#C99A5B] bg-[#C99A5B]/10 px-2.5 py-1 rounded-full border border-[#C99A5B]/20 font-mono">
            {{ mediaInfo.extractor || 'yt-dlp' }}
          </span>
        </div>
        <div class="flex gap-4">
          <img v-if="mediaInfo.thumbnail" :src="mediaInfo.thumbnail" class="w-40 h-24 object-cover rounded-xl border border-[#3A3330]" />
          <div class="space-y-1">
            <h4 class="text-sm font-bold text-[#E8E0D8]">{{ mediaInfo.title }}</h4>
            <p class="text-xs text-[#A09080]">Uploader: {{ mediaInfo.uploader || 'N/A' }} | Duration: {{ mediaInfo.duration || 'N/A' }}s</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Mode 2: Torrent & Magnet -->
    <div v-if="activeMode === 'torrent'" class="space-y-6">
      <div class="bg-[#1E1E1E] p-6 rounded-2xl border border-[#3A3330] space-y-4">
        <h3 class="text-xs font-bold uppercase tracking-wider text-[#E8E0D8]">Magnet URI or Torrent File</h3>
        <div class="flex gap-3">
          <input
            v-model="torrentUri"
            type="text"
            placeholder="magnet:?xt=urn:btih:... or path to .torrent file"
            class="flex-1 px-4 py-3 bg-[#141414] border border-[#3A3330] rounded-xl text-[#E8E0D8] text-xs focus:outline-none focus:border-[#C99A5B]"
          />
          <button @click="startTorrentDownload" class="px-8 py-3 bg-[#22c55e] hover:bg-[#16a34a] text-[#141414] font-bold text-xs rounded-xl shadow-lg transition">
            Start Torrent
          </button>
        </div>
        <div class="flex gap-6 text-xs text-[#B8A99A] pt-2">
          <label class="flex items-center gap-2">
            Download Mode:
            <select v-model="torrentMode" class="bg-[#141414] border border-[#3A3330] rounded px-2 py-1 text-xs text-[#E8E0D8]">
              <option value="FULL">FULL (Complete Download)</option>
              <option value="SEQUENTIAL">SEQUENTIAL (Ordered for Playback)</option>
              <option value="STREAM">STREAM (Local HTTP Stream)</option>
            </select>
          </label>
        </div>
      </div>
    </div>

    <!-- Mode 3: Batch Links -->
    <div v-if="activeMode === 'batch'" class="space-y-4 bg-[#1E1E1E] p-6 rounded-2xl border border-[#3A3330]">
      <h3 class="text-xs font-bold uppercase tracking-wider text-[#E8E0D8]">Batch Links (One URL per line)</h3>
      <textarea
        v-model="batchUrls"
        rows="6"
        placeholder="https://www.youtube.com/watch?v=1&#10;https://www.youtube.com/watch?v=2"
        class="w-full p-4 bg-[#141414] border border-[#3A3330] rounded-xl text-[#E8E0D8] text-xs font-mono focus:outline-none focus:border-[#C99A5B]"
      ></textarea>
      <div class="flex justify-end">
        <button @click="startBatchDownload" class="px-8 py-3 bg-[#C99A5B] hover:bg-[#A87C42] text-[#141414] font-bold text-xs rounded-xl shadow-lg">
          Process Batch Queue
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { apiClient } from '../services/apiClient'

const modes = [
  { id: 'single', label: 'Single / Playlist' },
  { id: 'torrent', label: 'Torrent & Magnet' },
  { id: 'batch', label: 'Batch URLs' }
]

const activeMode = ref('single')
const singleUrl = ref('')
const selectedFormat = ref('mp4')
const selectedQuality = ref('best')
const namingTemplate = ref('default')
const embedMetadata = ref(true)
const embedSubtitles = ref(false)
const loadingInfo = ref(false)
const downloading = ref(false)
const mediaInfo = ref<any>(null)

const torrentUri = ref('')
const torrentMode = ref('FULL')
const batchUrls = ref('')

async function fetchInfo() {
  if (!singleUrl.value) return
  loadingInfo.value = true
  try {
    mediaInfo.value = await apiClient.extractInfo(singleUrl.value)
  } catch (e: any) {
    alert('Metadata extraction failed: ' + e.message)
  } finally {
    loadingInfo.value = false
  }
}

async function startSingleDownload() {
  if (!singleUrl.value) return
  downloading.value = true
  try {
    await apiClient.startDownload({
      url: singleUrl.value,
      output_dir: 'downloads',
      format: selectedFormat.value,
      quality: selectedQuality.value,
      embed_metadata: embedMetadata.value
    })
    singleUrl.value = ''
    alert('Download task enqueued!')
  } catch (e: any) {
    alert('Failed to start download: ' + e.message)
  } finally {
    downloading.value = false
  }
}

async function startTorrentDownload() {
  if (!torrentUri.value) return
  alert(`Starting Torrent download in ${torrentMode.value} mode...`)
}

async function startBatchDownload() {
  if (!batchUrls.value) return
  alert('Processing batch queue...')
}
</script>
