<template>
  <div class="space-y-6">
    <div
      class="p-6 rounded-2xl border space-y-6 shadow-sm"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <!-- Mode & Operation Selection -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Mode Switcher -->
        <div>
          <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
            🎧/🎬 {{ t.modeLabel }}
          </label>
          <div
            class="flex p-1 rounded-xl border"
            style="background-color: var(--bg-input); border-color: var(--border-subtle);"
          >
            <button
              @click="mode = 'audio'; operation = 'mix'"
              class="flex-1 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer"
              :style="mode === 'audio' ? 'background-color: var(--accent-brass); color: var(--bg-primary); font-weight: bold;' : 'color: var(--text-secondary);'"
            >
              🎵 {{ t.modeAudio }}
            </button>
            <button
              @click="mode = 'video'; operation = 'overlay'"
              class="flex-1 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer"
              :style="mode === 'video' ? 'background-color: var(--accent-brass); color: var(--bg-primary); font-weight: bold;' : 'color: var(--text-secondary);'"
            >
              🎬 {{ t.modeVideo }}
            </button>
          </div>
        </div>

        <!-- Operation Dropdown -->
        <div>
          <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
            ⚡ {{ t.operationLabel }}
          </label>
          <select
            v-model="operation"
            class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <template v-if="mode === 'audio'">
              <option value="mix">Mix Audio Tracks (Multichannel overlay)</option>
              <option value="concat">Concatenate / Join Files Sequentially</option>
              <option value="crossfade">Crossfade Transition Between Tracks</option>
              <option value="normalize">Normalize Loudness (EBU R128)</option>
              <option value="trim">Trim Audio Segment</option>
              <option value="fade">Apply Fade-in / Fade-out</option>
            </template>
            <template v-else>
              <option value="overlay">Overlay Video / Graphic Layer</option>
              <option value="concat">Concatenate Video Clips</option>
              <option value="pip">Picture in Picture (PiP)</option>
              <option value="side-by-side">Side-by-Side Split Screen</option>
              <option value="watermark">Apply Logo / Watermark Overlay</option>
              <option value="transition">Fade Transition Between Clips</option>
              <option value="replace-audio">Replace Audio Stream with New Track</option>
            </template>
          </select>
        </div>
      </div>

      <!-- Multi-File Input List with DND -->
      <div class="space-y-3 pt-2 border-t" style="border-color: var(--border-subtle);">
        <div class="flex items-center justify-between">
          <label class="text-xs font-bold uppercase tracking-wider flex items-center gap-2" style="color: var(--text-muted);">
            <span>📁 {{ t.inputFilesList }}</span>
            <span
              class="px-2 py-0.5 rounded text-[10px] font-mono font-bold border"
              style="background-color: var(--bg-card); border-color: var(--border-brass); color: var(--accent-brass);"
            >
              {{ inputFiles.length }} {{ t.filesCount }}
            </span>
          </label>

          <div class="flex items-center gap-2">
            <button
              @click="addInputFiles"
              class="px-3 py-1.5 text-xs font-bold rounded-lg border transition hover:opacity-90 cursor-pointer"
              style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
            >
              + {{ t.addFiles }}
            </button>
            <button
              @click="inputFiles = []"
              :disabled="inputFiles.length === 0"
              class="px-3 py-1.5 text-xs font-semibold rounded-lg border transition hover:opacity-90 cursor-pointer disabled:opacity-50"
              style="background-color: var(--bg-card); color: var(--text-muted); border-color: var(--border-subtle);"
            >
              {{ t.clearList }}
            </button>
          </div>
        </div>

        <!-- Dropzone area -->
        <div
          v-if="inputFiles.length === 0"
          class="p-8 rounded-2xl border-2 border-dashed text-center text-xs space-y-1 transition cursor-pointer"
          :class="{ 'ring-2': isDragging }"
          :style="{
            backgroundColor: 'var(--bg-input)',
            borderColor: isDragging ? 'var(--accent-brass)' : 'var(--border-subtle)',
            color: 'var(--text-muted)'
          }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
          @click="addInputFiles"
        >
          <span class="text-2xl block">📥</span>
          <p class="font-medium" style="color: var(--text-primary);">{{ t.dropFilesHere }}</p>
          <p class="text-[11px]">{{ t.dropFilesHint }}</p>
        </div>

        <!-- File rows list -->
        <div v-else class="space-y-2 max-h-48 overflow-y-auto">
          <div
            v-for="(f, idx) in inputFiles"
            :key="idx"
            class="flex items-center justify-between p-2.5 rounded-xl border text-xs font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle);"
          >
            <div class="flex items-center gap-2 truncate min-w-0 flex-1">
              <span class="font-bold opacity-60">#{{ idx + 1 }}</span>
              <span class="truncate" style="color: var(--text-primary);">{{ f }}</span>
            </div>
            <button
              @click="removeFile(idx)"
              class="text-xs px-2 py-0.5 rounded border hover:opacity-80 cursor-pointer shrink-0 ml-2"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--status-error);"
            >
              ✕
            </button>
          </div>
        </div>
      </div>

      <!-- Dynamic Parameters Panel -->
      <div class="p-4 rounded-xl border space-y-3" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
        <h3 class="text-xs font-bold uppercase tracking-wider" style="color: var(--text-primary);">
          ⚙️ {{ t.operationOptions }} ({{ operation }})
        </h3>

        <!-- Crossfade Options -->
        <div v-if="operation === 'crossfade'" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
              Duration (seconds)
            </label>
            <input
              v-model.number="crossfadeDuration"
              type="number"
              min="0.5"
              max="10.0"
              step="0.5"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
        </div>

        <!-- Trim Options -->
        <div v-if="operation === 'trim'" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">Start Time (s)</label>
            <input
              v-model.number="trimStart"
              type="number"
              min="0"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">Duration (s)</label>
            <input
              v-model.number="trimDuration"
              type="number"
              min="1"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
        </div>

        <!-- Fade Options -->
        <div v-if="operation === 'fade'" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">Fade In Duration (s)</label>
            <input
              v-model.number="fadeIn"
              type="number"
              min="0"
              step="0.5"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">Fade Out Duration (s)</label>
            <input
              v-model.number="fadeOut"
              type="number"
              min="0"
              step="0.5"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
        </div>

        <!-- Overlay / PiP / Watermark Options -->
        <div v-if="['overlay', 'pip', 'watermark'].includes(operation)" class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">Position</label>
            <select
              v-model="overlayPosition"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option value="top_left">Top Left</option>
              <option value="top_right">Top Right</option>
              <option value="bottom_left">Bottom Left</option>
              <option value="bottom_right">Bottom Right (Default)</option>
              <option value="center">Center</option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">Scale Multiplier</label>
            <input
              v-model.number="overlayScale"
              type="number"
              min="0.1"
              max="1.0"
              step="0.05"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">Opacity (0.0 - 1.0)</label>
            <input
              v-model.number="overlayOpacity"
              type="number"
              min="0.1"
              max="1.0"
              step="0.05"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
        </div>

        <!-- Side-by-Side Options -->
        <div v-if="operation === 'side-by-side'" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">Split Orientation</label>
            <select
              v-model="splitOrientation"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option value="horizontal">Horizontal (Left / Right)</option>
              <option value="vertical">Vertical (Top / Bottom)</option>
            </select>
          </div>
        </div>

        <!-- Transition Duration -->
        <div v-if="operation === 'transition'" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">Transition Duration (s)</label>
            <input
              v-model.number="transitionDuration"
              type="number"
              min="0.5"
              max="5.0"
              step="0.5"
              class="w-full rounded-lg px-3 py-1.5 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
        </div>
      </div>

      <!-- Output Destination -->
      <div class="space-y-2 pt-2 border-t" style="border-color: var(--border-subtle);">
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

      <!-- Action Button -->
      <div class="flex items-center justify-between gap-3 pt-2 border-t" style="border-color: var(--border-subtle);">
        <button
          @click="resetForm"
          class="px-4 py-2.5 rounded-xl border text-xs font-semibold transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-secondary); border-color: var(--border-subtle);"
        >
          {{ t.reset }}
        </button>

        <button
          @click="runMixer"
          :disabled="inputFiles.length === 0 || isProcessing"
          class="px-8 py-2.5 text-xs font-bold rounded-xl shadow-lg transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
          style="background-color: var(--accent-brass); color: var(--bg-primary);"
        >
          <span>∿</span>
          <span>{{ isProcessing ? t.processing : t.runOperation }}</span>
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
      @retry="runMixer"
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
  modeLabel: 'Workspace Media Mode',
  modeAudio: 'Audio Composition',
  modeVideo: 'Video Composition',
  operationLabel: 'Mixer Operation',
  inputFilesList: 'Input Track List',
  filesCount: 'files',
  addFiles: 'Add Media Files',
  clearList: 'Clear All',
  dropFilesHere: 'Drop Audio or Video Files Here',
  dropFilesHint: 'or click Add Media Files button above',
  operationOptions: 'Parameters for',
  outputLabel: 'Output Destination File',
  outputPlaceholder: 'Auto-generated or custom output path',
  reset: 'Reset Form',
  runOperation: 'Execute Composition',
  processing: 'Processing Composition...',
  processLog: 'Composition Log'
}

const mode = ref<'audio' | 'video'>('audio')
const operation = ref('mix')
const inputFiles = ref<string[]>([])
const outputPath = ref('')

const crossfadeDuration = ref(2.0)
const trimStart = ref(0.0)
const trimDuration = ref(30.0)
const fadeIn = ref(1.0)
const fadeOut = ref(1.0)
const overlayPosition = ref('bottom_right')
const overlayScale = ref(0.25)
const overlayOpacity = ref(1.0)
const splitOrientation = ref('horizontal')
const transitionDuration = ref(1.0)

const isDragging = ref(false)
const isProcessing = ref(false)
const logLines = ref<string[]>([])
const errorInfo = ref<{ title: string; message: string; traceback?: string } | null>(null)

function handleDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    for (let i = 0; i < e.dataTransfer.files.length; i++) {
      const f = e.dataTransfer.files[i]
      const path = (f as any).path || f.name
      if (!inputFiles.value.includes(path)) {
        inputFiles.value.push(path)
      }
    }
    toastStore.info(`Added ${e.dataTransfer.files.length} files`)
  }
}

async function addInputFiles() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: true,
      filters: [{ name: 'Media Files', extensions: ['mp4', 'mkv', 'webm', 'mov', 'avi', 'mp3', 'wav', 'flac', 'm4a', 'opus'] }]
    })
    if (selected && Array.isArray(selected)) {
      for (const p of selected) {
        if (!inputFiles.value.includes(p)) {
          inputFiles.value.push(p)
        }
      }
      toastStore.success(`Added ${selected.length} files`)
    } else if (selected && typeof selected === 'string') {
      if (!inputFiles.value.includes(selected)) {
        inputFiles.value.push(selected)
      }
    }
  } catch {
    toastStore.info('Enter local paths or drop files.')
  }
}

function removeFile(index: number) {
  inputFiles.value.splice(index, 1)
}

async function browseOutput() {
  try {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const ext = mode.value === 'audio' ? 'mp3' : 'mp4'
    const selected = await save({
      filters: [{ name: 'Output File', extensions: [ext, 'mkv', 'wav'] }]
    })
    if (selected && typeof selected === 'string') {
      outputPath.value = selected
    }
  } catch {
    toastStore.info('Enter destination path directly.')
  }
}

function resetForm() {
  inputFiles.value = []
  outputPath.value = ''
  logLines.value = []
  errorInfo.value = null
}

async function runMixer() {
  if (inputFiles.value.length === 0) return
  isProcessing.value = true
  errorInfo.value = null
  logLines.value.push(`[${new Date().toLocaleTimeString()}] Starting ${mode.value} mixer operation: ${operation.value} on ${inputFiles.value.length} files`)

  const options: Record<string, any> = {}
  if (operation.value === 'crossfade') options.duration = crossfadeDuration.value
  if (operation.value === 'trim') {
    options.start = trimStart.value
    options.duration = trimDuration.value
  }
  if (operation.value === 'fade') {
    options.fade_in = fadeIn.value
    options.fade_out = fadeOut.value
  }
  if (['overlay', 'pip', 'watermark'].includes(operation.value)) {
    options.position = overlayPosition.value
    options.scale = overlayScale.value
    options.opacity = overlayOpacity.value
  }
  if (operation.value === 'side-by-side') options.orientation = splitOrientation.value
  if (operation.value === 'transition') options.duration = transitionDuration.value

  try {
    const res = await apiClient.runMixer({
      mode: mode.value,
      operation: operation.value,
      input_files: inputFiles.value,
      output_file: outputPath.value.trim() || undefined,
      options
    })

    logLines.value.push(`[${new Date().toLocaleTimeString()}] Task queued: ID ${res.task_id}`)
    logLines.value.push(`[${new Date().toLocaleTimeString()}] Output target: ${res.output_file}`)
    toastStore.success(`Mixer task queued (ID: ${res.task_id.substring(0, 8)})`)
  } catch (e: any) {
    errorInfo.value = {
      title: 'Mixer Operation Failed',
      message: e.message || 'Could not queue media composition operation.',
      traceback: String(e)
    }
    toastStore.error('Mixer operation failed')
  } finally {
    isProcessing.value = false
  }
}
</script>
