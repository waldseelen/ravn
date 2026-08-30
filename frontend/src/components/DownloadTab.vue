<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header / Mode Switcher -->
    <div
      class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl border shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 rounded-xl border flex items-center justify-center text-xl font-bold"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
        >
          <span>↓</span>
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

      <!-- Mode Selector Tabs -->
      <div
        class="flex p-1 rounded-xl border shrink-0"
        style="background-color: var(--bg-input); border-color: var(--border-subtle);"
      >
        <button
          v-for="mode in modes"
          :key="mode.id"
          @click="activeMode = mode.id"
          class="px-4 py-2 text-xs font-semibold rounded-lg transition cursor-pointer"
          :style="activeMode === mode.id ? 'background-color: var(--accent-brass); color: var(--bg-primary); font-weight: bold;' : 'color: var(--text-secondary);'"
        >
          {{ mode.icon }} {{ mode.label }}
        </button>
      </div>
    </div>

    <!-- P3-T9 aria2c Missing Warning Banner (Shown only in Torrent mode if aria2c missing) -->
    <div
      v-if="activeMode === 'torrent' && isAria2Missing"
      class="p-4 rounded-2xl border space-y-1 shadow-lg"
      style="background-color: var(--warning-bg); border-color: var(--status-warning);"
    >
      <div class="flex items-center gap-2 text-xs font-bold" style="color: var(--status-warning);">
        <span>⚠</span>
        <span>{{ t.aria2cMissing }}</span>
      </div>
      <p class="text-[11px]" style="color: var(--text-secondary);">
        {{ t.aria2cMissingDetail }}
      </p>
    </div>

    <!-- MODE 1: SINGLE URL & PLAYLIST FLOW (P3-T1 to P3-T7) -->
    <div v-if="activeMode === 'single'" class="space-y-6">
      <!-- P3-T1 & P3-T5: Source Input Card with Drag & Drop Dropzone -->
      <div
        class="p-6 rounded-2xl border space-y-4 shadow-sm transition-all"
        :class="{ 'ring-2': isDragging }"
        :style="{
          backgroundColor: 'var(--bg-surface)',
          borderColor: isDragging ? 'var(--accent-brass)' : 'var(--border-subtle)'
        }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <div class="flex items-center justify-between gap-3">
          <label class="block text-xs font-bold uppercase tracking-wider flex items-center gap-2" style="color: var(--text-muted);">
            <span>🔗 {{ t.sourceInputLabel }}</span>
            <span
              v-if="sourceClassifier"
              class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border"
              :style="{
                backgroundColor: 'var(--bg-input)',
                borderColor: 'var(--border-brass)',
                color: 'var(--accent-brass)'
              }"
            >
              {{ sourceClassifier }}
            </span>
          </label>

          <!-- Live URL Validation Icon (P3-T4) -->
          <div class="flex items-center gap-3 text-xs font-mono">
            <span
              v-if="singleUrl"
              class="font-bold flex items-center gap-1 text-[11px]"
              :style="{ color: isUrlValid ? 'var(--status-done)' : 'var(--status-warning)' }"
            >
              <span>{{ isUrlValid ? '✓' : '⚠' }}</span>
              <span>{{ isUrlValid ? t.validUrl : t.invalidUrl }}</span>
            </span>

            <span
              v-if="estimatedSize"
              class="text-[11px]"
              style="color: var(--text-muted);"
            >
              ~{{ estimatedSize }}
            </span>
          </div>
        </div>

        <div class="flex flex-col sm:flex-row gap-3">
          <div class="relative flex-1">
            <input
              v-model="singleUrl"
              @input="onUrlInput"
              type="text"
              :placeholder="t.urlPlaceholder"
              class="w-full px-4 py-3 rounded-xl text-xs border outline-none font-mono focus:ring-1"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            />
          </div>

          <button
            @click="browseTorrentFile"
            class="px-4 py-3 rounded-xl border text-xs font-semibold hover:opacity-90 cursor-pointer shrink-0"
            style="background-color: var(--bg-card); color: var(--text-secondary); border-color: var(--border-subtle);"
            :title="t.browseTorrentTooltip"
          >
            📁 {{ t.browseTorrent }}
          </button>

          <button
            @click="fetchInfo"
            :disabled="!singleUrl || loadingInfo"
            class="px-5 py-3 text-xs font-semibold rounded-xl border transition disabled:opacity-50 cursor-pointer shrink-0"
            style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
          >
            {{ loadingInfo ? t.analyzing : `🔍 ${t.fetchInfo}` }}
          </button>
        </div>

        <!-- P3-T3: Platform and Preset Bar (Collapsible or Inline) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-3 border-t text-xs" style="border-color: var(--border-subtle);">
          <!-- Platform Selector -->
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
              ❖ {{ t.platformLabel }}
            </label>
            <select
              v-model="selectedPlatform"
              @change="onPlatformChange"
              class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option v-for="p in platforms" :key="p.id" :value="p.id">
                {{ p.icon }} {{ p.label }}
              </option>
            </select>
          </div>

          <!-- Download Profile Presets -->
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
              ⚡ {{ t.profilePresetLabel }}
            </label>
            <select
              v-model="selectedProfile"
              @change="onProfileChange"
              class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option value="custom">{{ t.profileCustom }}</option>
              <option value="music">{{ t.profileMusic }}</option>
              <option value="podcast">{{ t.profilePodcast }}</option>
              <option value="archive">{{ t.profileArchive }}</option>
              <option value="social">{{ t.profileSocial }}</option>
            </select>
          </div>

          <!-- P3-T2: Output Mode Segmented Selector (Video vs Audio) -->
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
              🎧/🎬 {{ t.mediaTypeLabel }}
            </label>
            <div
              class="flex p-1 rounded-xl border"
              style="background-color: var(--bg-input); border-color: var(--border-subtle);"
            >
              <button
                @click="mediaType = 'video'"
                class="flex-1 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer"
                :style="mediaType === 'video' ? 'background-color: var(--accent-brass); color: var(--bg-primary); font-weight: bold;' : 'color: var(--text-secondary);'"
              >
                🎬 {{ t.typeVideo }}
              </button>
              <button
                @click="mediaType = 'audio'"
                class="flex-1 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer"
                :style="mediaType === 'audio' ? 'background-color: var(--accent-brass); color: var(--bg-primary); font-weight: bold;' : 'color: var(--text-secondary);'"
              >
                🎵 {{ t.typeAudio }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- P3-T6: Two Column Layout (Video Column & Audio Column Settings) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- VIDEO COLUMN -->
        <div
          class="p-6 rounded-2xl border space-y-4 shadow-sm transition"
          :style="{
            backgroundColor: 'var(--bg-surface)',
            borderColor: mediaType === 'video' ? 'var(--border-brass)' : 'var(--border-subtle)',
            opacity: mediaType === 'video' ? '1' : '0.7'
          }"
        >
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-bold flex items-center gap-2" style="color: var(--text-primary);">
              <span>🎬</span>
              <span>{{ t.videoColumnTitle }}</span>
            </h2>
            <span
              v-if="mediaType === 'video'"
              class="text-[10px] uppercase font-mono px-2 py-0.5 rounded border font-bold"
              style="background-color: var(--bg-card); border-color: var(--border-brass); color: var(--accent-brass);"
            >
              {{ t.activeSelection }}
            </span>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-muted);">
                {{ t.videoQuality }}
              </label>
              <select
                v-model="videoQuality"
                class="w-full rounded-xl px-3 py-2 text-xs border outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              >
                <option value="best">{{ t.qualityBest }} (4K/1080p)</option>
                <option value="1080p">1080p Full HD</option>
                <option value="720p">720p HD</option>
                <option value="480p">480p SD</option>
                <option value="360p">360p Low</option>
              </select>
            </div>

            <div>
              <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-muted);">
                {{ t.videoFormat }}
              </label>
              <select
                v-model="videoFormat"
                class="w-full rounded-xl px-3 py-2 text-xs border outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              >
                <option value="mp4">MP4 (Universal Compatibility)</option>
                <option value="mkv">MKV (Multi-audio / Subtitles)</option>
                <option value="webm">WebM (VP9/Opus)</option>
              </select>
            </div>

            <div class="flex items-center gap-2 pt-2">
              <input type="checkbox" v-model="embedSubtitles" id="chk-sub" class="rounded cursor-pointer" />
              <label for="chk-sub" class="text-xs cursor-pointer" style="color: var(--text-secondary);">
                {{ t.embedSubtitlesLabel }}
              </label>
            </div>
          </div>

          <button
            @click="startDownloadDirect('video')"
            :disabled="!singleUrl || downloading"
            class="w-full py-3 text-xs font-bold rounded-xl shadow-lg transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            style="background-color: var(--accent-brass); color: var(--bg-primary);"
          >
            <span>↓</span>
            <span>{{ downloading && mediaType === 'video' ? t.downloading : t.downloadVideo }}</span>
          </button>
        </div>

        <!-- AUDIO COLUMN -->
        <div
          class="p-6 rounded-2xl border space-y-4 shadow-sm transition"
          :style="{
            backgroundColor: 'var(--bg-surface)',
            borderColor: mediaType === 'audio' ? 'var(--border-brass)' : 'var(--border-subtle)',
            opacity: mediaType === 'audio' ? '1' : '0.7'
          }"
        >
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-bold flex items-center gap-2" style="color: var(--text-primary);">
              <span>🎵</span>
              <span>{{ t.audioColumnTitle }}</span>
            </h2>
            <span
              v-if="mediaType === 'audio'"
              class="text-[10px] uppercase font-mono px-2 py-0.5 rounded border font-bold"
              style="background-color: var(--bg-card); border-color: var(--border-brass); color: var(--accent-brass);"
            >
              {{ t.activeSelection }}
            </span>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-muted);">
                {{ t.audioFormat }}
              </label>
              <select
                v-model="audioFormat"
                class="w-full rounded-xl px-3 py-2 text-xs border outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              >
                <option value="mp3">MP3 (Universal Audio)</option>
                <option value="aac">AAC (M4A High Efficiency)</option>
                <option value="flac">FLAC (Lossless Studio Quality)</option>
                <option value="opus">OPUS (Modern Compact)</option>
                <option value="wav">WAV (Uncompressed PCM)</option>
                <option value="m4a">M4A (Apple Audio)</option>
              </select>
            </div>

            <div>
              <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-muted);">
                {{ t.audioBitrate }}
              </label>
              <select
                v-model="audioBitrate"
                class="w-full rounded-xl px-3 py-2 text-xs border outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              >
                <option value="320k">320 kbps (High Fidelity)</option>
                <option value="256k">256 kbps (Standard High)</option>
                <option value="192k">192 kbps (Balanced)</option>
                <option value="128k">128 kbps (Voice / Lightweight)</option>
                <option value="0">VBR 0 (Variable Max)</option>
              </select>
            </div>

            <div class="flex items-center gap-2 pt-2">
              <input type="checkbox" v-model="embedLyrics" id="chk-lyrics" class="rounded cursor-pointer" />
              <label for="chk-lyrics" class="text-xs cursor-pointer" style="color: var(--text-secondary);">
                {{ t.embedLyricsLabel }}
              </label>
            </div>
          </div>

          <button
            @click="startDownloadDirect('audio')"
            :disabled="!singleUrl || downloading"
            class="w-full py-3 text-xs font-bold rounded-xl shadow-lg transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            style="background-color: var(--accent-brass); color: var(--bg-primary);"
          >
            <span>↓</span>
            <span>{{ downloading && mediaType === 'audio' ? t.downloading : t.downloadAudio }}</span>
          </button>
        </div>
      </div>

      <!-- Playlist Inspection Button (When playlist detected) -->
      <div
        v-if="isPlaylistUrl"
        class="p-4 rounded-2xl border flex items-center justify-between gap-4"
        style="background-color: var(--bg-card); border-color: var(--border-brass);"
      >
        <div class="flex items-center gap-3">
          <span class="text-lg font-bold" style="color: var(--accent-brass);">≡</span>
          <div>
            <h3 class="text-xs font-bold" style="color: var(--text-primary);">
              {{ t.playlistDetected }}
            </h3>
            <p class="text-[11px]" style="color: var(--text-muted);">
              {{ t.playlistDetectedDetail }}
            </p>
          </div>
        </div>

        <button
          @click="openPlaylistReview"
          class="px-5 py-2.5 rounded-xl border text-xs font-bold transition flex items-center gap-2 hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-surface); color: var(--accent-brass); border-color: var(--border-brass);"
        >
          <span>≡</span>
          <span>{{ t.reviewAndSortPlaylist }}</span>
        </button>
      </div>

      <!-- Extracted Single Video Metadata Preview Card -->
      <div
        v-if="mediaInfo"
        class="p-6 rounded-2xl border space-y-4 shadow-sm"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <h3 class="text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
          {{ t.mediaPreviewTitle }}
        </h3>
        <div class="flex flex-col sm:flex-row gap-4 items-start">
          <img
            v-if="mediaInfo.thumbnail"
            :src="mediaInfo.thumbnail"
            alt="Thumbnail"
            class="w-48 h-28 object-cover rounded-xl border shrink-0"
            style="border-color: var(--border-subtle);"
          />
          <div class="space-y-1 min-w-0 flex-1">
            <h4 class="text-sm font-bold truncate" style="color: var(--text-primary);">
              {{ mediaInfo.title }}
            </h4>
            <div class="text-xs space-y-0.5" style="color: var(--text-secondary);">
              <p v-if="mediaInfo.uploader"><strong>{{ t.channel }}:</strong> {{ mediaInfo.uploader }}</p>
              <p v-if="mediaInfo.duration"><strong>{{ t.duration }}:</strong> {{ formatDurationSec(mediaInfo.duration) }}</p>
              <p v-if="mediaInfo.view_count"><strong>{{ t.views }}:</strong> {{ mediaInfo.view_count.toLocaleString() }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODE 2: TORRENT & MAGNET TAB (P3-T9) -->
    <div v-if="activeMode === 'torrent'" class="space-y-6">
      <div
        class="p-6 rounded-2xl border space-y-4 shadow-sm"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
          🧲 {{ t.torrentSourceLabel }}
        </label>

        <div class="flex flex-col sm:flex-row gap-3">
          <input
            v-model="torrentUri"
            type="text"
            :placeholder="t.torrentPlaceholder"
            class="flex-1 px-4 py-3 rounded-xl text-xs border outline-none font-mono focus:ring-1"
            style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
          />
          <button
            @click="browseTorrentFile"
            class="px-4 py-3 rounded-xl border text-xs font-semibold hover:opacity-90 cursor-pointer shrink-0"
            style="background-color: var(--bg-card); color: var(--text-secondary); border-color: var(--border-subtle);"
          >
            📁 {{ t.browseTorrent }}
          </button>
        </div>

        <!-- Mode selector: Full / Sequential / Stream -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-3 border-t text-xs" style="border-color: var(--border-subtle);">
          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
              ⚡ {{ t.torrentModeLabel }}
            </label>
            <select
              v-model="torrentMode"
              class="w-full rounded-xl px-3 py-2 text-xs border outline-none font-mono"
              style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
            >
              <option value="FULL">{{ t.torrentFull }}</option>
              <option value="SEQUENTIAL">{{ t.torrentSequential }}</option>
              <option value="STREAM">{{ t.torrentStream }}</option>
            </select>
          </div>

          <div>
            <label class="block text-[11px] font-semibold mb-1" style="color: var(--text-secondary);">
              📁 {{ t.outputFolderLabel }}
            </label>
            <div class="flex gap-2">
              <input
                v-model="outputDir"
                type="text"
                placeholder="Default Downloads"
                class="flex-1 rounded-xl px-3 py-2 text-xs border outline-none font-mono"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              />
              <button
                @click="browseOutputDir"
                class="px-3 py-2 rounded-xl border text-xs font-semibold cursor-pointer"
                style="background-color: var(--bg-card); border-color: var(--border-subtle);"
              >
                📁
              </button>
            </div>
          </div>

          <div class="flex items-end">
            <button
              @click="startTorrentDownload"
              :disabled="!torrentUri || downloading"
              class="w-full py-2.5 text-xs font-bold rounded-xl shadow-lg transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              style="background-color: var(--accent-brass); color: var(--bg-primary);"
            >
              <span>⊕</span>
              <span>{{ t.startTorrentDownload }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODE 3: BATCH URLS TAB (P3-T10) -->
    <div v-if="activeMode === 'batch'" class="space-y-6">
      <div
        class="p-6 rounded-2xl border space-y-4 shadow-sm"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <div class="flex items-center justify-between">
          <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
            📝 {{ t.batchHeader }}
          </label>
          <span class="text-[11px] font-mono" style="color: var(--text-muted);">
            {{ batchUrlList.length }} {{ t.validUrlsDetected }}
          </span>
        </div>

        <textarea
          v-model="batchUrls"
          rows="7"
          :placeholder="t.batchPlaceholder"
          class="w-full p-4 rounded-xl text-xs border font-mono outline-none focus:ring-1"
          style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
        ></textarea>

        <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t" style="border-color: var(--border-subtle);">
          <div class="flex items-center gap-4 text-xs">
            <div class="flex items-center gap-2">
              <span style="color: var(--text-muted);">Format:</span>
              <select
                v-model="selectedFormat"
                class="rounded-lg px-2 py-1 border text-xs outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              >
                <option value="mp4">MP4 (Video)</option>
                <option value="mp3">MP3 (Audio)</option>
                <option value="mkv">MKV (Video)</option>
                <option value="flac">FLAC (Audio)</option>
              </select>
            </div>

            <div class="flex items-center gap-2">
              <span style="color: var(--text-muted);">Quality:</span>
              <select
                v-model="selectedQuality"
                class="rounded-lg px-2 py-1 border text-xs outline-none"
                style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-primary);"
              >
                <option value="best">Best</option>
                <option value="1080p">1080p</option>
                <option value="720p">720p</option>
                <option value="audio">Audio Only</option>
              </select>
            </div>
          </div>

          <button
            @click="startBatchDownload"
            :disabled="batchUrlList.length === 0 || downloading"
            class="px-8 py-2.5 text-xs font-bold rounded-xl shadow-lg transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
            style="background-color: var(--accent-brass); color: var(--bg-primary);"
          >
            <span>↓</span>
            <span>{{ t.enqueueAll }} ({{ batchUrlList.length }})</span>
          </button>
        </div>
      </div>
    </div>

    <!-- P3-T11: ErrorPanel Component Integration -->
    <ErrorPanel
      v-if="errorInfo"
      :title="errorInfo.title"
      :message="errorInfo.message"
      :traceback="errorInfo.traceback"
      @retry="retryLastAction"
    />

    <!-- P3-T7: Playlist Sort & Filter Modal Dialog -->
    <PlaylistSortDialog
      :isOpen="isPlaylistDialogOpen"
      :entries="playlistEntries"
      @close="isPlaylistDialogOpen = false"
      @confirm="onPlaylistConfirmed"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useToastStore } from '../stores/toastStore'
import { useDownloadStore } from '../stores/downloadStore'
import { apiClient } from '../services/apiClient'
import ErrorPanel from './ErrorPanel.vue'
import PlaylistSortDialog from './PlaylistSortDialog.vue'

const route = useRoute()
const toastStore = useToastStore()
const downloadStore = useDownloadStore()

const t = {
  title: 'Media Acquisition & Downloads',
  subtitle: 'Single URLs, Playlist Extraction, Batch Links & Torrent/Magnet',
  aria2cMissing: 'aria2c Downloader Engine Missing',
  aria2cMissingDetail: 'Torrent & Magnet downloads require aria2c binary in PATH or app directory.',
  sourceInputLabel: 'Target Source Link',
  urlPlaceholder: 'Paste video, audio, playlist or magnet link...',
  validUrl: 'Valid URL',
  invalidUrl: 'Unrecognized URL',
  browseTorrent: 'Browse .torrent',
  browseTorrentTooltip: 'Select local .torrent file',
  fetchInfo: 'Fetch Info',
  analyzing: 'Analyzing...',
  platformLabel: 'Platform Profile',
  profilePresetLabel: 'Preset Config',
  profileCustom: 'Custom Selection',
  profileMusic: 'Music (MP3 320k)',
  profilePodcast: 'Podcast (AAC 192k)',
  profileArchive: 'Archive (Lossless FLAC)',
  profileSocial: 'Social Clip (MP4 1080p)',
  mediaTypeLabel: 'Media Mode',
  typeVideo: 'Video',
  typeAudio: 'Audio',
  videoColumnTitle: 'Video Acquisition',
  activeSelection: 'Selected Mode',
  videoQuality: 'Video Quality',
  qualityBest: 'Best Available',
  videoFormat: 'Video Container',
  embedSubtitlesLabel: 'Auto-embed Subtitles (TR/EN)',
  downloadVideo: 'Download Video',
  audioColumnTitle: 'Audio Extraction',
  audioFormat: 'Audio Format',
  audioBitrate: 'Bitrate Quality',
  embedLyricsLabel: 'Embed ID3 Tags & Cover Art',
  downloadAudio: 'Extract Audio',
  downloading: 'Queuing...',
  playlistDetected: 'Playlist / Set URL Detected',
  playlistDetectedDetail: 'Review track listing, filter items by duration or popularity, and sort order before acquisition.',
  reviewAndSortPlaylist: 'Review & Sort Items',
  mediaPreviewTitle: 'Media Metadata Preview',
  channel: 'Channel',
  duration: 'Duration',
  views: 'Views',
  torrentSourceLabel: 'Magnet Link or Local .torrent File',
  torrentPlaceholder: 'magnet:?xt=urn:btih:... or /path/to/file.torrent',
  torrentModeLabel: 'Acquisition Mode',
  torrentFull: 'FULL (Complete Download)',
  torrentSequential: 'SEQUENTIAL (Playback Order)',
  torrentStream: 'STREAM (Local HTTP Streaming)',
  outputFolderLabel: 'Destination Directory',
  startTorrentDownload: 'Start Torrent Task',
  batchHeader: 'Batch URL Acquisition',
  validUrlsDetected: 'valid links',
  batchPlaceholder: 'Paste multiple URLs (one per line)...\nhttps://...\nhttps://...',
  enqueueAll: 'Enqueue All Tasks'
}

const modes = [
  { id: 'single', label: 'Single / Playlist', icon: '↓' },
  { id: 'torrent', label: 'Torrent & Magnet', icon: '⊕' },
  { id: 'batch', label: 'Batch URLs', icon: '📝' }
]

const platforms = [
  { id: 'auto', label: 'Auto Detect', icon: '❖' },
  { id: 'youtube', label: 'YouTube', icon: '▶' },
  { id: 'twitter', label: 'Twitter / X', icon: '𝕏' },
  { id: 'instagram', label: 'Instagram', icon: '📸' },
  { id: 'tiktok', label: 'TikTok', icon: '🎵' },
  { id: 'vimeo', label: 'Vimeo', icon: '🎬' },
  { id: 'soundcloud', label: 'SoundCloud', icon: '☁' }
]

const activeMode = ref('single')
const singleUrl = ref('')
const selectedPlatform = ref('auto')
const selectedProfile = ref('custom')
const mediaType = ref<'video' | 'audio'>('video')

const videoQuality = ref('best')
const videoFormat = ref('mp4')
const embedSubtitles = ref(false)

const audioFormat = ref('mp3')
const audioBitrate = ref('320k')
const embedLyrics = ref(true)

const selectedFormat = ref('mp4')
const selectedQuality = ref('best')
const outputDir = ref('')

const isDragging = ref(false)
const loadingInfo = ref(false)
const downloading = ref(false)
const mediaInfo = ref<any>(null)
const isAria2Missing = ref(false)

const torrentUri = ref('')
const torrentMode = ref('FULL')
const batchUrls = ref('')

const errorInfo = ref<{ title: string; message: string; traceback?: string } | null>(null)
const isPlaylistDialogOpen = ref(false)
const playlistEntries = ref<any[]>([])

const isUrlValid = computed(() => {
  if (!singleUrl.value.trim()) return false
  const u = singleUrl.value.trim().toLowerCase()
  return u.startsWith('http://') || u.startsWith('https://') || u.startsWith('magnet:?') || u.endsWith('.torrent')
})

const isPlaylistUrl = computed(() => {
  const u = singleUrl.value.toLowerCase()
  return u.includes('list=') || u.includes('/playlist') || u.includes('/sets/') || u.includes('/collection/')
})

const sourceClassifier = computed(() => {
  if (!singleUrl.value.trim()) return ''
  const u = singleUrl.value.trim().toLowerCase()
  if (u.startsWith('magnet:?')) return 'Magnet Link'
  if (u.endsWith('.torrent')) return 'Torrent File'
  if (isPlaylistUrl.value) return 'Playlist URL'
  if (u.includes('youtube.com') || u.includes('youtu.be')) return 'YouTube'
  if (u.includes('twitter.com') || u.includes('x.com')) return 'Twitter / X'
  if (u.includes('instagram.com')) return 'Instagram'
  if (u.includes('tiktok.com')) return 'TikTok'
  if (u.includes('soundcloud.com')) return 'SoundCloud'
  if (isUrlValid.value) return 'Media URL'
  return ''
})

const estimatedSize = computed(() => {
  if (!mediaInfo.value) return ''
  if (mediaInfo.value.filesize_approx_mb) return `${mediaInfo.value.filesize_approx_mb} MB`
  if (mediaInfo.value.duration) {
    const min = mediaInfo.value.duration / 60
    const est = mediaType.value === 'audio' ? min * 2.5 : min * 18
    return est >= 1024 ? `${(est / 1024).toFixed(1)} GB` : `${est.toFixed(0)} MB`
  }
  return ''
})

const batchUrlList = computed(() => {
  return batchUrls.value
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.startsWith('http://') || line.startsWith('https://') || line.startsWith('magnet:'))
})

function onUrlInput() {
  errorInfo.value = null
  const u = singleUrl.value.trim()
  if (u.startsWith('magnet:?') || u.endsWith('.torrent')) {
    activeMode.value = 'torrent'
    torrentUri.value = u
  }
}

function onPlatformChange() {
  if (selectedPlatform.value === 'soundcloud') {
    mediaType.value = 'audio'
    audioFormat.value = 'mp3'
  }
}

function onProfileChange() {
  switch (selectedProfile.value) {
    case 'music':
      mediaType.value = 'audio'
      audioFormat.value = 'mp3'
      audioBitrate.value = '320k'
      embedLyrics.value = true
      break
    case 'podcast':
      mediaType.value = 'audio'
      audioFormat.value = 'aac'
      audioBitrate.value = '192k'
      embedLyrics.value = true
      break
    case 'archive':
      mediaType.value = 'audio'
      audioFormat.value = 'flac'
      embedLyrics.value = true
      break
    case 'social':
      mediaType.value = 'video'
      videoFormat.value = 'mp4'
      videoQuality.value = '1080p'
      break
  }
}

async function handleDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    const file = e.dataTransfer.files[0]
    if (file.name.endsWith('.torrent')) {
      activeMode.value = 'torrent'
      torrentUri.value = (file as any).path || file.name
      toastStore.info(`Loaded torrent file: ${file.name}`)
    }
  } else if (e.dataTransfer?.types.includes('text/plain')) {
    const text = e.dataTransfer.getData('text/plain')
    if (text) {
      singleUrl.value = text.trim()
      onUrlInput()
    }
  }
}

async function browseTorrentFile() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Torrent Files', extensions: ['torrent'] }]
    })
    if (selected && typeof selected === 'string') {
      activeMode.value = 'torrent'
      torrentUri.value = selected
      toastStore.success(`Selected torrent: ${selected}`)
    }
  } catch {
    toastStore.warning('Desktop file selector not active; paste file path directly.')
  }
}

async function browseOutputDir() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({ directory: true, multiple: false })
    if (selected && typeof selected === 'string') {
      outputDir.value = selected
    }
  } catch {
    toastStore.info('Enter output directory manually.')
  }
}

async function fetchInfo() {
  if (!singleUrl.value.trim()) return
  loadingInfo.value = true
  errorInfo.value = null
  mediaInfo.value = null

  try {
    if (isPlaylistUrl.value) {
      const plData = await apiClient.extractPlaylistInfo(singleUrl.value.trim())
      playlistEntries.value = plData.entries || []
      isPlaylistDialogOpen.value = true
      toastStore.info(`Extracted playlist with ${playlistEntries.value.length} items`)
    } else {
      const info = await apiClient.extractInfo(singleUrl.value.trim())
      mediaInfo.value = info
      toastStore.success(`Fetched: ${info.title || 'Media Metadata'}`)
    }
  } catch (e: any) {
    errorInfo.value = {
      title: 'Failed to Extract Media Information',
      message: e.message || 'Could not reach server or media URL is unavailable.',
      traceback: String(e)
    }
    toastStore.error('Media info extraction failed')
  } finally {
    loadingInfo.value = false
  }
}

async function openPlaylistReview() {
  if (playlistEntries.value.length === 0) {
    await fetchInfo()
  } else {
    isPlaylistDialogOpen.value = true
  }
}

async function startDownloadDirect(type: 'video' | 'audio') {
  if (!singleUrl.value.trim()) return
  downloading.value = true
  errorInfo.value = null

  try {
    const rawUrl = singleUrl.value.trim()
    const payload = {
      url: rawUrl,
      output_dir: outputDir.value || '',
      format: type === 'video' ? videoFormat.value : audioFormat.value,
      quality: type === 'video' ? videoQuality.value : 'audio',
      embed_metadata: true,
      embed_lyrics: embedLyrics.value,
      audio_bitrate: type === 'audio' ? audioBitrate.value : undefined
    }

    const res = await apiClient.startDownload(payload)
    downloadStore.addTask({
      id: res.task_id,
      name: mediaInfo.value?.title || rawUrl,
      type: 'download',
      status: 'running',
      progress: 0,
      progress_message: 'Starting download...',
      started_at: new Date().toISOString()
    })
    downloadStore.fetchQueue()

    const destFolder = outputDir.value || 'Downloads'
    toastStore.success(`Download started! Target: ${destFolder}`)
    singleUrl.value = ''
    mediaInfo.value = null
  } catch (e: any) {
    errorInfo.value = {
      title: 'Download Enqueue Failed',
      message: e.message || 'Could not send download task to backend queue.',
      traceback: String(e)
    }
    toastStore.error('Failed to start download')
  } finally {
    downloading.value = false
  }
}

async function onPlaylistConfirmed(selectedUrls: string[]) {
  isPlaylistDialogOpen.value = false
  if (selectedUrls.length === 0) return

  downloading.value = true
  try {
    const res = await apiClient.startBatchDownload({
      urls: selectedUrls,
      output_dir: outputDir.value || '',
      format: mediaType.value === 'video' ? videoFormat.value : audioFormat.value,
      quality: mediaType.value === 'video' ? videoQuality.value : 'audio'
    })
    downloadStore.fetchQueue()
    toastStore.success(`Enqueued ${res.enqueued} playlist tracks`)
    singleUrl.value = ''
  } catch (e: any) {
    errorInfo.value = {
      title: 'Playlist Enqueue Failed',
      message: e.message || 'Could not queue playlist tracks.',
      traceback: String(e)
    }
  } finally {
    downloading.value = false
  }
}

async function startTorrentDownload() {
  if (!torrentUri.value.trim()) return
  downloading.value = true
  errorInfo.value = null

  try {
    const res = await apiClient.startTorrentDownload({
      source: torrentUri.value.trim(),
      output_dir: outputDir.value || '',
      mode: torrentMode.value
    })
    downloadStore.fetchQueue()
    toastStore.success(`Torrent queued in ${res.mode} mode`)
    torrentUri.value = ''
  } catch (e: any) {
    errorInfo.value = {
      title: 'Torrent Download Error',
      message: e.message || 'Failed to start aria2c torrent session.',
      traceback: String(e)
    }
    toastStore.error('Torrent startup failed')
  } finally {
    downloading.value = false
  }
}

async function startBatchDownload() {
  if (batchUrlList.value.length === 0) return
  downloading.value = true
  errorInfo.value = null

  try {
    const res = await apiClient.startBatchDownload({
      urls: batchUrlList.value,
      output_dir: outputDir.value || '',
      format: selectedFormat.value,
      quality: selectedQuality.value
    })
    downloadStore.fetchQueue()
    toastStore.success(`Enqueued ${res.enqueued} batch URLs`)
    batchUrls.value = ''
  } catch (e: any) {
    errorInfo.value = {
      title: 'Batch Download Failed',
      message: e.message || 'Could not enqueue batch items.',
      traceback: String(e)
    }
  } finally {
    downloading.value = false
  }
}

function retryLastAction() {
  if (activeMode.value === 'single') {
    startDownloadDirect(mediaType.value)
  } else if (activeMode.value === 'torrent') {
    startTorrentDownload()
  } else if (activeMode.value === 'batch') {
    startBatchDownload()
  }
}

function formatDurationSec(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}m ${s}s`
}

function checkQueryParams() {
  if (route.query.url && typeof route.query.url === 'string') {
    singleUrl.value = route.query.url
    activeMode.value = 'single'
    onUrlInput()
  }
  if (route.query.tab === 'torrent') {
    activeMode.value = 'torrent'
  } else if (route.query.tab === 'batch') {
    activeMode.value = 'batch'
  } else if (route.query.tab === 'playlist') {
    activeMode.value = 'single'
  }
}

onMounted(async () => {
  checkQueryParams()
  try {
    const health = await apiClient.getHealth()
    if (health?.tools?.missing_optional?.includes('aria2c')) {
      isAria2Missing.value = true
    }
  } catch {
    // API unready
  }
})

watch(() => route.query, () => {
  checkQueryParams()
})
</script>

