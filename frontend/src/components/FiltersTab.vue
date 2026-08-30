<template>
  <div class="space-y-6">
    <div
      class="p-6 rounded-2xl border space-y-6 shadow-sm"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <!-- Source & Output Paths with DND -->
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

      <!-- Numeric Sliders & Controls -->
      <div class="space-y-3 pt-2 border-t" style="border-color: var(--border-subtle);">
        <h3 class="text-xs font-bold uppercase tracking-wider flex items-center gap-2" style="color: var(--text-primary);">
          <span>◫</span>
          <span>{{ t.numericAdjustments }}</span>
        </h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
          <!-- Brightness -->
          <div class="p-3 rounded-xl border space-y-1.5" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
            <div class="flex items-center justify-between text-[11px]">
              <span style="color: var(--text-secondary);">{{ t.brightness }}</span>
              <span class="font-mono font-bold" style="color: var(--accent-brass);">{{ brightness >= 0 ? `+${brightness.toFixed(2)}` : brightness.toFixed(2) }}</span>
            </div>
            <input v-model.number="brightness" type="range" min="-1" max="1" step="0.05" class="w-full cursor-pointer" />
          </div>

          <!-- Contrast -->
          <div class="p-3 rounded-xl border space-y-1.5" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
            <div class="flex items-center justify-between text-[11px]">
              <span style="color: var(--text-secondary);">{{ t.contrast }}</span>
              <span class="font-mono font-bold" style="color: var(--accent-brass);">{{ contrast.toFixed(1) }}x</span>
            </div>
            <input v-model.number="contrast" type="range" min="0" max="3" step="0.1" class="w-full cursor-pointer" />
          </div>

          <!-- Saturation -->
          <div class="p-3 rounded-xl border space-y-1.5" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
            <div class="flex items-center justify-between text-[11px]">
              <span style="color: var(--text-secondary);">{{ t.saturation }}</span>
              <span class="font-mono font-bold" style="color: var(--accent-brass);">{{ saturation.toFixed(1) }}x</span>
            </div>
            <input v-model.number="saturation" type="range" min="0" max="3" step="0.1" class="w-full cursor-pointer" />
          </div>

          <!-- Blur -->
          <div class="p-3 rounded-xl border space-y-1.5" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
            <div class="flex items-center justify-between text-[11px]">
              <span style="color: var(--text-secondary);">{{ t.blur }}</span>
              <span class="font-mono font-bold" style="color: var(--accent-brass);">{{ blur.toFixed(1) }}</span>
            </div>
            <input v-model.number="blur" type="range" min="0" max="10" step="0.5" class="w-full cursor-pointer" />
          </div>

          <!-- Sharpen -->
          <div class="p-3 rounded-xl border space-y-1.5" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
            <div class="flex items-center justify-between text-[11px]">
              <span style="color: var(--text-secondary);">{{ t.sharpen }}</span>
              <span class="font-mono font-bold" style="color: var(--accent-brass);">{{ sharpen.toFixed(1) }}</span>
            </div>
            <input v-model.number="sharpen" type="range" min="0" max="5" step="0.5" class="w-full cursor-pointer" />
          </div>

          <!-- Rotate -->
          <div class="p-3 rounded-xl border space-y-1.5" style="background-color: var(--bg-input); border-color: var(--border-subtle);">
            <label class="block text-[11px] font-semibold" style="color: var(--text-secondary);">
              {{ t.rotate }}
            </label>
            <select
              v-model.number="rotate"
              class="w-full rounded-lg px-2 py-1 text-xs border outline-none font-mono"
              style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option :value="0">0° (Normal)</option>
              <option :value="90">90° CW</option>
              <option :value="180">180° Flip</option>
              <option :value="270">270° CCW</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Effects & Grading Checkboxes -->
      <div class="space-y-3 pt-2 border-t" style="border-color: var(--border-subtle);">
        <h3 class="text-xs font-bold uppercase tracking-wider" style="color: var(--text-primary);">
          {{ t.effectCheckboxes }}
        </h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-xs">
          <label class="flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer transition" :style="{ backgroundColor: flipH ? 'var(--bg-card)' : 'transparent', borderColor: flipH ? 'var(--border-brass)' : 'var(--border-subtle)', color: flipH ? 'var(--accent-brass)' : 'var(--text-secondary)' }">
            <input type="checkbox" v-model="flipH" class="rounded cursor-pointer" />
            <span>{{ t.flipH }}</span>
          </label>

          <label class="flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer transition" :style="{ backgroundColor: flipV ? 'var(--bg-card)' : 'transparent', borderColor: flipV ? 'var(--border-brass)' : 'var(--border-subtle)', color: flipV ? 'var(--accent-brass)' : 'var(--text-secondary)' }">
            <input type="checkbox" v-model="flipV" class="rounded cursor-pointer" />
            <span>{{ t.flipV }}</span>
          </label>

          <label class="flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer transition" :style="{ backgroundColor: grayscale ? 'var(--bg-card)' : 'transparent', borderColor: grayscale ? 'var(--border-brass)' : 'var(--border-subtle)', color: grayscale ? 'var(--accent-brass)' : 'var(--text-secondary)' }">
            <input type="checkbox" v-model="grayscale" class="rounded cursor-pointer" />
            <span>{{ t.grayscale }}</span>
          </label>

          <label class="flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer transition" :style="{ backgroundColor: sepia ? 'var(--bg-card)' : 'transparent', borderColor: sepia ? 'var(--border-brass)' : 'var(--border-subtle)', color: sepia ? 'var(--accent-brass)' : 'var(--text-secondary)' }">
            <input type="checkbox" v-model="sepia" class="rounded cursor-pointer" />
            <span>{{ t.sepia }}</span>
          </label>

          <label class="flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer transition" :style="{ backgroundColor: invert ? 'var(--bg-card)' : 'transparent', borderColor: invert ? 'var(--border-brass)' : 'var(--border-subtle)', color: invert ? 'var(--accent-brass)' : 'var(--text-secondary)' }">
            <input type="checkbox" v-model="invert" class="rounded cursor-pointer" />
            <span>{{ t.invert }}</span>
          </label>

          <label class="flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer transition" :style="{ backgroundColor: deinterlace ? 'var(--bg-card)' : 'transparent', borderColor: deinterlace ? 'var(--border-brass)' : 'var(--border-subtle)', color: deinterlace ? 'var(--accent-brass)' : 'var(--text-secondary)' }">
            <input type="checkbox" v-model="deinterlace" class="rounded cursor-pointer" />
            <span>{{ t.deinterlace }}</span>
          </label>
        </div>
      </div>

      <!-- Denoise & 3D LUT Controls -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t" style="border-color: var(--border-subtle);">
        <!-- Denoise -->
        <div class="space-y-1.5">
          <label class="block text-[11px] font-semibold" style="color: var(--text-secondary);">
            🧹 {{ t.denoiseLabel }}
          </label>
          <select
            v-model="denoise"
            class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="off">Off (No Denoise Filter)</option>
            <option value="light">Light (Fast 3D Denoise)</option>
            <option value="moderate">Moderate (HQDN3D Balanced)</option>
            <option value="strong">Strong (Heavy grain removal)</option>
            <option value="ultra">Ultra (Maximum smoothing)</option>
          </select>
        </div>

        <!-- 3D LUT File -->
        <div class="space-y-1.5">
          <label class="block text-[11px] font-semibold" style="color: var(--text-secondary);">
            🎨 {{ t.lutLabel }}
          </label>
          <div class="flex gap-2">
            <input
              v-model="lutFile"
              type="text"
              :placeholder="t.lutPlaceholder"
              class="flex-1 px-4 py-2 rounded-xl text-xs border outline-none font-mono"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
            <button
              @click="browseLutFile"
              class="px-3.5 py-2 rounded-xl border text-xs font-semibold hover:opacity-90 cursor-pointer"
              style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
            >
              📁
            </button>
          </div>
        </div>
      </div>

      <!-- Active Filters Summary Banner -->
      <div
        class="p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
        style="background-color: var(--bg-input); border-color: var(--border-subtle);"
      >
        <div class="flex items-center gap-2">
          <span class="font-bold" style="color: var(--text-muted);">{{ t.activeFilterSummary }}:</span>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="(filt, idx) in activeFiltersSummary"
              :key="idx"
              class="px-2 py-0.5 rounded text-[11px] font-mono border font-semibold"
              style="background-color: var(--bg-card); border-color: var(--border-brass); color: var(--accent-brass);"
            >
              {{ filt }}
            </span>
            <span v-if="activeFiltersSummary.length === 0" style="color: var(--text-muted);">
              {{ t.noneActive }}
            </span>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="resetFilters"
            class="px-4 py-2 rounded-xl border text-xs font-semibold transition hover:opacity-90 cursor-pointer"
            style="background-color: var(--bg-card); color: var(--text-secondary); border-color: var(--border-subtle);"
          >
            {{ t.reset }}
          </button>
          <button
            @click="applyFilters"
            :disabled="!inputPath || isProcessing"
            class="px-8 py-2 text-xs font-bold rounded-xl shadow-lg transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
            style="background-color: var(--accent-brass); color: var(--bg-primary);"
          >
            <span>◫</span>
            <span>{{ isProcessing ? t.applying : t.applyFilters }}</span>
          </button>
        </div>
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
      @retry="applyFilters"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToastStore } from '../stores/toastStore'
import { apiClient } from '../services/apiClient'
import ErrorPanel from './ErrorPanel.vue'

const toastStore = useToastStore()

const t = {
  inputLabel: 'Source Video Path',
  inputPlaceholder: 'Select or drop video file...',
  outputLabel: 'Target Filtered Video Destination',
  outputPlaceholder: 'Auto-generated or custom output path',
  numericAdjustments: 'Color, Sharpness & Geometry Adjustments',
  brightness: 'Brightness',
  contrast: 'Contrast',
  saturation: 'Saturation',
  blur: 'Gaussian Blur',
  sharpen: 'Unsharp Mask',
  rotate: 'Rotation',
  effectCheckboxes: 'Visual Effects & Color Grading Filters',
  flipH: 'Flip Horizontal',
  flipV: 'Flip Vertical',
  grayscale: 'Grayscale (B&W)',
  sepia: 'Sepia Vintage',
  invert: 'Invert Colors',
  deinterlace: 'YADIF Deinterlace',
  advancedDenoiseLut: 'Denoise & 3D LUT Grading',
  denoiseLabel: 'Temporal/Spatial Denoise Filter',
  denoiseOff: 'Off',
  denoiseLight: 'Light',
  denoiseModerate: 'Moderate',
  denoiseStrong: 'Strong',
  denoiseUltra: 'Ultra',
  lutLabel: '3D Color Grading LUT (.cube / .3dl)',
  lutPlaceholder: 'Select 3D LUT file...',
  activeFilterSummary: 'Active Filter Stack',
  noneActive: 'No active filters (Passthrough)',
  reset: 'Reset All',
  applyFilters: 'Apply Video Filters',
  applying: 'Rendering Filters...',
  processLog: 'Filter Rendering Log'
}

const inputPath = ref('')
const outputPath = ref('')

const brightness = ref(0.0)
const contrast = ref(1.0)
const saturation = ref(1.0)
const blur = ref(0.0)
const sharpen = ref(0.0)
const rotate = ref(0)

const flipH = ref(false)
const flipV = ref(false)
const grayscale = ref(false)
const sepia = ref(false)
const invert = ref(false)
const deinterlace = ref(false)

const denoise = ref('off')
const lutFile = ref('')

const isProcessing = ref(false)
const logLines = ref<string[]>([])
const errorInfo = ref<{ title: string; message: string; traceback?: string } | null>(null)

const activeFiltersSummary = computed(() => {
  const list: string[] = []
  if (brightness.value !== 0.0) list.push(`Brightness: ${brightness.value >= 0 ? '+' : ''}${brightness.value.toFixed(2)}`)
  if (contrast.value !== 1.0) list.push(`Contrast: ${contrast.value.toFixed(1)}x`)
  if (saturation.value !== 1.0) list.push(`Saturation: ${saturation.value.toFixed(1)}x`)
  if (blur.value > 0) list.push(`Blur: ${blur.value}`)
  if (sharpen.value > 0) list.push(`Sharpen: ${sharpen.value}`)
  if (rotate.value !== 0) list.push(`Rotate: ${rotate.value}°`)
  if (flipH.value) list.push('Flip-H')
  if (flipV.value) list.push('Flip-V')
  if (grayscale.value) list.push('Grayscale')
  if (sepia.value) list.push('Sepia')
  if (invert.value) list.push('Invert')
  if (deinterlace.value) list.push('Deinterlace')
  if (denoise.value !== 'off') list.push(`Denoise: ${denoise.value}`)
  if (lutFile.value) list.push('3D-LUT')
  return list
})

async function browseInput() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Video Files', extensions: ['mp4', 'mkv', 'avi', 'mov', 'webm'] }]
    })
    if (selected && typeof selected === 'string') {
      inputPath.value = selected
      toastStore.success(`Selected video: ${selected}`)
    }
  } catch {
    toastStore.info('Enter local video path directly.')
  }
}

async function browseOutput() {
  try {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const selected = await save({
      filters: [{ name: 'Video Output', extensions: ['mp4', 'mkv', 'webm'] }]
    })
    if (selected && typeof selected === 'string') {
      outputPath.value = selected
    }
  } catch {
    toastStore.info('Enter destination path directly.')
  }
}

async function browseLutFile() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'LUT Files', extensions: ['cube', '3dl', 'dat'] }]
    })
    if (selected && typeof selected === 'string') {
      lutFile.value = selected
      toastStore.success(`Selected LUT: ${selected}`)
    }
  } catch {
    toastStore.info('Enter LUT path directly.')
  }
}

function resetFilters() {
  brightness.value = 0.0
  contrast.value = 1.0
  saturation.value = 1.0
  blur.value = 0.0
  sharpen.value = 0.0
  rotate.value = 0
  flipH.value = false
  flipV.value = false
  grayscale.value = false
  sepia.value = false
  invert.value = false
  deinterlace.value = false
  denoise.value = 'off'
  lutFile.value = ''
  errorInfo.value = null
}

async function applyFilters() {
  if (!inputPath.value.trim()) return
  isProcessing.value = true
  errorInfo.value = null
  logLines.value.push(`[${new Date().toLocaleTimeString()}] Applying filter stack (${activeFiltersSummary.value.length} active) to ${inputPath.value}`)

  try {
    const res = await apiClient.applyFilters({
      input_file: inputPath.value.trim(),
      output_file: outputPath.value.trim() || undefined,
      brightness: brightness.value,
      contrast: contrast.value,
      saturation: saturation.value,
      blur: blur.value,
      sharpen: sharpen.value,
      rotate: rotate.value,
      flip_h: flipH.value,
      flip_v: flipV.value,
      grayscale: grayscale.value,
      sepia: sepia.value,
      invert: invert.value,
      deinterlace: deinterlace.value,
      denoise: denoise.value,
      lut_file: lutFile.value.trim() || undefined
    })

    logLines.value.push(`[${new Date().toLocaleTimeString()}] Filter task enqueued: ID ${res.task_id}`)
    logLines.value.push(`[${new Date().toLocaleTimeString()}] Target Output: ${res.output_file}`)
    toastStore.success(`Filter rendering queued (ID: ${res.task_id.substring(0, 8)})`)
  } catch (e: any) {
    errorInfo.value = {
      title: 'Filter Rendering Failed',
      message: e.message || 'Could not execute FFmpeg video filter chain.',
      traceback: String(e)
    }
    toastStore.error('Filter processing failed')
  } finally {
    isProcessing.value = false
  }
}
</script>
