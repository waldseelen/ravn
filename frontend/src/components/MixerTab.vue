<template>
  <div class="p-6 max-w-7xl mx-auto space-y-6">
    <div class="flex items-center justify-between bg-slate-900/80 backdrop-blur p-4 rounded-2xl border border-slate-800 shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-cyan-600/20 text-cyan-400 rounded-xl border border-cyan-500/30">
          <span class="text-2xl">🎛️</span>
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-100">Audio Track Mixer</h1>
          <p class="text-xs text-slate-400">Combine background music, voiceover tracks, or swap audio streams</p>
        </div>
      </div>
    </div>

    <div class="bg-slate-900/60 backdrop-blur p-6 rounded-2xl border border-slate-800 space-y-4">
      <div class="space-y-3">
        <label class="block text-xs font-semibold text-slate-300">Video File (Primary Visual Track)</label>
        <input v-model="videoFile" type="text" placeholder="Select video file..." class="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100" />
      </div>
      <div class="space-y-3">
        <label class="block text-xs font-semibold text-slate-300">Secondary Audio Stream File</label>
        <input v-model="audioFile" type="text" placeholder="Select background music or voiceover file..." class="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100" />
      </div>
      <div class="flex justify-end pt-2">
        <button @click="mixTracks" class="px-8 py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded-xl shadow-lg shadow-cyan-600/30">
          Mix & Render Stream
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const videoFile = ref('')
const audioFile = ref('')

function mixTracks() {
  alert('Mixing audio streams...')
}
</script>
