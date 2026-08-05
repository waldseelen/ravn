<template>
  <div class="max-w-6xl mx-auto space-y-8">
    <!-- Hero / Welcome Banner -->
    <div class="relative overflow-hidden p-8 rounded-2xl bg-gradient-to-r from-[#1E1E1E] to-[#252525] border border-[#3A3330] shadow-xl">
      <div class="relative z-10 space-y-3 max-w-2xl">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#C99A5B]/10 border border-[#C99A5B]/20 text-[#C99A5B] text-xs font-semibold">
          <span>❖</span>
          <span>RAVN Media Pipeline v2.0</span>
        </div>
        <h1 class="text-3xl font-extrabold text-[#E8E0D8] tracking-tight">Welcome to RAVN</h1>
        <p class="text-sm text-[#B8A99A] leading-relaxed">
          High-performance media acquisition, studio transcoding, subtitle burn-in, and local media library management powered by yt-dlp & FFmpeg.
        </p>
        <div class="pt-2 flex gap-4">
          <RouterLink
            to="/download"
            class="px-6 py-2.5 bg-[#C99A5B] hover:bg-[#A87C42] text-[#141414] font-bold text-xs rounded-xl shadow-lg shadow-[#C99A5B]/20 transition flex items-center gap-2"
          >
            <span>↓</span>
            <span>New Download</span>
          </RouterLink>
          <RouterLink
            to="/studio"
            class="px-6 py-2.5 bg-[#252525] hover:bg-[#2A2A2A] text-[#E8E0D8] font-semibold text-xs rounded-xl border border-[#3A3330] transition flex items-center gap-2"
          >
            <span>❖</span>
            <span>Open Studio</span>
          </RouterLink>
        </div>
      </div>
    </div>

    <!-- System Stats Cards Grid (Orijinal Home Workspace) -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="p-6 bg-[#1E1E1E] border border-[#3A3330] rounded-2xl space-y-2">
        <div class="flex items-center justify-between text-[#A09080] text-xs font-semibold">
          <span>Active Downloads</span>
          <span class="text-[#C99A5B]">↓</span>
        </div>
        <div class="text-3xl font-black text-[#E8E0D8]">{{ downloadStore.tasks.length }}</div>
        <div class="text-[11px] text-[#B8A99A]">Real-time task queue</div>
      </div>

      <div class="p-6 bg-[#1E1E1E] border border-[#3A3330] rounded-2xl space-y-2">
        <div class="flex items-center justify-between text-[#A09080] text-xs font-semibold">
          <span>Media Library</span>
          <span class="text-[#C99A5B]">▦</span>
        </div>
        <div class="text-3xl font-black text-[#E8E0D8]">{{ libraryCount }}</div>
        <div class="text-[11px] text-[#B8A99A]">Organized media items</div>
      </div>

      <div class="p-6 bg-[#1E1E1E] border border-[#3A3330] rounded-2xl space-y-2">
        <div class="flex items-center justify-between text-[#A09080] text-xs font-semibold">
          <span>FFmpeg Engine</span>
          <span class="text-[#22c55e]">✓</span>
        </div>
        <div class="text-3xl font-black text-[#22c55e]">Active</div>
        <div class="text-[11px] text-[#B8A99A]">Bundled binaries ready</div>
      </div>
    </div>

    <!-- Quick Workspaces Showcase -->
    <div class="space-y-4">
      <h2 class="text-base font-bold text-[#E8E0D8] flex items-center gap-2">
        <span class="text-[#C99A5B]">❖</span>
        <span>Studio Workspaces</span>
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <RouterLink
          to="/download"
          class="p-6 bg-[#1E1E1E] hover:bg-[#252525] border border-[#3A3330] hover:border-[#C99A5B]/50 rounded-2xl transition group space-y-3"
        >
          <div class="flex items-center gap-3">
            <div class="p-3 bg-[#C99A5B]/10 text-[#C99A5B] rounded-xl border border-[#C99A5B]/20 text-lg">
              ↓
            </div>
            <div>
              <h3 class="text-sm font-bold text-[#E8E0D8] group-hover:text-[#C99A5B] transition">Media Acquisition & Torrent</h3>
              <p class="text-xs text-[#A09080]">Single URLs, Playlists, Batch & Torrent/Magnet flows</p>
            </div>
          </div>
        </RouterLink>

        <RouterLink
          to="/studio"
          class="p-6 bg-[#1E1E1E] hover:bg-[#252525] border border-[#3A3330] hover:border-[#C99A5B]/50 rounded-2xl transition group space-y-3"
        >
          <div class="flex items-center gap-3">
            <div class="p-3 bg-[#C99A5B]/10 text-[#C99A5B] rounded-xl border border-[#C99A5B]/20 text-lg">
              ⇄
            </div>
            <div>
              <h3 class="text-sm font-bold text-[#E8E0D8] group-hover:text-[#C99A5B] transition">Processing & Studio Tools</h3>
              <p class="text-xs text-[#A09080]">Transcode, Subtitles, Video Filters, EQ & Audio Mixer</p>
            </div>
          </div>
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useDownloadStore } from '../stores/downloadStore'
import { apiClient } from '../services/apiClient'

const downloadStore = useDownloadStore()
const libraryCount = ref(0)

onMounted(async () => {
  try {
    const history = await apiClient.getHistory()
    libraryCount.value = history.length
  } catch (e) {
    console.error(e)
  }
})
</script>
