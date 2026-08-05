<template>
  <div class="p-6 max-w-7xl mx-auto space-y-6">
    <div class="flex items-center justify-between bg-slate-900/80 backdrop-blur p-4 rounded-2xl border border-slate-800 shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-teal-600/20 text-teal-400 rounded-xl border border-teal-500/30">
          <span class="text-2xl">✂️</span>
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-100">Media Utilities</h1>
          <p class="text-xs text-slate-400">Trim/Cut, GIF Maker, Audio Extractor & FFprobe Inspector</p>
        </div>
      </div>
    </div>

    <!-- Quick Utilities Cards Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-slate-900/60 backdrop-blur p-6 rounded-2xl border border-slate-800 space-y-3">
        <h3 class="text-sm font-semibold text-slate-200">Video Trimmer</h3>
        <p class="text-xs text-slate-400">Cut video between start & end timestamps without quality loss.</p>
        <div class="flex gap-2">
          <input v-model="startTime" type="text" placeholder="00:00:00" class="w-1/2 p-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 font-mono" />
          <input v-model="endTime" type="text" placeholder="00:01:30" class="w-1/2 p-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 font-mono" />
        </div>
        <button class="w-full py-2 bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold rounded-lg">Trim Segment</button>
      </div>

      <div class="bg-slate-900/60 backdrop-blur p-6 rounded-2xl border border-slate-800 space-y-3">
        <h3 class="text-sm font-semibold text-slate-200">Animated GIF Maker</h3>
        <p class="text-xs text-slate-400">Convert short video clips into high-quality animated GIFs.</p>
        <label class="block text-xs text-slate-400">
          FPS:
          <select v-model="gifFps" class="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200">
            <option value="15">15 FPS</option>
            <option value="24">24 FPS</option>
            <option value="30">30 FPS</option>
          </select>
        </label>
        <button class="w-full py-2 bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold rounded-lg">Generate GIF</button>
      </div>

      <div class="bg-slate-900/60 backdrop-blur p-6 rounded-2xl border border-slate-800 space-y-3">
        <h3 class="text-sm font-semibold text-slate-200">Fast Audio Extract</h3>
        <p class="text-xs text-slate-400">Extract pure audio stream into MP3/AAC instantly.</p>
        <button class="w-full py-2 bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold rounded-lg">Extract Audio Track</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const startTime = ref('00:00:00')
const endTime = ref('00:01:00')
const gifFps = ref('15')
</script>
