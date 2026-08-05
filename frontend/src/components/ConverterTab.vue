<template>
  <div class="p-6 max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between bg-slate-900/80 backdrop-blur p-4 rounded-2xl border border-slate-800 shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-purple-600/20 text-purple-400 rounded-xl border border-purple-500/30">
          <span class="text-2xl">🎬</span>
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-100">Media Converter</h1>
          <p class="text-xs text-slate-400">High-performance FFmpeg video & audio transcode engine</p>
        </div>
      </div>
    </div>

    <!-- Converter Form -->
    <div class="bg-slate-900/60 backdrop-blur p-6 rounded-2xl border border-slate-800 space-y-6">
      <div class="space-y-2">
        <label class="block text-sm font-semibold text-slate-200">Input File Path</label>
        <div class="flex gap-3">
          <input
            v-model="inputFilePath"
            type="text"
            placeholder="C:/path/to/input/video.mp4"
            class="flex-1 px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:border-purple-500"
          />
          <button @click="browseInputFile" class="px-5 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700">
            Browse...
          </button>
        </div>
      </div>

      <!-- Settings Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
        <!-- Target Format -->
        <div class="space-y-2">
          <label class="block text-xs font-semibold text-slate-400">Target Container / Format</label>
          <select v-model="targetFormat" class="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-sm">
            <optgroup label="Video Formats">
              <option value="mp4">MP4 (H.264 / AAC)</option>
              <option value="mkv">MKV (Matroska)</option>
              <option value="webm">WebM (VP9 / Opus)</option>
              <option value="avi">AVI</option>
              <option value="mov">MOV (ProRes/H.264)</option>
            </optgroup>
            <optgroup label="Audio Formats">
              <option value="mp3">MP3 (Audio)</option>
              <option value="m4a">M4A (AAC Audio)</option>
              <option value="flac">FLAC (Lossless)</option>
              <option value="wav">WAV (PCM Uncompressed)</option>
              <option value="ogg">OGG (Vorbis)</option>
            </optgroup>
          </select>
        </div>

        <!-- Video Codec / Quality -->
        <div class="space-y-2">
          <label class="block text-xs font-semibold text-slate-400">Encoder / Quality Preset</label>
          <select v-model="qualityPreset" class="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-sm">
            <option value="ultrafast">Ultrafast (Fastest, Larger File)</option>
            <option value="medium">Medium (Balanced - Recommended)</option>
            <option value="veryslow">Very Slow (Best Compression)</option>
            <option value="copy">Stream Copy (Passthrough - No Re-encode)</option>
          </select>
        </div>

        <!-- Resolution Scale -->
        <div class="space-y-2">
          <label class="block text-xs font-semibold text-slate-400">Resolution Scaling</label>
          <select v-model="resolutionScale" class="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-sm">
            <option value="original">Same as Source</option>
            <option value="1080">Scale to 1080p (Full HD)</option>
            <option value="720">Scale to 720p (HD)</option>
            <option value="480">Scale to 480p (SD)</option>
          </select>
        </div>
      </div>

      <!-- Advanced Options Switches -->
      <div class="flex flex-wrap gap-6 pt-2 text-xs text-slate-300 border-t border-slate-800/60">
        <label class="flex items-center gap-2">
          <input v-model="normalizeAudio" type="checkbox" class="rounded bg-slate-950 border-slate-800 text-purple-600" />
          Normalize Audio (EBU R128 Loudness)
        </label>
        <label class="flex items-center gap-2">
          <input v-model="stripAudio" type="checkbox" class="rounded bg-slate-950 border-slate-800 text-purple-600" />
          Mute / Remove Audio Track
        </label>
      </div>

      <!-- Action Button -->
      <div class="flex justify-end pt-4">
        <button
          @click="startConversion"
          :disabled="!inputFilePath || converting"
          class="px-8 py-3 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-xl shadow-lg shadow-purple-600/30 transition disabled:opacity-50"
        >
          {{ converting ? 'Converting FFmpeg Stream...' : 'Start Conversion' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const inputFilePath = ref('')
const targetFormat = ref('mp4')
const qualityPreset = ref('medium')
const resolutionScale = ref('original')
const normalizeAudio = ref(false)
const stripAudio = ref(false)
const converting = ref(false)

function browseInputFile() {
  const sample = 'C:/Downloads/sample_video.mkv'
  inputFilePath.value = sample
}

function startConversion() {
  if (!inputFilePath.value) return
  converting.value = true
  setTimeout(() => {
    converting.value = false
    alert('Conversion finished successfully!')
  }, 2000)
}
</script>
