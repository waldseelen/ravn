<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div
      class="flex flex-col sm:flex-row sm:items-center justify-between p-5 rounded-2xl border shadow-xl gap-4"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex items-center gap-3">
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center text-2xl font-bold border"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
        >
          <span>⚙</span>
        </div>
        <div>
          <h1 class="text-base font-bold uppercase tracking-wider" style="color: var(--text-primary);">
            {{ t.title }}
          </h1>
          <p class="text-xs" style="color: var(--text-muted);">{{ t.subtitle }}</p>
        </div>
      </div>

      <!-- Quick Action Buttons -->
      <div class="flex items-center gap-2 flex-wrap">
        <button
          @click="saveSettings"
          :disabled="isSaving"
          class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          style="background-color: var(--accent-brass); color: var(--bg-primary);"
        >
          <span v-if="isSaving">⏳ {{ t.saving }}</span>
          <span v-else>💾 {{ t.saveSettings }}</span>
        </button>
        <button
          @click="showResetModal = true"
          class="px-3 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          ↺ {{ t.resetSettings }}
        </button>
        <button
          @click="exportSettings"
          class="px-3 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          📥 {{ t.exportJson }}
        </button>
        <button
          @click="importSettings"
          class="px-3 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          📤 {{ t.importJson }}
        </button>
      </div>
    </div>

    <!-- Error Panel -->
    <ErrorPanel
      :show="Boolean(errorMessage)"
      :message="errorMessage"
      @retry="loadAll"
    />

    <!-- Section 1: Tool Health (P6-T1) -->
    <div
      class="p-6 rounded-2xl border space-y-4 shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-3" style="border-color: var(--border-subtle);">
        <div>
          <h2 class="text-sm font-bold uppercase tracking-wider" style="color: var(--text-primary);">
            🩺 {{ t.toolHealthTitle }}
          </h2>
          <p class="text-xs" style="color: var(--text-muted);">{{ t.toolHealthSubtitle }}</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="hasMissingTools"
            @click="installMissingTools"
            :disabled="isInstallingTools"
            class="px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1 cursor-pointer disabled:opacity-50"
            style="background-color: var(--accent-brass); color: var(--bg-primary);"
          >
            <span v-if="isInstallingTools">⏳ {{ t.installing }}</span>
            <span v-else>➕ {{ t.installMissingTools }}</span>
          </button>
          <button
            @click="fetchHealth"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
            style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
          >
            ↻ {{ t.refresh }}
          </button>
        </div>
      </div>

      <!-- Tools Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          v-for="(info, toolName) in toolsSummary"
          :key="toolName"
          class="p-4 rounded-xl border space-y-2 transition flex flex-col justify-between"
          style="background-color: var(--bg-card); border-color: var(--border-subtle);"
        >
          <div>
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wide" style="color: var(--text-primary);">
                {{ toolName }}
              </span>
              <span
                class="text-[10px] font-bold font-mono px-2 py-0.5 rounded border"
                :style="{
                  backgroundColor: info.status === 'available' ? 'var(--success-bg)' : 'var(--error-bg)',
                  borderColor: info.status === 'available' ? 'var(--status-done)' : 'var(--status-error)',
                  color: info.status === 'available' ? 'var(--status-done)' : 'var(--status-error)'
                }"
              >
                {{ info.status === 'available' ? '✓ ' + t.available : '✕ ' + t.missing }}
              </span>
            </div>
            <div class="text-[11px] font-mono mt-1" style="color: var(--accent-brass);">
              {{ info.version ? 'v' + info.version : t.noVersion }}
            </div>
            <div class="text-[10px] font-mono truncate mt-0.5" style="color: var(--text-muted);" :title="info.path || ''">
              {{ info.path || t.noPathFound }}
            </div>
          </div>
          <div class="text-[10px] border-t pt-2 mt-2" style="border-color: var(--border-subtle); color: var(--text-secondary);">
            <span class="font-bold">{{ t.features }}:</span>
            {{ (info.affected_features && info.affected_features.length > 0) ? info.affected_features.join(', ') : t.allFeaturesOperational }}
          </div>
        </div>
      </div>
    </div>

    <!-- Section 2: General Settings (P6-T2) -->
    <div
      class="p-6 rounded-2xl border space-y-4 shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <h2 class="text-sm font-bold uppercase tracking-wider border-b pb-2" style="color: var(--text-primary); border-color: var(--border-subtle);">
        🌐 {{ t.generalSection }}
      </h2>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Theme Selector -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.themeLabel }}
          </label>
          <select
            v-model="formData.theme"
            @change="applyThemeLive"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="dark">Nordic Dark</option>
            <option value="light">Nordic Light</option>
          </select>
        </div>

        <!-- Language Selector -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.languageLabel }}
          </label>
          <select
            v-model="formData.language"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="tr">Türkçe (TR)</option>
            <option value="en">English (EN)</option>
          </select>
        </div>

        <!-- Close Behavior -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.closeBehaviorLabel }}
          </label>
          <select
            v-model="formData.close_to_tray"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option :value="true">{{ t.closeToTray }}</option>
            <option :value="false">{{ t.closeFully }}</option>
          </select>
        </div>
      </div>

      <!-- Toggles & Update Check Row -->
      <div class="pt-2 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <label class="flex items-center gap-2 cursor-pointer p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
          <input type="checkbox" v-model="formData.notifications_enabled" class="rounded accent-brass" />
          <span class="text-xs font-semibold" style="color: var(--text-primary);">{{ t.notificationsEnabled }}</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
          <input type="checkbox" v-model="formData.auto_update_check" class="rounded accent-brass" />
          <span class="text-xs font-semibold" style="color: var(--text-primary);">{{ t.autoCheckUpdates }}</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
          <input type="checkbox" v-model="formData.crash_reporting_enabled" class="rounded accent-brass" />
          <span class="text-xs font-semibold" style="color: var(--text-primary);">{{ t.crashReporting }}</span>
        </label>
      </div>

      <!-- Manual Update Check Box -->
      <div class="p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
        <div class="space-y-1">
          <div class="text-xs font-bold" style="color: var(--text-primary);">{{ t.updateCheckTitle }}</div>
          <div class="text-[11px]" style="color: var(--text-muted);">
            {{ updateStatusMessage || t.updateCheckPrompt }}
          </div>
        </div>
        <button
          @click="checkForUpdates"
          :disabled="isCheckingUpdates"
          class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition hover:opacity-90 cursor-pointer disabled:opacity-50"
          style="background-color: var(--bg-surface); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          <span v-if="isCheckingUpdates">⏳ {{ t.checking }}</span>
          <span v-else>🔍 {{ t.checkNow }}</span>
        </button>
      </div>
    </div>

    <!-- Section 3: Download Settings (P6-T3) -->
    <div
      class="p-6 rounded-2xl border space-y-4 shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <h2 class="text-sm font-bold uppercase tracking-wider border-b pb-2" style="color: var(--text-primary); border-color: var(--border-subtle);">
        📥 {{ t.downloadSection }}
      </h2>

      <!-- Download Directory -->
      <div class="space-y-1.5">
        <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
          {{ t.downloadDirLabel }}
        </label>
        <div class="flex gap-2">
          <input
            v-model="formData.default_download_path"
            type="text"
            class="flex-1 px-3 py-2 rounded-xl text-xs border focus:outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
          <button
            @click="browseDownloadDir"
            class="px-3 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
            style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
          >
            {{ t.browse }}
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Default Format -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.defaultFormatLabel }}
          </label>
          <select
            v-model="formData.default_format"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="MP4">MP4</option>
            <option value="MP3">MP3</option>
            <option value="MKV">MKV</option>
          </select>
        </div>

        <!-- Default Quality -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.defaultQualityLabel }}
          </label>
          <select
            v-model="formData.default_quality"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="best">{{ t.qualityBest }}</option>
            <option value="1080p">1080p</option>
            <option value="720p">720p</option>
            <option value="480p">480p</option>
          </select>
        </div>

        <!-- Concurrent Downloads Slider -->
        <div class="space-y-1.5">
          <div class="flex justify-between items-center text-xs font-semibold" style="color: var(--text-secondary);">
            <span>{{ t.concurrentDownloads }}</span>
            <span class="font-mono font-bold" style="color: var(--accent-brass);">{{ formData.concurrent_downloads }}</span>
          </div>
          <input
            type="range"
            min="1"
            max="5"
            step="1"
            v-model.number="formData.concurrent_downloads"
            class="w-full accent-brass cursor-pointer"
          />
        </div>

        <!-- History Limit -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.historyLimitLabel }}
          </label>
          <input
            v-model.number="formData.history_limit"
            type="number"
            min="10"
            max="10000"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
        </div>
      </div>
    </div>

    <!-- Section 4: Subtitle Settings (P6-T4) -->
    <div
      class="p-6 rounded-2xl border space-y-4 shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <h2 class="text-sm font-bold uppercase tracking-wider border-b pb-2" style="color: var(--text-primary); border-color: var(--border-subtle);">
        💬 {{ t.subtitleSection }}
      </h2>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Preferred Subtitle Language -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.preferredSubtitleLang }}
          </label>
          <select
            v-model="formData.preferred_subtitle_language"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="tr">tr (Türkçe)</option>
            <option value="en">en (English)</option>
            <option value="de">de (Deutsch)</option>
            <option value="fr">fr (Français)</option>
            <option value="es">es (Español)</option>
          </select>
        </div>

        <!-- Subtitle Fallback Language -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.fallbackSubtitleLang }}
          </label>
          <select
            v-model="formData.subtitle_fallback_language"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="none">{{ t.noFallback }}</option>
            <option value="en">en (English)</option>
            <option value="tr">tr (Türkçe)</option>
            <option value="de">de (Deutsch)</option>
            <option value="fr">fr (Français)</option>
            <option value="es">es (Español)</option>
          </select>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
        <label class="flex items-center gap-2 cursor-pointer p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
          <input type="checkbox" v-model="formData.auto_subtitle_download" class="rounded accent-brass" />
          <span class="text-xs font-semibold" style="color: var(--text-primary);">{{ t.autoSubtitles }}</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
          <input type="checkbox" v-model="formData.subtitle_include_auto_generated" class="rounded accent-brass" />
          <span class="text-xs font-semibold" style="color: var(--text-primary);">{{ t.includeAutoSubs }}</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
          <input type="checkbox" v-model="formData.auto_embed_subtitles" class="rounded accent-brass" />
          <span class="text-xs font-semibold" style="color: var(--text-primary);">{{ t.autoEmbedSubs }}</span>
        </label>
      </div>
    </div>

    <!-- Section 5: Metadata & Naming (P6-T5) -->
    <div
      class="p-6 rounded-2xl border space-y-4 shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <h2 class="text-sm font-bold uppercase tracking-wider border-b pb-2" style="color: var(--text-primary); border-color: var(--border-subtle);">
        🏷 {{ t.metadataSection }}
      </h2>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Naming Preset -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.namingPresetLabel }}
          </label>
          <select
            v-model="formData.download_naming_preset"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          >
            <option value="standard">{{ t.presetStandard }}</option>
            <option value="clean">{{ t.presetClean }}</option>
            <option value="playlist">{{ t.presetPlaylist }}</option>
          </select>
        </div>

        <!-- Custom Filename Template -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.filenameTemplateLabel }}
          </label>
          <input
            v-model="formData.download_filename_template"
            type="text"
            :placeholder="t.filenameTemplatePlaceholder"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
        <label class="flex items-center gap-2 cursor-pointer p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
          <input type="checkbox" v-model="formData.embed_metadata" class="rounded accent-brass" />
          <span class="text-xs font-semibold" style="color: var(--text-primary);">{{ t.embedMetadata }}</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
          <input type="checkbox" v-model="formData.auto_sort_downloads" class="rounded accent-brass" />
          <span class="text-xs font-semibold" style="color: var(--text-primary);">{{ t.autoSortDownloads }}</span>
        </label>
      </div>
    </div>

    <!-- Section 6: Post-Process & Reliability (P6-T6 & P6-T7) -->
    <div
      class="p-6 rounded-2xl border space-y-4 shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <h2 class="text-sm font-bold uppercase tracking-wider border-b pb-2" style="color: var(--text-primary); border-color: var(--border-subtle);">
        ⚙ {{ t.postProcessAndReliabilitySection }}
      </h2>

      <!-- Post-Process Options -->
      <div class="p-4 rounded-xl border space-y-3" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
        <div class="text-xs font-bold" style="color: var(--text-primary);">{{ t.postProcessSubTitle }}</div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="formData.download_postprocess.extract_audio" class="rounded accent-brass" />
            <span class="text-xs" style="color: var(--text-primary);">{{ t.extractAudio }}</span>
          </label>
          <div v-if="formData.download_postprocess.extract_audio" class="flex gap-2">
            <select
              v-model="formData.download_postprocess.audio_format"
              class="px-2 py-1 rounded text-xs border"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option value="mp3">MP3</option>
              <option value="m4a">M4A</option>
              <option value="aac">AAC</option>
              <option value="flac">FLAC</option>
              <option value="opus">OPUS</option>
              <option value="wav">WAV</option>
            </select>
            <select
              v-model="formData.download_postprocess.audio_bitrate"
              class="px-2 py-1 rounded text-xs border"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option value="128k">128k</option>
              <option value="192k">192k</option>
              <option value="320k">320k</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="formData.download_postprocess.convert_enabled" class="rounded accent-brass" />
            <span class="text-xs" style="color: var(--text-primary);">{{ t.convertVideo }}</span>
          </label>
          <div v-if="formData.download_postprocess.convert_enabled">
            <select
              v-model="formData.download_postprocess.convert_format"
              class="px-2 py-1 rounded text-xs border"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option value="mp4">MP4</option>
              <option value="mkv">MKV</option>
              <option value="webm">WebM</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Reliability Options -->
      <div class="p-4 rounded-xl border space-y-3" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
        <div class="text-xs font-bold" style="color: var(--text-primary);">{{ t.reliabilitySubTitle }}</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="formData.download_robustness.enable_archive" class="rounded accent-brass" />
            <span class="text-xs" style="color: var(--text-primary);">{{ t.enableArchive }}</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="formData.download_robustness.detect_duplicates" class="rounded accent-brass" />
            <span class="text-xs" style="color: var(--text-primary);">{{ t.detectDuplicates }}</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="formData.download_robustness.continue_partial" class="rounded accent-brass" />
            <span class="text-xs" style="color: var(--text-primary);">{{ t.continuePartial }}</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="formData.download_robustness.format_fallback" class="rounded accent-brass" />
            <span class="text-xs" style="color: var(--text-primary);">{{ t.formatFallback }}</span>
          </label>
        </div>

        <div class="pt-2 space-y-1">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.rateLimitLabel }} (KB/s - 0 = Limitsiz)
          </label>
          <input
            v-model.number="formData.download_robustness.rate_limit_kbps"
            type="number"
            min="0"
            class="w-full sm:w-64 px-3 py-1.5 rounded-xl text-xs border focus:outline-none"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
        </div>
      </div>
    </div>

    <!-- Section 7: Advanced Tuning & Cookies (Collapsible - P6-T8) -->
    <div
      class="rounded-2xl border overflow-hidden shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <button
        type="button"
        @click="advancedExpanded = !advancedExpanded"
        class="w-full p-5 flex items-center justify-between text-left transition hover:opacity-90 cursor-pointer"
        style="background-color: var(--bg-surface);"
      >
        <div class="flex items-center gap-2">
          <span class="text-sm font-bold" style="color: var(--accent-brass);">🔧</span>
          <span class="text-xs font-bold uppercase tracking-wider" style="color: var(--text-primary);">
            {{ t.advancedDownloadTitle }}
          </span>
          <span class="text-[11px] hidden sm:inline" style="color: var(--text-muted);">— {{ t.advancedSubtitle }}</span>
        </div>
        <span class="text-xs font-mono" style="color: var(--text-muted);">
          {{ advancedExpanded ? '▲' : '▼' }}
        </span>
      </button>

      <div v-show="advancedExpanded" class="p-6 space-y-4 border-t" style="border-color: var(--border-subtle);">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <!-- Cookies Mode -->
          <div class="space-y-1.5">
            <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
              {{ t.cookiesModeLabel }}
            </label>
            <select
              v-model="formData.download_advanced.cookies_mode"
              class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option value="none">{{ t.cookiesNone }}</option>
              <option value="browser">{{ t.cookiesBrowser }}</option>
              <option value="file">{{ t.cookiesFile }}</option>
            </select>
          </div>

          <!-- Cookies Browser -->
          <div v-if="formData.download_advanced.cookies_mode === 'browser'" class="space-y-1.5">
            <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
              {{ t.cookiesBrowserLabel }}
            </label>
            <select
              v-model="formData.download_advanced.cookies_browser"
              class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none cursor-pointer"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option value="chrome">Chrome</option>
              <option value="firefox">Firefox</option>
              <option value="edge">Edge</option>
              <option value="safari">Safari</option>
              <option value="brave">Brave</option>
              <option value="chromium">Chromium</option>
              <option value="opera">Opera</option>
            </select>
          </div>

          <!-- Cookies Profile -->
          <div v-if="formData.download_advanced.cookies_mode === 'browser'" class="space-y-1.5">
            <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
              {{ t.cookiesProfileLabel }}
            </label>
            <input
              v-model="formData.download_advanced.cookies_profile"
              type="text"
              placeholder="Default / Profile 1"
              class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>

          <!-- Cookies File -->
          <div v-if="formData.download_advanced.cookies_mode === 'file'" class="sm:col-span-2 space-y-1.5">
            <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
              {{ t.cookiesFileLabel }}
            </label>
            <div class="flex gap-2">
              <input
                v-model="formData.download_advanced.cookies_file"
                type="text"
                class="flex-1 px-3 py-2 rounded-xl text-xs border focus:outline-none font-mono"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              />
              <button
                @click="browseCookieFile"
                class="px-3 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
                style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
              >
                {{ t.browse }}
              </button>
            </div>
          </div>
        </div>

        <!-- Network Tuning Fields -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div class="space-y-1.5">
            <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
              {{ t.concurrentFragments }}
            </label>
            <input
              v-model.number="formData.download_advanced.concurrent_fragments"
              type="number"
              min="1"
              max="16"
              class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
          <div class="space-y-1.5">
            <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
              {{ t.fragmentRetries }}
            </label>
            <input
              v-model.number="formData.download_advanced.fragment_retries"
              type="number"
              min="0"
              max="50"
              class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
          <div class="space-y-1.5">
            <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
              {{ t.socketTimeout }} (sn)
            </label>
            <input
              v-model.number="formData.download_advanced.socket_timeout_seconds"
              type="number"
              min="5"
              max="300"
              class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Section 8: Engine & External Tools (P6-T9) -->
    <div
      class="p-6 rounded-2xl border space-y-4 shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <h2 class="text-sm font-bold uppercase tracking-wider border-b pb-2" style="color: var(--text-primary); border-color: var(--border-subtle);">
        ⚡ {{ t.engineSection }}
      </h2>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- FFmpeg Path -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.ffmpegPathLabel }}
          </label>
          <input
            v-model="formData.ffmpeg_path"
            type="text"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
        </div>

        <!-- aria2c Path -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.aria2PathLabel }}
          </label>
          <input
            v-model="formData.aria2c_path"
            type="text"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none font-mono"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
        </div>

        <!-- Torrent Seed Time -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.seedTimeLabel }} (dakika)
          </label>
          <input
            v-model.number="formData.torrent_seed_time"
            type="number"
            min="0"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
        </div>

        <!-- Torrent Max Connections -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold" style="color: var(--text-secondary);">
            {{ t.maxConnectionsLabel }}
          </label>
          <input
            v-model.number="formData.torrent_max_connections"
            type="number"
            min="1"
            max="128"
            class="w-full px-3 py-2 rounded-xl text-xs border focus:outline-none"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
        </div>
      </div>

      <div class="pt-2">
        <label class="flex items-center gap-2 cursor-pointer p-3 rounded-xl border" style="background-color: var(--bg-card); border-color: var(--border-subtle);">
          <input type="checkbox" v-model="formData.auto_cleanup" class="rounded accent-brass" />
          <span class="text-xs font-semibold" style="color: var(--text-primary);">{{ t.autoCleanup }}</span>
        </label>
      </div>
    </div>

    <!-- Reset Confirmation Modal -->
    <div
      v-if="showResetModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      style="background-color: rgba(0,0,0,0.6);"
      @click.self="showResetModal = false"
    >
      <div
        class="max-w-sm w-full p-6 rounded-2xl border shadow-2xl space-y-4 text-center"
        style="background-color: var(--bg-surface); border-color: var(--status-error);"
      >
        <div class="text-3xl">⚠️</div>
        <h3 class="text-sm font-bold" style="color: var(--text-primary);">
          {{ t.confirmResetTitle }}
        </h3>
        <p class="text-xs" style="color: var(--text-muted);">
          {{ t.confirmResetSubtitle }}
        </p>

        <div class="flex items-center justify-center gap-3 pt-2">
          <button
            @click="showResetModal = false"
            class="px-4 py-2 rounded-xl text-xs font-semibold border transition hover:opacity-90 cursor-pointer"
            style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
          >
            {{ t.cancel }}
          </button>
          <button
            @click="executeResetSettings"
            class="px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer"
            style="background-color: var(--error-bg); color: var(--status-error); border: 1px solid var(--status-error);"
          >
            {{ t.confirmResetBtn }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { apiClient } from '../services/apiClient'
import { useToastStore } from '../stores/toastStore'
import ErrorPanel from './ErrorPanel.vue'

const toast = useToastStore()

const t = {
  title: 'Ayarlar ve Tercihler',
  subtitle: 'İndirme motoru, dönüştürme, altyazı, bağımlılıklar ve sistem ayarları',
  saving: 'Kaydediliyor...',
  saveSettings: 'Ayarları Kaydet',
  resetSettings: 'Varsayılana Sıfırla',
  exportJson: 'JSON Dışa Aktar',
  importJson: 'JSON İçe Aktar',
  toolHealthTitle: 'Harici Araç Sağlık Durumu',
  toolHealthSubtitle: 'FFmpeg, yt-dlp, aria2c ve ffprobe çalışma ve sürüm raporu',
  refresh: 'Yenile',
  installMissingTools: 'Eksik Araçları Yükle',
  installing: 'Yükleniyor...',
  available: 'Hazır',
  missing: 'Eksik',
  noVersion: 'Sürüm Yok',
  noPathFound: 'Yol bulunamadı',
  features: 'Özellikler',
  allFeaturesOperational: 'Tüm özellikler aktif',
  generalSection: 'Genel Tercihler ve Tema',
  themeLabel: 'Görünüm Teması',
  languageLabel: 'Arayüz Dili',
  closeBehaviorLabel: 'Uygulama Kapatma Davranışı',
  closeToTray: 'Sistem Tepsisine Küçült',
  closeFully: 'Uygulamayı Tamamen Kapat',
  notificationsEnabled: 'Masaüstü Bildirimleri Aktif',
  autoCheckUpdates: 'Açılışta Güncellemeleri Otomatik Denetle',
  crashReporting: 'Anonim Hata Raporlama Aktif',
  updateCheckTitle: 'Sürüm ve Güncelleme Kontrolü',
  updateCheckPrompt: 'GitHub üzerindeki en son yayınlanan sürümü kontrol edin.',
  checking: 'Kontrol ediliyor...',
  checkNow: 'Şimdi Kontrol Et',
  downloadSection: 'İndirme ve Depolama Ayarları',
  downloadDirLabel: 'Varsayılan İndirme Klasörü',
  browse: 'Gözat',
  defaultFormatLabel: 'Varsayılan Medya Formatı',
  defaultQualityLabel: 'Varsayılan Video Kalitesi',
  qualityBest: 'En İyi (Best)',
  concurrentDownloads: 'Eşzamanlı İndirme Limiti',
  historyLimitLabel: 'Geçmiş Kayıt Tutma Limiti',
  subtitleSection: 'Altyazı Tercihleri',
  preferredSubtitleLang: 'Öncelikli Altyazı Dili',
  fallbackSubtitleLang: 'Yedek Altyazı Dili (Fallback)',
  noFallback: 'Yedek Dil Yok',
  autoSubtitles: 'Mevcut Altyazıları Otomatik İndir',
  includeAutoSubs: 'Otomatik Üretilen Altyazıları Dahil Et',
  autoEmbedSubs: 'Altyazıyı Medya Dosyasına Göm (Embed)',
  metadataSection: 'Metadata ve Dosya İsimlendirme',
  namingPresetLabel: 'İsimlendirme Şablonu',
  presetStandard: 'Standart (Başlık - [ID])',
  presetClean: 'Temiz (Sadece Başlık)',
  presetPlaylist: 'Çalma Listesi (Sıra - Başlık)',
  filenameTemplateLabel: 'Özel Dosya Şablonu (Gelişmiş)',
  filenameTemplatePlaceholder: '%(title)s.%(ext)s',
  embedMetadata: 'ID3 ve Medya Metaverilerini Otomatik Göm',
  autoSortDownloads: 'Kanal/Sanatçı Adına Göre Klasörle',
  postProcessAndReliabilitySection: 'İşleme ve Güvenilirlik',
  postProcessSubTitle: 'İndirme Sonrası Otomatik Dönüştürme',
  extractAudio: 'Sesi Ayıkla (Extract Audio)',
  convertVideo: 'Videoyu Dönüştür',
  reliabilitySubTitle: 'İndirme Güvenilirlik ve Hız Limitleri',
  enableArchive: 'İndirme Arşivi Tut (Mükerrer Önleme)',
  detectDuplicates: 'Yinelenen Dosyaları Tespit Et',
  continuePartial: 'Yarım Kalan İndirmelere Devam Et',
  formatFallback: 'Format Bulunamazsa En Uygununa Geç',
  rateLimitLabel: 'İndirme Hız Limiti',
  advancedDownloadTitle: 'Gelişmiş İndirme ve Cookie Ayarları',
  advancedSubtitle: 'Cookie yönetimi, fragment indirme ve zaman aşımı yapılandırması',
  cookiesModeLabel: 'Cookie Kullanım Modu',
  cookiesNone: 'Kullanma (None)',
  cookiesBrowser: 'Tarayıcıdan Çek (Browser)',
  cookiesFile: 'Dosyadan Oku (File)',
  cookiesBrowserLabel: 'Kaynak Tarayıcı',
  cookiesProfileLabel: 'Tarayıcı Profili',
  cookiesFileLabel: 'Cookie Dosyası Yolu (.txt)',
  concurrentFragments: 'Parçalı İndirme Fragment Sayısı',
  fragmentRetries: 'Fragment Yeniden Deneme Limiti',
  socketTimeout: 'Soket Zaman Aşımı',
  engineSection: 'Motor ve Harici Araç Yolları',
  ffmpegPathLabel: 'FFmpeg Yolu',
  aria2PathLabel: 'aria2c Yolu',
  seedTimeLabel: 'Torrent Gönderme Süresi (Seed Time)',
  maxConnectionsLabel: 'Torrent Maksimum Bağlantı Sayısı',
  autoCleanup: 'Geçici Dosyaları Otomatik Temizle',
  confirmResetTitle: 'Ayarları Sıfırlamak İstiyor musunuz?',
  confirmResetSubtitle: 'Tüm tercihleriniz varsayılan fabrika ayarlarına döndürülecektir.',
  cancel: 'İptal',
  confirmResetBtn: 'Evet, Sıfırla'
}

// State
const isSaving = ref(false)
const isInstallingTools = ref(false)
const isCheckingUpdates = ref(false)
const updateStatusMessage = ref('')
const advancedExpanded = ref(false)
const showResetModal = ref(false)
const errorMessage = ref('')
const toolsSummary = ref<Record<string, any>>({})

const formData = reactive({
  theme: 'dark',
  language: 'tr',
  notifications_enabled: true,
  auto_update_check: true,
  crash_reporting_enabled: true,
  close_to_tray: true,
  default_download_path: '',
  default_format: 'MP4',
  default_quality: 'best',
  concurrent_downloads: 2,
  history_limit: 1000,
  auto_subtitle_download: false,
  preferred_subtitle_language: 'tr',
  subtitle_fallback_language: 'en',
  subtitle_include_auto_generated: true,
  auto_embed_subtitles: false,
  embed_metadata: true,
  auto_sort_downloads: false,
  download_naming_preset: 'standard',
  download_filename_template: '',
  download_postprocess: {
    extract_audio: false,
    audio_format: 'mp3',
    audio_bitrate: '192k',
    convert_enabled: false,
    convert_format: 'mkv',
    embed_subtitles: false
  },
  download_robustness: {
    enable_archive: true,
    detect_duplicates: true,
    continue_partial: true,
    format_fallback: true,
    rate_limit_kbps: 0
  },
  download_advanced: {
    cookies_mode: 'none',
    cookies_browser: 'chrome',
    cookies_profile: '',
    cookies_file: '',
    concurrent_fragments: 1,
    fragment_retries: 10,
    socket_timeout_seconds: 30
  },
  ffmpeg_path: 'ffmpeg',
  aria2c_path: 'aria2c',
  torrent_seed_time: 0,
  torrent_max_connections: 16,
  auto_cleanup: false
})

const hasMissingTools = computed(() => {
  return Object.values(toolsSummary.value).some((t: any) => t.status !== 'available')
})

async function fetchHealth() {
  try {
    const health = await apiClient.getHealth()
    toolsSummary.value = health.tools?.tools || {}
  } catch (err: any) {
    errorMessage.value = err.message || 'Araç sağlık durumu alınamadı'
  }
}

async function fetchSettings() {
  try {
    const res = await apiClient.getSettings()
    Object.assign(formData, res)
    // Synchronize nested structures safely
    if (res.download_postprocess) Object.assign(formData.download_postprocess, res.download_postprocess)
    if (res.download_robustness) Object.assign(formData.download_robustness, res.download_robustness)
    if (res.download_advanced) Object.assign(formData.download_advanced, res.download_advanced)
  } catch (err: any) {
    errorMessage.value = err.message || 'Ayarlar yüklenemedi'
  }
}

function applyThemeLive() {
  document.documentElement.dataset.theme = formData.theme
  localStorage.setItem('ravn_theme', formData.theme)
}

async function browseDownloadDir() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      directory: true,
      multiple: false
    })
    if (selected && typeof selected === 'string') {
      formData.default_download_path = selected
    }
  } catch {
    const manual = prompt('İndirme klasörü yolunu girin:', formData.default_download_path)
    if (manual) formData.default_download_path = manual
  }
}

async function browseCookieFile() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Text / Cookies', extensions: ['txt', 'cookies'] }]
    })
    if (selected && typeof selected === 'string') {
      formData.download_advanced.cookies_file = selected
    }
  } catch {
    const manual = prompt('Cookie dosya yolunu girin:', formData.download_advanced.cookies_file)
    if (manual) formData.download_advanced.cookies_file = manual
  }
}

async function saveSettings() {
  isSaving.value = true
  errorMessage.value = ''
  try {
    await apiClient.patchSettings(JSON.parse(JSON.stringify(formData)))
    applyThemeLive()
    toast.success('Ayarlar başarıyla kaydedildi')
  } catch (err: any) {
    errorMessage.value = err.message || 'Ayarlar kaydedilemedi'
    toast.error(errorMessage.value)
  } finally {
    isSaving.value = false
  }
}

async function executeResetSettings() {
  showResetModal.value = false
  try {
    const res = await apiClient.resetSettings()
    Object.assign(formData, res)
    applyThemeLive()
    toast.success('Ayarlar varsayılana sıfırlandı')
  } catch (err: any) {
    toast.error(err.message || 'Sıfırlama başarısız')
  }
}

async function installMissingTools() {
  isInstallingTools.value = true
  try {
    const res = await apiClient.installTools()
    if (res.success) {
      toast.success('Eksik araçlar başarıyla yüklendi')
      await fetchHealth()
    } else {
      toast.warning(res.message || 'Araç yükleme desteklenmiyor')
    }
  } catch (err: any) {
    toast.error(err.message || 'Araç yükleme başarısız')
  } finally {
    isInstallingTools.value = false
  }
}

async function checkForUpdates() {
  isCheckingUpdates.value = true
  updateStatusMessage.value = ''
  try {
    const res = await apiClient.checkUpdates()
    if (res.has_update) {
      updateStatusMessage.value = `Yeni sürüm mevcut: v${res.latest_version} (${res.release_name || ''})`
      toast.info(`Yeni güncelleme bulundu: v${res.latest_version}`)
    } else {
      updateStatusMessage.value = `Uygulama güncel: v${res.current_version}`
      toast.success(`Uygulama güncel: v${res.current_version}`)
    }
  } catch (err: any) {
    updateStatusMessage.value = 'Güncelleme kontrolü başarısız'
    toast.error(err.message || 'Güncelleme kontrolü başarısız')
  } finally {
    isCheckingUpdates.value = false
  }
}

async function exportSettings() {
  try {
    const res = await apiClient.exportSettings()
    toast.success(`Ayarlar dışa aktarıldı: ${res.output_file}`)
  } catch (err: any) {
    toast.error(err.message || 'Dışa aktarma başarısız')
  }
}

async function importSettings() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'JSON Settings', extensions: ['json'] }]
    })
    if (selected && typeof selected === 'string') {
      const res = await apiClient.importSettings({ file_path: selected })
      Object.assign(formData, res.config)
      applyThemeLive()
      toast.success('Ayarlar başarıyla içe aktarıldı')
    }
  } catch {
    const manual = prompt('Ayar JSON dosya yolunu girin:')
    if (manual) {
      try {
        const res = await apiClient.importSettings({ file_path: manual })
        Object.assign(formData, res.config)
        applyThemeLive()
        toast.success('Ayarlar içe aktarıldı')
      } catch (e: any) {
        toast.error(e.message || 'İçe aktarma başarısız')
      }
    }
  }
}

async function loadAll() {
  await Promise.all([fetchSettings(), fetchHealth()])
}

onMounted(async () => {
  await loadAll()
})
</script>
