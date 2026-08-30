<template>
  <div class="space-y-6">
    <!-- Source & Destination Card with DND -->
    <div
      class="p-6 rounded-2xl border space-y-4 shadow-sm"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Input File DND -->
        <div class="space-y-2">
          <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
            📥 {{ t.inputLabel }}
          </label>
          <div class="flex gap-2">
            <input
              v-model="inputPath"
              type="text"
              :placeholder="t.inputPlaceholder"
              class="flex-1 px-4 py-2.5 rounded-xl text-xs border outline-none font-mono"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
            <button
              @click="browseInput"
              class="px-3.5 py-2 rounded-xl border text-xs font-semibold hover:opacity-90 cursor-pointer shrink-0"
              style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
            >
              📁
            </button>
          </div>
        </div>

        <!-- Output File -->
        <div class="space-y-2">
          <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
            📤 {{ t.outputLabel }}
          </label>
          <div class="flex gap-2">
            <input
              v-model="outputPath"
              type="text"
              :placeholder="t.outputPlaceholder"
              class="flex-1 px-4 py-2.5 rounded-xl text-xs border outline-none font-mono"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
            <button
              @click="browseOutput"
              class="px-3.5 py-2 rounded-xl border text-xs font-semibold hover:opacity-90 cursor-pointer shrink-0"
              style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
            >
              📁
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 4 Collapsible Panels (Progressive Disclosure) -->
    <div class="space-y-4">
      <!-- 1. Quick Helpers (6 buttons) -->
      <div
        class="rounded-2xl border overflow-hidden shadow-sm transition"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <button
          @click="openPanels.quick = !openPanels.quick"
          class="w-full flex items-center justify-between p-4 text-xs font-bold transition text-left cursor-pointer hover:opacity-90"
          style="background-color: var(--bg-card); color: var(--text-primary);"
        >
          <span class="flex items-center gap-2">
            <span>⚡</span>
            <span>{{ t.panelQuick }} (6)</span>
          </span>
          <span class="text-xs" style="color: var(--accent-brass);">{{ openPanels.quick ? '▲' : '▼' }}</span>
        </button>

        <div v-show="openPanels.quick" class="p-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          <button
            v-for="op in quickOps"
            :key="op.id"
            @click="runHelper('quick', op.id, op.name)"
            :disabled="!inputPath || runningOp === op.id"
            class="p-3.5 rounded-xl border text-center text-xs font-semibold flex flex-col items-center justify-center gap-2 transition hover:opacity-90 disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <span class="text-xl">{{ op.icon }}</span>
            <span class="truncate w-full">{{ op.name }}</span>
          </button>
        </div>
      </div>

      <!-- 2. Audio Utilities (6 buttons) -->
      <div
        class="rounded-2xl border overflow-hidden shadow-sm transition"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <button
          @click="openPanels.audio = !openPanels.audio"
          class="w-full flex items-center justify-between p-4 text-xs font-bold transition text-left cursor-pointer hover:opacity-90"
          style="background-color: var(--bg-card); color: var(--text-primary);"
        >
          <span class="flex items-center gap-2">
            <span>🎵</span>
            <span>{{ t.panelAudio }} (6)</span>
          </span>
          <span class="text-xs" style="color: var(--accent-brass);">{{ openPanels.audio ? '▲' : '▼' }}</span>
        </button>

        <div v-show="openPanels.audio" class="p-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          <button
            v-for="op in audioOps"
            :key="op.id"
            @click="runHelper('audio', op.id, op.name)"
            :disabled="!inputPath || runningOp === op.id"
            class="p-3.5 rounded-xl border text-center text-xs font-semibold flex flex-col items-center justify-center gap-2 transition hover:opacity-90 disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <span class="text-xl">{{ op.icon }}</span>
            <span class="truncate w-full">{{ op.name }}</span>
          </button>
        </div>
      </div>

      <!-- 3. Video Utilities (8 buttons) -->
      <div
        class="rounded-2xl border overflow-hidden shadow-sm transition"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <button
          @click="openPanels.video = !openPanels.video"
          class="w-full flex items-center justify-between p-4 text-xs font-bold transition text-left cursor-pointer hover:opacity-90"
          style="background-color: var(--bg-card); color: var(--text-primary);"
        >
          <span class="flex items-center gap-2">
            <span>🎬</span>
            <span>{{ t.panelVideo }} (8)</span>
          </span>
          <span class="text-xs" style="color: var(--accent-brass);">{{ openPanels.video ? '▲' : '▼' }}</span>
        </button>

        <div v-show="openPanels.video" class="p-6 grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-3">
          <button
            v-for="op in videoOps"
            :key="op.id"
            @click="runHelper('video', op.id, op.name)"
            :disabled="!inputPath || runningOp === op.id"
            class="p-3 rounded-xl border text-center text-xs font-semibold flex flex-col items-center justify-center gap-2 transition hover:opacity-90 disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <span class="text-lg">{{ op.icon }}</span>
            <span class="truncate w-full">{{ op.name }}</span>
          </button>
        </div>
      </div>

      <!-- 4. Smart Helpers (3 buttons) -->
      <div
        class="rounded-2xl border overflow-hidden shadow-sm transition"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <button
          @click="openPanels.smart = !openPanels.smart"
          class="w-full flex items-center justify-between p-4 text-xs font-bold transition text-left cursor-pointer hover:opacity-90"
          style="background-color: var(--bg-card); color: var(--text-primary);"
        >
          <span class="flex items-center gap-2">
            <span>🧠</span>
            <span>{{ t.panelSmart }} (3)</span>
          </span>
          <span class="text-xs" style="color: var(--accent-brass);">{{ openPanels.smart ? '▲' : '▼' }}</span>
        </button>

        <div v-show="openPanels.smart" class="p-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            v-for="op in smartOps"
            :key="op.id"
            @click="runHelper('smart', op.id, op.name)"
            :disabled="!inputPath || runningOp === op.id"
            class="p-4 rounded-xl border text-center text-xs font-semibold flex flex-col items-center justify-center gap-2 transition hover:opacity-90 disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <span class="text-2xl">{{ op.icon }}</span>
            <span class="font-bold">{{ op.name }}</span>
            <span class="text-[11px]" style="color: var(--text-muted);">{{ op.desc }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Execution Log Box -->
    <div v-if="logLines.length > 0" class="p-5 rounded-2xl border space-y-2 shadow-sm" style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
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

    <!-- Error Panel Integration -->
    <ErrorPanel
      v-if="errorInfo"
      :title="errorInfo.title"
      :message="errorInfo.message"
      :traceback="errorInfo.traceback"
      @retry="retryLastOp"
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
  inputLabel: 'Source Media File',
  inputPlaceholder: 'Select or drop video/audio file...',
  outputLabel: 'Target Output Destination',
  outputPlaceholder: 'Auto-generated or custom output path',
  panelQuick: 'Quick Helpers',
  panelAudio: 'Audio Utilities',
  panelVideo: 'Video Utilities',
  panelSmart: 'Smart AI & Inspection Helpers',
  processLog: 'Utility Operation Log'
}

const inputPath = ref('')
const outputPath = ref('')
const runningOp = ref<string | null>(null)
const logLines = ref<string[]>([])
const errorInfo = ref<{ title: string; message: string; traceback?: string } | null>(null)
let lastOpArgs: { category: string; opId: string; name: string } | null = null

const openPanels = ref({
  quick: true,
  audio: true,
  video: true,
  smart: true
})

const quickOps = [
  { id: 'remux', name: 'Remux Stream', icon: '⇄' },
  { id: 'extract-audio', name: 'Strip Audio (MP3)', icon: '🎵' },
  { id: 'mute', name: 'Mute Audio', icon: '🔇' },
  { id: 'trim-30s', name: 'Trim 30s', icon: '✂' },
  { id: 'preview-clip', name: 'Preview Clip (10s)', icon: '🎞' },
  { id: 'thumbnail', name: 'Thumbnail (640px)', icon: '🖼' }
]

const audioOps = [
  { id: 'volume-boost', name: 'Volume +3dB', icon: '🔊' },
  { id: 'fade', name: 'Fade In/Out', icon: '∿' },
  { id: 'convert-bitrate', name: '192k 44.1kHz', icon: '⚡' },
  { id: 'to-stereo', name: 'Stereo / Mono (2ch)', icon: '🎧' },
  { id: 'silence-detect', name: 'Silence Detection (-50dB)', icon: '🔍' },
  { id: 'loudness-norm', name: 'EBU R128 Norm', icon: '📊' }
]

const videoOps = [
  { id: 'scale-720p', name: 'Scale 720p', icon: '📐' },
  { id: 'crop-90', name: 'Crop 90%', icon: '✂' },
  { id: 'pad', name: 'Pad Frames', icon: '◻' },
  { id: 'rotate-90', name: 'Rotate 90°', icon: '↻' },
  { id: 'fps-30', name: 'Change 30 FPS', icon: '⏱' },
  { id: 'color-adjust', name: 'Color Adjust', icon: '🎨' },
  { id: 'blur-sharpen', name: 'Blur / Sharpen', icon: '✦' },
  { id: 'deinterlace', name: 'Deinterlace', icon: '▤' }
]

const smartOps = [
  { id: 'blackframe-detect', name: 'Black Frame Detector', desc: 'Scan for black cut frames', icon: '⬛' },
  { id: 'scene-preview', name: 'Scene Preview (10 scenes)', desc: 'Generate multi-scene grid preview', icon: '🎬' },
  { id: 'scene-thumbnails', name: 'Scene Thumbnails (640px)', desc: 'Extract keyframe thumbnails', icon: '🖼' }
]

async function browseInput() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Media Files', extensions: ['mp4', 'mkv', 'avi', 'mov', 'webm', 'mp3', 'wav', 'flac', 'm4a', 'opus'] }]
    })
    if (selected && typeof selected === 'string') {
      inputPath.value = selected
      toastStore.success(`Selected media: ${selected}`)
    }
  } catch {
    toastStore.info('Enter media path directly.')
  }
}

async function browseOutput() {
  try {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const selected = await save({
      filters: [{ name: 'Media Output', extensions: ['mp4', 'mkv', 'webm', 'mp3', 'jpg', 'png'] }]
    })
    if (selected && typeof selected === 'string') {
      outputPath.value = selected
    }
  } catch {
    toastStore.info('Enter destination path directly.')
  }
}

async function runHelper(category: string, opId: string, name: string) {
  if (!inputPath.value.trim()) return
  runningOp.value = opId
  errorInfo.value = null
  lastOpArgs = { category, opId, name }
  logLines.value.push(`[${new Date().toLocaleTimeString()}] Executing ${name} (${opId}) on ${inputPath.value}`)

  try {
    const res = await apiClient.runUtility({
      category,
      operation: opId,
      input_file: inputPath.value.trim(),
      output_file: outputPath.value.trim() || undefined
    })

    logLines.value.push(`[${new Date().toLocaleTimeString()}] Task queued: ID ${res.task_id}`)
    logLines.value.push(`[${new Date().toLocaleTimeString()}] Output target: ${res.output_file}`)
    toastStore.success(`Utility task queued: ${name}`)
  } catch (e: any) {
    errorInfo.value = {
      title: `Utility Operation '${name}' Failed`,
      message: e.message || 'Could not execute FFmpeg media helper.',
      traceback: String(e)
    }
    toastStore.error(`Operation failed: ${name}`)
  } finally {
    runningOp.value = null
  }
}

function retryLastOp() {
  if (lastOpArgs) {
    runHelper(lastOpArgs.category, lastOpArgs.opId, lastOpArgs.name)
  }
}
</script>
