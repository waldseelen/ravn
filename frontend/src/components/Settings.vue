<template>
  <div class="p-6 max-w-4xl mx-auto space-y-6">
    <div class="border-b border-slate-700 pb-4">
      <h1 class="text-2xl font-bold text-slate-100">Application Settings</h1>
      <p class="text-sm text-slate-400">Configure global defaults, paths, and download automation options.</p>
    </div>

    <div v-if="loading" class="text-slate-400 py-8 text-center">Loading settings...</div>

    <div v-else class="space-y-6">
      <div class="bg-slate-800/60 p-6 rounded-xl border border-slate-700 space-y-4">
        <h2 class="text-lg font-semibold text-slate-200 border-b border-slate-700 pb-2">General & Storage</h2>
        <div class="grid grid-cols-1 gap-4">
          <label class="block space-y-1">
            <span class="text-sm font-medium text-slate-300">Default Output Directory</span>
            <input
              v-model="settings.download_dir"
              type="text"
              class="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </label>
        </div>
      </div>

      <div class="bg-slate-800/60 p-6 rounded-xl border border-slate-700 space-y-4">
        <h2 class="text-lg font-semibold text-slate-200 border-b border-slate-700 pb-2">Preferences</h2>
        <div class="space-y-3">
          <label class="flex items-center gap-3">
            <input v-model="settings.embed_metadata" type="checkbox" class="w-4 h-4 rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0" />
            <span class="text-sm text-slate-200">Automatically embed metadata & cover art</span>
          </label>
          <label class="flex items-center gap-3">
            <input v-model="settings.auto_subtitle" type="checkbox" class="w-4 h-4 rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0" />
            <span class="text-sm text-slate-200">Download subtitles automatically when available</span>
          </label>
        </div>
      </div>

      <div class="flex justify-end gap-3 pt-4">
        <button
          @click="saveSettings"
          :disabled="saving"
          class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 font-medium text-white rounded-lg transition"
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
