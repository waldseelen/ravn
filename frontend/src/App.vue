<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="min-h-screen bg-slate-900 text-slate-100 flex">
    <!-- Sidebar Navigation -->
    <aside class="w-64 bg-slate-950 border-r border-slate-800 p-4 space-y-6">
      <div class="flex items-center gap-3 px-2">
        <span class="text-xl font-black tracking-wider text-indigo-400">RAVN</span>
        <span class="text-xs px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded font-mono border border-indigo-500/20">v2.0</span>
      </div>

      <nav class="space-y-1">
        <RouterLink
          to="/"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition"
          active-class="bg-indigo-600 text-white"
        >
          <span>⚡ Dashboard</span>
        </RouterLink>

        <RouterLink
          to="/library"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition"
          active-class="bg-indigo-600 text-white"
        >
          <span>📁 Library</span>
        </RouterLink>

        <RouterLink
          to="/settings"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition"
          active-class="bg-indigo-600 text-white"
        >
          <span>⚙️ Settings</span>
        </RouterLink>
      </nav>
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 overflow-y-auto">
      <RouterView />
    </main>
  </div>
</template>

<style>
@import "./style.css";
</style>