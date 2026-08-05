<template>
  <div class="p-6 max-w-7xl mx-auto space-y-6">
    <div class="flex items-center justify-between bg-slate-900/80 backdrop-blur p-4 rounded-2xl border border-slate-800 shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-amber-600/20 text-amber-400 rounded-xl border border-amber-500/30">
          <span class="text-2xl">📝</span>
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-100">Subtitle Studio</h1>
          <p class="text-xs text-slate-400">Extract, burn-in (hardsub), embed (softsub), and download subtitle files</p>
        </div>
      </div>
    </div>

    <div class="bg-slate-900/60 backdrop-blur p-6 rounded-2xl border border-slate-800 space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-2">
          <label class="block text-xs font-semibold text-slate-300">Video File</label>
          <input v-model="videoPath" type="text" placeholder="Select video file..." class="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100" />
        </div>
        <div class="space-y-2">
          <label class="block text-xs font-semibold text-slate-300">Subtitle File (.srt / .ass / .vtt)</label>
          <input v-model="subPath" type="text" placeholder="Select subtitle file..." class="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100" />
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Embedding Mode</label>
          <select v-model="embedMode" class="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200">
            <option value="soft">SoftSub (Mux track into container)</option>
            <option value="hard">HardSub (Burn text directly into video stream)</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Target Language</label>
          <select v-model="targetLang" class="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200">
            <option value="tr">Turkish (tr)</option>
            <option value="en">English (en)</option>
            <option value="es">Spanish (es)</option>
            <option value="de">German (de)</option>
          </select>
        </div>
        <div class="flex items-end">
          <button @click="processSubtitles" class="w-full py-3 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-xl shadow-lg shadow-amber-600/30 transition">
            Process Subtitles
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const videoPath = ref('')
const subPath = ref('')
const embedMode = ref('soft')
const targetLang = ref('tr')

function processSubtitles() {
  alert(`Processing subtitles with ${embedMode.value} mode...`)
}
</script>
