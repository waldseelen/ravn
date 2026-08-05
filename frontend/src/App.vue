<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useDownloadStore } from './stores/downloadStore'
import { connectWebSocket } from './services/apiClient'

const route = useRoute()
const downloadStore = useDownloadStore()
const isQueueDrawerOpen = ref(false)

function toggleQueueDrawer() {
  isQueueDrawerOpen.value = !isQueueDrawerOpen.value
}

onMounted(() => {
  connectWebSocket((event, data) => {
    downloadStore.isConnected = true
    if (event === 'task.progress') {
      downloadStore.updateTaskProgress(data.task_id, data.progress, data.message)
    } else if (event === 'task.complete') {
      downloadStore.completeTask(data.task_id, data.output_path, data.duration_seconds)
    } else if (event === 'task.error') {
      downloadStore.failTask(data.task_id, data.error_message)
    }
  })
})
</script>

<template>
  <div class="h-screen w-screen bg-[#141414] text-[#E8E0D8] flex overflow-hidden font-sans select-none">
    <!-- Left Sidebar Nav (Orijinal CustomTkinter Nordic Brass Layout) -->
    <aside class="w-64 bg-[#1E1E1E] border-r border-[#3A3330] flex flex-col justify-between p-4 z-20">
      <div class="space-y-6">
        <!-- Brand Logo Header -->
        <div class="flex items-center gap-3 px-2 pt-1 pb-3 border-b border-[#3A3330]">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#C99A5B] to-[#A87C42] flex items-center justify-center font-black text-[#141414] text-xl shadow-lg shadow-[#C99A5B]/20 border border-[#D8AC6E]/30">
            ❖
          </div>
          <div>
            <span class="text-base font-bold tracking-wider text-[#E8E0D8] block leading-tight">RAVN</span>
            <span class="text-[11px] text-[#C99A5B] font-semibold block">Media Pipeline</span>
          </div>
        </div>

        <!-- Workspaces Navigation -->
        <nav class="space-y-6">
          <!-- Primary Workspaces -->
          <div class="space-y-1">
            <span class="px-3 text-[10px] font-bold uppercase tracking-widest text-[#A09080]">Workspaces</span>
            
            <RouterLink
              to="/"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all duration-150"
              :class="route.path === '/' ? 'bg-[#C99A5B] text-[#141414] shadow-md shadow-[#C99A5B]/30' : 'text-[#B8A99A] hover:text-[#E8E0D8] hover:bg-[#252525]'"
            >
              <span class="text-sm">⌂</span>
              <span>Home</span>
            </RouterLink>

            <RouterLink
              to="/download"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all duration-150"
              :class="route.path === '/download' ? 'bg-[#C99A5B] text-[#141414] shadow-md shadow-[#C99A5B]/30' : 'text-[#B8A99A] hover:text-[#E8E0D8] hover:bg-[#252525]'"
            >
              <span class="text-sm">↓</span>
              <span>Download</span>
            </RouterLink>

            <RouterLink
              to="/studio"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all duration-150"
              :class="route.path.startsWith('/studio') ? 'bg-[#C99A5B] text-[#141414] shadow-md shadow-[#C99A5B]/30' : 'text-[#B8A99A] hover:text-[#E8E0D8] hover:bg-[#252525]'"
            >
              <span class="text-sm">❖</span>
              <span>Studio Tools</span>
            </RouterLink>

            <RouterLink
              to="/library"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all duration-150"
              :class="route.path === '/library' ? 'bg-[#C99A5B] text-[#141414] shadow-md shadow-[#C99A5B]/30' : 'text-[#B8A99A] hover:text-[#E8E0D8] hover:bg-[#252525]'"
            >
              <span class="text-sm">▦</span>
              <span>Media Library</span>
            </RouterLink>
          </div>

          <!-- Auxiliary Settings -->
          <div class="space-y-1">
            <span class="px-3 text-[10px] font-bold uppercase tracking-widest text-[#A09080]">System</span>
            
            <RouterLink
              to="/settings"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all duration-150"
              :class="route.path === '/settings' ? 'bg-[#C99A5B] text-[#141414] shadow-md shadow-[#C99A5B]/30' : 'text-[#B8A99A] hover:text-[#E8E0D8] hover:bg-[#252525]'"
            >
              <span class="text-sm">⚙</span>
              <span>Settings</span>
            </RouterLink>
          </div>
        </nav>
      </div>

      <!-- Footer Live Queue Drawer Button -->
      <div class="space-y-3 pt-4 border-t border-[#3A3330]">
        <button
          @click="toggleQueueDrawer"
          class="w-full flex items-center justify-between px-3 py-2.5 bg-[#252525] hover:bg-[#2A2A2A] border border-[#3A3330] rounded-lg text-xs font-medium text-[#E8E0D8] transition"
        >
          <div class="flex items-center gap-2">
            <span class="text-[#C99A5B]">☰</span>
            <span>Task Queue</span>
          </div>
          <span
            v-if="downloadStore.tasks.length > 0"
            class="px-1.5 py-0.5 text-[10px] font-mono font-bold bg-[#C99A5B] text-[#141414] rounded-full"
          >
            {{ downloadStore.tasks.length }}
          </span>
        </button>

        <div class="flex items-center justify-between text-[11px] px-1 text-[#A09080]">
          <div class="flex items-center gap-2">
            <span
              class="w-2 h-2 rounded-full"
              :class="downloadStore.isConnected ? 'bg-[#22c55e]' : 'bg-[#f59e0b]'"
            ></span>
            <span>{{ downloadStore.isConnected ? 'Engine Ready' : 'Connecting...' }}</span>
          </div>
          <span class="font-mono text-[10px]">v2.0-Tauri</span>
        </div>
      </div>
    </aside>

    <!-- Main Workspace Content Area -->
    <div class="flex-1 flex flex-col min-w-0 bg-[#141414]">
      <main class="flex-1 overflow-y-auto p-8">
        <RouterView />
      </main>

      <!-- Bottom Task Queue Drawer (Orijinal CustomTkinter Drawer) -->
      <div
        v-if="isQueueDrawerOpen"
        class="bg-[#1E1E1E] border-t border-[#3A3330] p-4 max-h-64 overflow-y-auto transition-all shadow-2xl z-30"
      >
        <div class="flex items-center justify-between pb-3 border-b border-[#3A3330] mb-3">
          <div class="flex items-center gap-2">
            <span class="text-[#C99A5B] font-bold text-sm">☰ Live Queue Drawer</span>
            <span class="text-xs text-[#A09080]">({{ downloadStore.tasks.length }} tasks)</span>
          </div>
          <button @click="toggleQueueDrawer" class="text-xs text-[#B8A99A] hover:text-[#E8E0D8]">✕ Close</button>
        </div>

        <div v-if="downloadStore.tasks.length === 0" class="text-center py-6 text-xs text-[#A09080]">
          No active tasks in queue.
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="task in downloadStore.tasks"
            :key="task.id"
            class="p-3 bg-[#252525] border border-[#3A3330] rounded-lg flex items-center justify-between text-xs"
          >
            <div class="flex-1 mr-4 truncate">
              <div class="font-medium text-[#E8E0D8] truncate">{{ task.name }}</div>
              <div class="text-[10px] text-[#A09080] truncate">{{ task.progress_message || 'Processing...' }}</div>
            </div>
            <div class="w-32 mr-4">
              <div class="w-full bg-[#141414] h-1.5 rounded-full overflow-hidden">
                <div class="bg-[#C99A5B] h-full" :style="{ width: `${task.progress || 0}%` }"></div>
              </div>
            </div>
            <span class="font-mono text-[10px] px-2 py-0.5 rounded bg-[#141414] text-[#C99A5B] border border-[#3A3330]">
              {{ task.progress }}%
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
@import "./style.css";
</style>