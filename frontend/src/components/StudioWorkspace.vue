<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Studio Header & Sub-Tab Bar -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#1E1E1E] p-4 rounded-2xl border border-[#3A3330] shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-[#C99A5B]/10 text-[#C99A5B] rounded-xl border border-[#C99A5B]/20">
          <span class="text-xl">❖</span>
        </div>
        <div>
          <h1 class="text-lg font-bold text-[#E8E0D8]">Studio Processing Suite</h1>
          <p class="text-xs text-[#A09080]">Professional FFmpeg media processing pipeline</p>
        </div>
      </div>

      <!-- Studio Inner Navigation Bar (Orijinal CustomTkinter Studio Tabs) -->
      <div class="flex bg-[#141414] p-1 rounded-xl border border-[#3A3330]">
        <button
          v-for="tab in studioTabs"
          :key="tab.id"
          @click="activeStudioTab = tab.id"
          class="px-4 py-2 text-xs font-semibold rounded-lg transition-all"
          :class="activeStudioTab === tab.id ? 'bg-[#C99A5B] text-[#141414] shadow-md' : 'text-[#B8A99A] hover:text-[#E8E0D8]'"
        >
          <span>{{ tab.icon }}</span>
          <span class="ml-1.5">{{ tab.label }}</span>
        </button>
      </div>
    </div>

    <!-- Active Studio View -->
    <div>
      <ConverterTab v-if="activeStudioTab === 'converter'" />
      <SubtitleTab v-if="activeStudioTab === 'subtitles'" />
      <FiltersTab v-if="activeStudioTab === 'filters'" />
      <MixerTab v-if="activeStudioTab === 'mixer'" />
      <UtilitiesTab v-if="activeStudioTab === 'utilities'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ConverterTab from './ConverterTab.vue'
import SubtitleTab from './SubtitleTab.vue'
import FiltersTab from './FiltersTab.vue'
import MixerTab from './MixerTab.vue'
import UtilitiesTab from './UtilitiesTab.vue'

const studioTabs = [
  { id: 'converter', label: 'Converter', icon: '⇄' },
  { id: 'subtitles', label: 'Subtitles', icon: '≡' },
  { id: 'filters', label: 'Filters & EQ', icon: '◫' },
  { id: 'mixer', label: 'Audio Mixer', icon: '∿' },
  { id: 'utilities', label: 'Utilities & Trim', icon: '✂' }
]

const activeStudioTab = ref('converter')
</script>
