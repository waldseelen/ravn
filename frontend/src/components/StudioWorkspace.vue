<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Studio Header & Sub-Tab Bar -->
    <div
      class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl border shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 rounded-xl border flex items-center justify-center text-xl font-bold"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
        >
          <span>❖</span>
        </div>
        <div>
          <h1 class="text-base font-bold" style="color: var(--text-primary);">
            {{ t.title }}
          </h1>
          <p class="text-xs" style="color: var(--text-muted);">
            {{ t.subtitle }}
          </p>
        </div>
      </div>

      <!-- Studio Navigation Bar & Launcher Toggle -->
      <div class="flex items-center gap-2">
        <button
          v-if="activeStudioTab !== 'launcher'"
          @click="activeStudioTab = 'launcher'"
          class="px-3 py-2 text-xs font-semibold rounded-xl border transition flex items-center gap-1.5 cursor-pointer hover:opacity-90"
          style="background-color: var(--bg-card); color: var(--text-secondary); border-color: var(--border-subtle);"
        >
          <span>‹</span>
          <span>{{ t.backToLauncher }}</span>
        </button>

        <div
          class="flex p-1 rounded-xl border shrink-0"
          style="background-color: var(--bg-input); border-color: var(--border-subtle);"
        >
          <button
            v-for="tab in studioTabs"
            :key="tab.id"
            @click="activeStudioTab = tab.id"
            class="px-3.5 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer"
            :style="activeStudioTab === tab.id ? 'background-color: var(--accent-brass); color: var(--bg-primary); font-weight: bold;' : 'color: var(--text-secondary);'"
          >
            <span>{{ tab.icon }}</span>
            <span class="ml-1.5">{{ tab.label }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- VIEW 1: STUDIO LAUNCHER GRID (P4-T1) -->
    <div v-if="activeStudioTab === 'launcher'" class="space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <div
          v-for="card in launcherCards"
          :key="card.id"
          @click="activeStudioTab = card.id"
          class="p-6 rounded-2xl border transition-all duration-200 cursor-pointer flex flex-col justify-between hover:scale-[1.01] shadow-sm hover:shadow-md"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div
                class="w-12 h-12 rounded-xl border flex items-center justify-center text-2xl"
                style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
              >
                <span>{{ card.icon }}</span>
              </div>
              <span
                class="text-[10px] uppercase font-mono px-2 py-0.5 rounded border font-bold"
                style="background-color: var(--bg-card); border-color: var(--border-subtle); color: var(--text-muted);"
              >
                {{ card.badge }}
              </span>
            </div>

            <div>
              <h3 class="text-sm font-bold" style="color: var(--text-primary);">
                {{ card.title }}
              </h3>
              <p class="text-xs mt-1 line-clamp-2" style="color: var(--text-secondary);">
                {{ card.desc }}
              </p>
            </div>
          </div>

          <div class="pt-4 mt-4 border-t flex items-center justify-between text-xs font-semibold" style="border-color: var(--border-subtle); color: var(--accent-brass);">
            <span>{{ t.openTool }}</span>
            <span>→</span>
          </div>
        </div>
      </div>
    </div>

    <!-- VIEW 2: FOCUSED STUDIO WORKSPACES -->
    <div v-else>
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

const t = {
  title: 'Studio Media Suite',
  subtitle: 'FFmpeg Transcoding, Subtitles, Filters, Multi-track Mixing & Smart Helpers',
  backToLauncher: 'Launcher Grid',
  openTool: 'Launch Tool'
}

const studioTabs = [
  { id: 'converter', label: 'Converter', icon: '⇄' },
  { id: 'subtitles', label: 'Subtitles', icon: '≡' },
  { id: 'filters', label: 'Filters & EQ', icon: '◫' },
  { id: 'mixer', label: 'Mixer', icon: '∿' },
  { id: 'utilities', label: 'Utilities', icon: '✂' }
]

const launcherCards = [
  {
    id: 'converter',
    icon: '⇄',
    badge: 'Transcode',
    title: 'Format Converter',
    desc: 'Transcode video/audio containers, switch codecs (H.264, HEVC, VP9, AV1, Opus), adjust CRF and hardware acceleration.'
  },
  {
    id: 'subtitles',
    icon: '≡',
    badge: 'Captions',
    title: 'Subtitle Manager',
    desc: 'Extract online subtitles (TR/EN/DE/FR/ES), convert formats (SRT/VTT/ASS), shift timing, and embed soft/hard subs.'
  },
  {
    id: 'filters',
    icon: '◫',
    badge: 'Grade & FX',
    title: 'Video Filters & FX',
    desc: 'Tune brightness, contrast, saturation, blur, sharpen, rotation, denoise, 3D LUTs, and color grading filters.'
  },
  {
    id: 'mixer',
    icon: '∿',
    badge: 'Composition',
    title: 'Audio & Video Mixer',
    desc: 'Multi-track concatenation, crossfade transitions, audio normalization, picture-in-picture (PIP), watermark, and overlay.'
  },
  {
    id: 'utilities',
    icon: '✂',
    badge: 'Quick Tools',
    title: 'Media Utilities & Trim',
    desc: 'Fast remuxing, audio stripping, silence detection, 30s trimming, thumbnail generation, loudness (EBU R128), and black frame scanning.'
  }
]

const activeStudioTab = ref('converter')
</script>

