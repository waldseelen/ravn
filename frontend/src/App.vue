<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 flex font-sans antialiased">
    <!-- Sidebar Navigation -->
    <aside class="w-64 bg-slate-900/90 backdrop-blur border-r border-slate-800/80 p-4 flex flex-col justify-between space-y-6">
      <div class="space-y-6">
        <!-- Brand Header -->
        <div class="flex items-center justify-between px-2">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-black text-white text-lg shadow-lg shadow-indigo-500/30">
              R
            </div>
            <div>
              <span class="text-base font-bold tracking-wider text-slate-100 block">RAVN</span>
              <span class="text-[10px] text-slate-400 font-medium block">Media Pipeline v2.0</span>
            </div>
          </div>
          <span class="text-[10px] px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded-full font-mono border border-indigo-500/20">
            Tauri
          </span>
        </div>

        <!-- Navigation Links -->
        <nav class="space-y-4">
          <!-- Acquisition Section -->
          <div class="space-y-1">
            <span class="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500">Acquisition</span>
            <RouterLink
              to="/"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-200"
              active-class="bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
            >
              <span>⚡</span>
              <span>Download & Torrent</span>
            </RouterLink>
            <RouterLink
              to="/queue"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all duration-200"
              active-class="bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
            >
              <span>📊</span>
              <span>Live Queue</span>
            </RouterLink>
          </div>

          <!-- Studio Tools Section -->
          <div class="space-y-1">
            <span class="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500">Studio & Processing</span>
            <RouterLink
              to="/converter"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all duration-200"
              active-class="bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
            >
              <span>🎬</span>
              <span>Media Converter</span>
            </RouterLink>
            <RouterLink
              to="/subtitles"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all duration-200"
              active-class="bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
            >
              <span>📝</span>
              <span>Subtitle Studio</span>
            </RouterLink>
            <RouterLink
              to="/filters"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all duration-200"
              active-class="bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
            >
              <span>🎨</span>
              <span>Filters & Equalizer</span>
            </RouterLink>
            <RouterLink
              to="/mixer"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all duration-200"
              active-class="bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
            >
              <span>🎛️</span>
              <span>Audio Mixer</span>
            </RouterLink>
            <RouterLink
              to="/utilities"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all duration-200"
              active-class="bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
            >
              <span>✂️</span>
              <span>Utilities & Trim</span>
            </RouterLink>
          </div>

          <!-- Library & System -->
          <div class="space-y-1">
            <span class="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500">Organization</span>
            <RouterLink
              to="/library"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all duration-200"
              active-class="bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
            >
              <span>📁</span>
              <span>Media Library</span>
            </RouterLink>
            <RouterLink
              to="/settings"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all duration-200"
              active-class="bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
            >
              <span>⚙️</span>
              <span>Preferences</span>
            </RouterLink>
          </div>
        </nav>
      </div>

      <!-- Footer Engine Status -->
      <div class="bg-slate-950 p-3 rounded-xl border border-slate-800/80 flex items-center justify-between text-xs">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span class="text-slate-300 text-[11px]">Python Core</span>
        </div>
        <span class="text-[10px] text-slate-500 font-mono">Port 7842</span>
      </div>
    </aside>

    <!-- Main Dynamic Content -->
    <main class="flex-1 overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <RouterView />
    </main>
  </div>
</template>

<style>
@import "./style.css";
</style>