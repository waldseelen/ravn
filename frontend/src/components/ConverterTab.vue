<template>
  <div class="space-y-6">
    <!-- Converter Settings Card -->
    <div
      class="p-6 rounded-2xl border space-y-6 shadow-sm"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <!-- Input File DND Zone -->
      <div class="space-y-2">
        <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
          📥 {{ t.inputFileLabel }}
        </label>
        <div
          class="p-5 rounded-2xl border-2 border-dashed transition-all flex flex-col sm:flex-row items-center justify-between gap-4"
          :class="{ 'ring-2': isDragging }"
          :style="{
            backgroundColor: 'var(--bg-input)',
            borderColor: isDragging ? 'var(--accent-brass)' : 'var(--border-subtle)'
          }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
        >
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <span class="text-2xl" style="color: var(--accent-brass);">📁</span>
            <div class="min-w-0 flex-1">
              <input
                v-model="inputFile"
                type="text"
                :placeholder="t.inputPlaceholder"
                class="w-full text-xs font-mono bg-transparent border-none outline-none truncate"
                style="color: var(--text-primary);"
              />
              <p class="text-[11px]" style="color: var(--text-muted);">
                {{ inputFile ? inputFile : t.dndHint }}
              </p>
            </div>
          </div>

          <button
            @click="browseInputFile"
            class="px-4 py-2.5 rounded-xl border text-xs font-semibold hover:opacity-90 cursor-pointer shrink-0"
            style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
          >
            📂 {{ t.browse }}
          </button>
        </div>
      </div>

      <!-- Codecs and Parameters Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-2">
        <!-- Video Codec -->
        <div>
          <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
            🎬 {{ t.videoCodec }}
          </label>
          <select
            v-model="videoCodec"
            class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="h264">H.264 / AVC (libx264)</option>
            <option value="hevc">HEVC / H.265 (libx265)</option>
            <option value="vp9">VP9 (libvpx-vp9)</option>
            <option value="av1">AV1 (libaom-av1)</option>
            <option value="copy">Copy (Direct Stream Copy)</option>
          </select>
        </div>

        <!-- Audio Codec -->
        <div>
          <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
            🎵 {{ t.audioCodec }}
          </label>
          <select
            v-model="audioCodec"
            class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="aac">AAC (Standard Audio)</option>
            <option value="mp3">MP3 (libmp3lame)</option>
            <option value="opus">OPUS (High Quality Compact)</option>
            <option value="flac">FLAC (Lossless)</option>
            <option value="copy">Copy (Direct Audio Copy)</option>
          </select>
        </div>

        <!-- Quality / CRF -->
        <div>
          <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
            ✦ {{ t.videoQuality }}
          </label>
          <select
            v-model="videoQuality"
            class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="LOSSLESS">Kayıpsız / Lossless (CRF 0)</option>
            <option value="VERYHIGH">Çok Yüksek / Studio (CRF 18)</option>
            <option value="HIGH">Yüksek / High Quality (CRF 23)</option>
            <option value="MEDIUM">Orta / Balanced (CRF 28)</option>
            <option value="LOW">Düşük / Compact (CRF 33)</option>
            <option value="VERYLOW">Çok Düşük / Tiny (CRF 51)</option>
          </select>
        </div>

        <!-- Speed Preset -->
        <div>
          <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
            ⚡ {{ t.speedPreset }}
          </label>
          <select
            v-model="speedPreset"
            class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="ultrafast">ultrafast (Fastest render)</option>
            <option value="superfast">superfast</option>
            <option value="veryfast">veryfast</option>
            <option value="faster">faster</option>
            <option value="fast">fast (Recommended)</option>
            <option value="medium">medium</option>
            <option value="slow">slow (Better compression)</option>
            <option value="slower">slower</option>
            <option value="veryslow">veryslow</option>
          </select>
        </div>

        <!-- Hardware Acceleration -->
        <div>
          <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
            🚀 {{ t.hardwareAccel }}
          </label>
          <select
            v-model="hardwareAccel"
            class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="">Yok (Software / CPU)</option>
            <option value="nvenc">NVENC (NVIDIA GPU)</option>
            <option value="quicksync">Quick Sync (Intel QSV)</option>
            <option value="amf">AMF (AMD GPU)</option>
          </select>
        </div>

        <!-- Audio Bitrate -->
        <div>
          <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
            🎧 {{ t.audioBitrate }}
          </label>
          <select
            v-model="audioBitrate"
            class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="320k">320 kbps (High Fidelity)</option>
            <option value="256k">256 kbps</option>
            <option value="192k">192 kbps (Standard High)</option>
            <option value="128k">128 kbps (Balanced)</option>
            <option value="96k">96 kbps (Voice / Small)</option>
          </select>
        </div>
      </div>

      <!-- Output Destination -->
      <div class="space-y-2 pt-2 border-t" style="border-color: var(--border-subtle);">
        <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
          📤 {{ t.outputFileLabel }}
        </label>
        <div class="flex gap-3">
          <input
            v-model="outputFile"
            type="text"
            :placeholder="t.outputPlaceholder"
            class="flex-1 px-4 py-2.5 rounded-xl text-xs border outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
          <button
            @click="browseOutputFile"
            class="px-4 py-2.5 rounded-xl border text-xs font-semibold hover:opacity-90 cursor-pointer shrink-0"
            style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
          >
            📁 {{ t.browse }}
          </button>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center justify-between gap-3 pt-2">
        <button
          @click="clearForm"
          class="px-4 py-2.5 rounded-xl border text-xs font-semibold transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-secondary); border-color: var(--border-subtle);"
        >
          {{ t.clear }}
        </button>

        <button
          @click="startConversion"
          :disabled="!inputFile || isProcessing"
          class="px-8 py-2.5 text-xs font-bold rounded-xl shadow-lg transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
          style="background-color: var(--accent-brass); color: var(--bg-primary);"
        >
          <span>⇄</span>
          <span>{{ isProcessing ? t.converting : t.startConvert }}</span>
        </button>
      </div>

      <!-- Live Log Area -->
      <div v-if="logLines.length > 0" class="space-y-2 pt-2 border-t" style="border-color: var(--border-subtle);">
        <label class="block text-[11px] font-bold uppercase tracking-wider" style="color: var(--text-muted);">
          {{ t.processLog }}
        </label>
        <div
          class="p-4 rounded-xl font-mono text-[11px] max-h-36 overflow-y-auto space-y-1"
          style="background-color: var(--bg-card); border: 1px solid var(--border-subtle); color: var(--text-secondary);"
        >
          <div v-for="(line, idx) in logLines" :key="idx" class="truncate">
            {{ line }}
          </div>
        </div>
      </div>
    </div>

    <!-- Error Panel Integration -->
    <ErrorPanel
      v-if="errorInfo"
      :title="errorInfo.title"
      :message="errorInfo.message"
      :traceback="errorInfo.traceback"
      @retry="startConversion"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToastStore } from '../stores/toastStore'
import { apiClient } from '../services/apiClient'
import ErrorPanel from './ErrorPanel.vue'

const toastStore = useToastStore()

const t = {
  inputFileLabel: 'Source Media File',
  inputPlaceholder: 'Select or drag & drop media file here...',
  dndHint: 'Drag and drop any audio or video file here',
  browse: 'Browse File',
  videoCodec: 'Video Codec',
  audioCodec: 'Audio Codec',
  videoQuality: 'Video Quality (CRF)',
  speedPreset: 'Encoder Speed Preset',
  hardwareAccel: 'Hardware Acceleration',
  audioBitrate: 'Audio Bitrate',
  outputFileLabel: 'Output Destination File',
  outputPlaceholder: 'Auto-generated or custom output path',
  clear: 'Clear Form',
  startConvert: 'Start Conversion',
  converting: 'Transcoding Media...',
  processLog: 'Execution Log'
}

const inputFile = ref('')
const outputFile = ref('')
const videoCodec = ref('h264')
const audioCodec = ref('aac')
const videoQuality = ref('HIGH')
const speedPreset = ref('fast')
const hardwareAccel = ref('')
const audioBitrate = ref('192k')

const isDragging = ref(false)
const isProcessing = ref(false)
const logLines = ref<string[]>([])
const errorInfo = ref<{ title: string; message: string; traceback?: string } | null>(null)

function handleDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    const f = e.dataTransfer.files[0]
    inputFile.value = (f as any).path || f.name
    toastStore.info(`Loaded source file: ${f.name}`)
  }
}

async function browseInputFile() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Media Files', extensions: ['mp4', 'mkv', 'avi', 'mov', 'webm', 'mp3', 'wav', 'flac', 'm4a', 'opus'] }]
    })
    if (selected && typeof selected === 'string') {
      inputFile.value = selected
      toastStore.success(`Selected file: ${selected}`)
    }
  } catch {
    toastStore.info('Enter local file path directly.')
  }
}

async function browseOutputFile() {
  try {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const selected = await save({
      filters: [{ name: 'Media Output', extensions: ['mp4', 'mkv', 'webm', 'mp3', 'flac'] }]
    })
    if (selected && typeof selected === 'string') {
      outputFile.value = selected
    }
  } catch {
    toastStore.info('Enter destination path directly.')
  }
}

function clearForm() {
  inputFile.value = ''
  outputFile.value = ''
  logLines.value = []
  errorInfo.value = null
}

async function startConversion() {
  if (!inputFile.value.trim()) return
  isProcessing.value = true
  errorInfo.value = null
  logLines.value.push(`[${new Date().toLocaleTimeString()}] Queuing transcode task: ${inputFile.value}`)

  try {
    const res = await apiClient.startConversion({
      input_file: inputFile.value.trim(),
      output_file: outputFile.value.trim() || undefined,
      video_codec: videoCodec.value,
      audio_codec: audioCodec.value,
      video_quality: videoQuality.value,
      audio_bitrate: audioBitrate.value,
      preset: speedPreset.value,
      hardware_accel: hardwareAccel.value || undefined
    })

    logLines.value.push(`[${new Date().toLocaleTimeString()}] Task enqueued: ID ${res.task_id}`)
    logLines.value.push(`[${new Date().toLocaleTimeString()}] Target Output: ${res.output_file}`)
    toastStore.success(`Conversion task queued (ID: ${res.task_id.substring(0, 8)})`)
  } catch (e: any) {
    errorInfo.value = {
      title: 'Transcoding Failed to Start',
      message: e.message || 'Could not queue FFmpeg conversion task.',
      traceback: String(e)
    }
    toastStore.error('Conversion failed')
  } finally {
    isProcessing.value = false
  }
}
</script>
