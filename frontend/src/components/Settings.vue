<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div
      class="flex items-center justify-between p-4 rounded-2xl border shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex items-center gap-3">
        <div
          class="p-3 rounded-xl border text-xl"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
        >
          <span>⚙</span>
        </div>
        <div>
          <h1 class="text-lg font-bold" style="color: var(--text-primary);">{{ t.title }}</h1>
          <p class="text-xs" style="color: var(--text-muted);">{{ t.subtitle }}</p>
        </div>
      </div>
    </div>

    <!-- Status feedback -->
    <div
      v-if="saveSuccess"
      class="p-4 rounded-xl border text-xs font-semibold"
      style="background-color: var(--success-bg); border-color: var(--status-success); color: var(--status-success);"
    >
      ✓ {{ t.saveSuccess }}
    </div>

    <div
      v-if="errorMessage"
      class="p-4 rounded-xl border text-xs font-semibold"
      style="background-color: var(--error-bg); border-color: var(--status-error); color: var(--status-error);"
    >
      ✕ {{ errorMessage }}
    </div>

    <div v-if="loading" class="py-8 text-center text-xs" style="color: var(--text-muted);">
      {{ t.loading }}
    </div>

    <div v-else class="space-y-6">
      <!-- Tool Health Diagnostics Box -->
      <div
        class="p-6 rounded-2xl border space-y-4 shadow-sm"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <h2
          class="text-xs font-bold uppercase tracking-wider border-b pb-2"
          style="color: var(--text-primary); border-color: var(--border-subtle);"
        >
          {{ t.toolHealthTitle }}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            class="p-4 border rounded-xl flex items-center justify-between"
            style="background-color: var(--bg-card); border-color: var(--border-subtle);"
          >
            <div>
              <div class="text-xs font-bold" style="color: var(--text-primary);">FFmpeg / FFprobe</div>
              <div class="text-[10px]" style="color: var(--text-muted);">Transcode Engine</div>
            </div>
            <span
              class="text-xs font-bold px-2 py-0.5 rounded border"
              style="background-color: var(--success-bg); color: var(--status-success); border-color: var(--status-success);"
            >
              Available
            </span>
          </div>

          <div
            class="p-4 border rounded-xl flex items-center justify-between"
            style="background-color: var(--bg-card); border-color: var(--border-subtle);"
          >
            <div>
              <div class="text-xs font-bold" style="color: var(--text-primary);">yt-dlp Engine</div>
              <div class="text-[10px]" style="color: var(--text-muted);">Extractor Engine</div>
            </div>
            <span
              class="text-xs font-bold px-2 py-0.5 rounded border"
              style="background-color: var(--success-bg); color: var(--status-success); border-color: var(--status-success);"
            >
              Available
            </span>
          </div>

          <div
            class="p-4 border rounded-xl flex items-center justify-between"
            style="background-color: var(--bg-card); border-color: var(--border-subtle);"
          >
            <div>
              <div class="text-xs font-bold" style="color: var(--text-primary);">aria2c Client</div>
              <div class="text-[10px]" style="color: var(--text-muted);">Torrent & Magnet</div>
            </div>
            <span
              class="text-xs font-bold px-2 py-0.5 rounded border"
              style="background-color: var(--warning-bg); color: var(--status-warning); border-color: var(--status-warning);"
            >
              Optional
            </span>
          </div>
        </div>
      </div>

      <!-- Storage & General Settings -->
      <div
        class="p-6 rounded-2xl border space-y-4 shadow-sm"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <h2
          class="text-xs font-bold uppercase tracking-wider border-b pb-2"
          style="color: var(--text-primary); border-color: var(--border-subtle);"
        >
          {{ t.storageTitle }}
        </h2>
        <div class="space-y-4">
          <label class="block space-y-1">
            <span class="text-xs font-semibold" style="color: var(--text-secondary);">{{ t.outputDirLabel }}</span>
            <input
              v-model="settings.download_dir"
              type="text"
              class="w-full px-4 py-3 rounded-xl text-xs border focus:outline-none"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </label>

          <div class="space-y-3 pt-2">
            <label class="flex items-center gap-3 cursor-pointer">
              <input v-model="settings.embed_metadata" type="checkbox" class="w-4 h-4 rounded accent-amber-600" />
              <span class="text-xs" style="color: var(--text-primary);">{{ t.embedMetadata }}</span>
            </label>
            <label class="flex items-center gap-3 cursor-pointer">
              <input v-model="settings.auto_subtitle" type="checkbox" class="w-4 h-4 rounded accent-amber-600" />
              <span class="text-xs" style="color: var(--text-primary);">{{ t.autoSubtitle }}</span>
            </label>
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-3 pt-2">
        <button
          @click="saveSettings"
          :disabled="saving"
          class="px-8 py-3 font-bold text-xs rounded-xl shadow-lg transition cursor-pointer disabled:opacity-50"
          style="background-color: var(--accent-brass); color: var(--bg-primary);"
        >
          {{ saving ? t.saving : t.save }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiClient } from '../services/apiClient'

const t = {
  title: 'Application Settings & Tool Health',
  subtitle: 'Configure global paths, tool dependencies, and default preferences',
  saveSuccess: 'Settings saved successfully',
  loading: 'Loading settings...',
  toolHealthTitle: 'Bundled Tool Health Status',
  storageTitle: 'Storage & Automation',
  outputDirLabel: 'Default Output Directory',
  embedMetadata: 'Automatically embed metadata & cover art',
  autoSubtitle: 'Download subtitles automatically when available',
  save: 'Save Settings',
  saving: 'Saving...'
}

const settings = ref<Record<string, any>>({})
const loading = ref(true)
const saving = ref(false)
const saveSuccess = ref(false)
const errorMessage = ref('')

async function loadSettings() {
  loading.value = true
  try {
    settings.value = await apiClient.getSettings()
  } catch (e: any) {
    errorMessage.value = e.message || 'Failed to load settings'
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveSuccess.value = false
  errorMessage.value = ''
  try {
    await apiClient.patchSettings(settings.value)
    saveSuccess.value = true
    setTimeout(() => { saveSuccess.value = false }, 3000)
  } catch (e: any) {
    errorMessage.value = e.message || 'Failed to save settings'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>
