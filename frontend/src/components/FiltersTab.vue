<template>
  <div class="p-6 max-w-7xl mx-auto space-y-6">
    <div class="flex items-center justify-between bg-slate-900/80 backdrop-blur p-4 rounded-2xl border border-slate-800 shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-rose-600/20 text-rose-400 rounded-xl border border-rose-500/30">
          <span class="text-2xl">🎨</span>
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-100">Video Filters & Audio Equalizer</h1>
          <p class="text-xs text-slate-400">Color correction, FPS conversion, audio gain & multi-band EQ</p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Video Filters -->
      <div class="bg-slate-900/60 backdrop-blur p-6 rounded-2xl border border-slate-800 space-y-4">
        <h3 class="text-sm font-semibold text-slate-200 border-b border-slate-800 pb-2">Video Adjustments</h3>
        <div class="space-y-3 text-xs">
          <label class="block space-y-1">
            <span class="text-slate-400">Brightness ({{ brightness }})</span>
            <input v-model="brightness" type="range" min="-1" max="1" step="0.1" class="w-full accent-rose-500" />
          </label>
          <label class="block space-y-1">
            <span class="text-slate-400">Contrast ({{ contrast }})</span>
            <input v-model="contrast" type="range" min="0" max="2" step="0.1" class="w-full accent-rose-500" />
          </label>
          <label class="block space-y-1">
            <span class="text-slate-400">Saturation ({{ saturation }})</span>
            <input v-model="saturation" type="range" min="0" max="3" step="0.1" class="w-full accent-rose-500" />
          </label>
        </div>
      </div>

      <!-- Audio Equalizer -->
      <div class="bg-slate-900/60 backdrop-blur p-6 rounded-2xl border border-slate-800 space-y-4">
        <h3 class="text-sm font-semibold text-slate-200 border-b border-slate-800 pb-2">Audio Equalizer & Gain</h3>
        <div class="space-y-3 text-xs">
          <label class="block space-y-1">
            <span class="text-slate-400">Bass Boost (+{{ bass }} dB)</span>
            <input v-model="bass" type="range" min="0" max="14" step="1" class="w-full accent-rose-500" />
          </label>
          <label class="block space-y-1">
            <span class="text-slate-400">Treble (+{{ treble }} dB)</span>
            <input v-model="treble" type="range" min="0" max="14" step="1" class="w-full accent-rose-500" />
          </label>
          <label class="block space-y-1">
            <span class="text-slate-400">Master Gain ({{ gain }}x)</span>
            <input v-model="gain" type="range" min="0.5" max="3" step="0.1" class="w-full accent-rose-500" />
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const brightness = ref(0)
const contrast = ref(1)
const saturation = ref(1)
const bass = ref(0)
const treble = ref(0)
const gain = ref(1)
</script>
