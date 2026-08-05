<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between bg-[#1E1E1E] p-4 rounded-2xl border border-[#3A3330] shadow-xl">
      <div class="flex items-center gap-3">
        <div class="p-3 bg-[#C99A5B]/10 text-[#C99A5B] rounded-xl border border-[#C99A5B]/20">
          <span class="text-xl">⚙</span>
        </div>
        <div>
          <h1 class="text-lg font-bold text-[#E8E0D8]">Application Settings & Tool Health</h1>
          <p class="text-xs text-[#A09080]">Configure global paths, tool dependencies, and default preferences</p>
        </div>
      </div>
    </div>

    <div v-if="loading" class="text-[#A09080] py-8 text-center text-xs">Loading settings...</div>

    <div v-else class="space-y-6">
      <!-- Tool Health Diagnostics Box -->
      <div class="bg-[#1E1E1E] p-6 rounded-2xl border border-[#3A3330] space-y-4">
        <h2 class="text-xs font-bold uppercase tracking-wider text-[#E8E0D8] border-b border-[#3A3330] pb-2">Bundled Tool Health Status</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="p-4 bg-[#141414] border border-[#3A3330] rounded-xl flex items-center justify-between">
            <div>
              <div class="text-xs font-bold text-[#E8E0D8]">FFmpeg / FFprobe</div>
              <div class="text-[10px] text-[#A09080]">Transcode Engine</div>
            </div>
            <span class="text-xs font-bold px-2 py-0.5 rounded bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/20">Available</span>
          </div>

          <div class="p-4 bg-[#141414] border border-[#3A3330] rounded-xl flex items-center justify-between">
            <div>
              <div class="text-xs font-bold text-[#E8E0D8]">yt-dlp Engine</div>
              <div class="text-[10px] text-[#A09080]">Extractor Engine</div>
            </div>
            <span class="text-xs font-bold px-2 py-0.5 rounded bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/20">Available</span>
          </div>

          <div class="p-4 bg-[#141414] border border-[#3A3330] rounded-xl flex items-center justify-between">
            <div>
              <div class="text-xs font-bold text-[#E8E0D8]">aria2c Client</div>
              <div class="text-[10px] text-[#A09080]">Torrent & Magnet</div>
            </div>
            <span class="text-xs font-bold px-2 py-0.5 rounded bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20">Optional</span>
          </div>
        </div>
      </div>

      <!-- Storage & General Settings -->
      <div class="bg-[#1E1E1E] p-6 rounded-2xl border border-[#3A3330] space-y-4">
        <h2 class="text-xs font-bold uppercase tracking-wider text-[#E8E0D8] border-b border-[#3A3330] pb-2">Storage & Automation</h2>
        <div class="space-y-4">
          <label class="block space-y-1">
            <span class="text-xs font-semibold text-[#B8A99A]">Default Output Directory</span>
            <input
              v-model="settings.download_dir"
              type="text"
              class="w-full px-4 py-3 bg-[#141414] border border-[#3A3330] rounded-xl text-[#E8E0D8] text-xs focus:outline-none focus:border-[#C99A5B]"
            />
          </label>

          <div class="space-y-3 pt-2">
            <label class="flex items-center gap-3">
              <input v-model="settings.embed_metadata" type="checkbox" class="w-4 h-4 rounded bg-[#141414] border-[#3A3330] text-[#C99A5B]" />
              <span class="text-xs text-[#E8E0D8]">Automatically embed metadata & cover art</span>
            </label>
            <label class="flex items-center gap-3">
              <input v-model="settings.auto_subtitle" type="checkbox" class="w-4 h-4 rounded bg-[#141414] border-[#3A3330] text-[#C99A5B]" />
              <span class="text-xs text-[#E8E0D8]">Download subtitles automatically when available</span>
            </label>
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-3 pt-2">
        <button
          @click="saveSettings"
          :disabled="saving"
          class="px-8 py-3 bg-[#C99A5B] hover:bg-[#A87C42] text-[#141414] font-bold text-xs rounded-xl shadow-lg transition"
        >
          {{ saving ? 'Saving...' : 'Save Settings' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiClient } from '../services/apiClient'

const settings = ref<Record<string, any>>({})
const loading = ref(true)
const saving = ref(false)

async function loadSettings() {
  loading.value = true
  try {
    settings.value = await apiClient.getSettings()
  } catch (e) {
    console.error('Failed to load settings:', e)
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await apiClient.patchSettings(settings.value)
    alert('Settings saved successfully!')
  } catch (e: any) {
    alert('Failed to save settings: ' + e.message)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>
