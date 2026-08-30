<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useDownloadStore } from './stores/downloadStore'
import { useToastStore } from './stores/toastStore'
import { connectWebSocket } from './services/apiClient'
import ToastManager from './components/ToastManager.vue'
import CommandPalette from './components/CommandPalette.vue'

const route = useRoute()
const router = useRouter()
const downloadStore = useDownloadStore()
const toastStore = useToastStore()

const isQueueDrawerOpen = ref(false)
const isPaletteOpen = ref(false)
const currentTheme = ref<'dark' | 'light'>('dark')
const currentLang = ref<'TR' | 'EN'>('TR')

const activeCount = computed(() => downloadStore.tasks.filter(t => t.status === 'running').length)
const queuedCount = computed(() => downloadStore.tasks.filter(t => t.status === 'queued' || t.status === 'pending').length)
const completedCount = computed(() => downloadStore.tasks.filter(t => t.status === 'completed').length)

function toggleQueueDrawer() {
  isQueueDrawerOpen.value = !isQueueDrawerOpen.value
}

function togglePalette() {
  isPaletteOpen.value = !isPaletteOpen.value
}

function toggleTheme() {
  currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = currentTheme.value
  localStorage.setItem('ravn_theme', currentTheme.value)
  toastStore.info(`Theme changed to ${currentTheme.value === 'dark' ? 'Nordic Dark' : 'Nordic Light'}`)
}

function toggleLang() {
  currentLang.value = currentLang.value === 'TR' ? 'EN' : 'TR'
  localStorage.setItem('ravn_lang', currentLang.value)
  toastStore.info(`Dil değiştirildi: ${currentLang.value === 'TR' ? 'Türkçe' : 'English'}`)
}

async function handlePasteUrl() {
  try {
    const text = await navigator.clipboard.readText()
    if (text && (text.startsWith('http://') || text.startsWith('https://') || text.startsWith('magnet:'))) {
      router.push({ path: '/download', query: { url: text } })
      toastStore.success('Clipboard URL pasted into Download workspace')
    } else {
      router.push('/download')
      toastStore.warning('Clipboard does not contain a valid URL')
    }
  } catch {
    router.push('/download')
  }
}

function handleGlobalKeydown(e: KeyboardEvent) {
  // Ctrl+K -> Command Palette
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    togglePalette()
    return
  }

  // Escape -> Close modal / drawer
  if (e.key === 'Escape') {
    if (isPaletteOpen.value) {
      isPaletteOpen.value = false
      return
    }
    if (isQueueDrawerOpen.value) {
      isQueueDrawerOpen.value = false
      return
    }
  }

  // Ctrl+, or Ctrl+P -> Settings
  if ((e.ctrlKey || e.metaKey) && (e.key === ',' || e.key.toLowerCase() === 'p')) {
    e.preventDefault()
    router.push('/settings')
    return
  }
}

async function clearCompletedTasks() {
  try {
    const res = await fetch('http://127.0.0.1:7842/api/v1/queue/completed', { method: 'DELETE' })
    if (res.ok) {
      downloadStore.tasks = downloadStore.tasks.filter(t => t.status !== 'completed')
      toastStore.success('Completed tasks cleared')
    }
  } catch {
    // Handling
  }
}

async function cancelTask(taskId: string) {
  try {
    await fetch(`http://127.0.0.1:7842/api/v1/queue/${taskId}/cancel`, { method: 'POST' })
    toastStore.info('Task cancellation requested')
  } catch {
    // Handling
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'running': return 'var(--status-running)'
    case 'completed': return 'var(--status-done)'
    case 'failed': return 'var(--status-error)'
    case 'cancelled': return 'var(--status-cancelled)'
    case 'paused': return 'var(--status-paused)'
    default: return 'var(--status-queued)'
  }
}

onMounted(() => {
  // Restore saved theme
  const savedTheme = localStorage.getItem('ravn_theme') as 'dark' | 'light' | null
  if (savedTheme) {
    currentTheme.value = savedTheme
    document.documentElement.dataset.theme = savedTheme
  }

  // Restore saved language
  const savedLang = localStorage.getItem('ravn_lang') as 'TR' | 'EN' | null
  if (savedLang) {
    currentLang.value = savedLang
  }

  window.addEventListener('keydown', handleGlobalKeydown)

  connectWebSocket((event, data) => {
    downloadStore.isConnected = true
    if (event === 'task.progress') {
      downloadStore.updateTaskProgress(data.task_id, data.progress, data.message)
    } else if (event === 'task.complete') {
      downloadStore.completeTask(data.task_id, data.output_path, data.duration_seconds)
      toastStore.success(`Completed: ${data.output_path ? data.output_path.split(/[\\/]/).pop() : 'Task'}`)
    } else if (event === 'task.error') {
      downloadStore.failTask(data.task_id, data.error_message)
      toastStore.error(`Task failed: ${data.error_message}`)
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<template>
  <div class="h-screen w-screen flex flex-col overflow-hidden font-sans select-none" style="background-color: var(--bg-primary); color: var(--text-primary);">
    <!-- Toast Notifications Layer -->
    <ToastManager />

    <!-- Command Palette Modal -->
    <CommandPalette
      :is-open="isPaletteOpen"
      @close="isPaletteOpen = false"
      @toggle-theme="toggleTheme"
      @toggle-lang="toggleLang"
      @toggle-queue="toggleQueueDrawer"
      @paste-url="handlePasteUrl"
    />

    <!-- Top Header & Quick Action Bar (P1-T1 & P1-T2) -->
    <header
      class="h-14 border-b flex items-center justify-between px-4 shrink-0 z-30 shadow-sm"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <!-- Brand Logo Header -->
      <div class="flex items-center gap-3">
        <div
          class="w-8 h-8 rounded-xl flex items-center justify-center font-bold text-sm shadow-md border"
          style="background-color: var(--accent-brass); color: var(--bg-primary); border-color: var(--accent-brass-light);"
        >
          ❖
        </div>
        <div>
          <span class="text-xs font-bold tracking-wider block leading-none" style="color: var(--accent-brass);">RAVN</span>
          <span class="text-[10px] block leading-none" style="color: var(--text-muted);">Media Suite</span>
        </div>
      </div>

      <!-- Quick Action Buttons (P1-T2) -->
      <div class="hidden md:flex items-center gap-2">
        <button
          @click="handlePasteUrl"
          class="px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          <span>↓</span>
          <span>Paste URL</span>
        </button>

        <button
          @click="router.push({ path: '/download', query: { tab: 'torrent' } })"
          class="px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          <span>⊕</span>
          <span>Add Torrent</span>
        </button>

        <button
          @click="router.push('/studio')"
          class="px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          <span>⇄</span>
          <span>Convert File</span>
        </button>

        <button
          @click="router.push('/library')"
          class="px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          <span>▦</span>
          <span>Open Library</span>
        </button>
      </div>

      <!-- Top Right Controls (Theme, Lang, Command Palette, Queue Drawer Toggle) -->
      <div class="flex items-center gap-2">
        <!-- Command Palette Trigger Button -->
        <button
          @click="togglePalette"
          class="px-2.5 py-1.5 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-secondary); border-color: var(--border-subtle);"
          title="Command Palette (Ctrl+K)"
        >
          <span>🔍</span>
          <kbd class="text-[10px] font-mono opacity-80">Ctrl+K</kbd>
        </button>

        <!-- Theme Toggle Button -->
        <button
          @click="toggleTheme"
          class="p-1.5 rounded-lg border text-xs transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
          :title="`Theme: ${currentTheme === 'dark' ? 'Dark' : 'Light'} (Click to switch)`"
        >
          <span>◐</span>
        </button>

        <!-- Language Toggle Button -->
        <button
          @click="toggleLang"
          class="px-2 py-1 rounded-lg border text-[11px] font-bold transition hover:opacity-90 cursor-pointer font-mono"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-subtle);"
          :title="`Language: ${currentLang}`"
        >
          {{ currentLang }}
        </button>

        <!-- Queue Drawer Toggle Button -->
        <button
          @click="toggleQueueDrawer"
          class="px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-2 transition hover:opacity-90 cursor-pointer"
          :style="isQueueDrawerOpen ? 'background-color: var(--accent-brass); color: var(--bg-primary); border-color: var(--accent-brass);' : 'background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);'"
        >
          <span>☰</span>
          <span class="hidden sm:inline">Queue</span>
          <span
            v-if="downloadStore.tasks.length > 0"
            class="px-1.5 py-0.2 text-[10px] font-mono font-bold rounded-full"
            :style="isQueueDrawerOpen ? 'background-color: var(--bg-primary); color: var(--accent-brass);' : 'background-color: var(--accent-brass); color: var(--bg-primary);'"
          >
            {{ downloadStore.tasks.length }}
          </span>
        </button>
      </div>
    </header>

    <!-- Main Workspace Frame (Sidebar + Content + 380px Right Queue Drawer) -->
    <div class="flex-1 flex overflow-hidden relative">
      <!-- Left Sidebar Nav -->
      <aside
        class="w-56 border-r flex flex-col justify-between p-4 z-20 shrink-0"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <div class="space-y-6">
          <nav class="space-y-6">
            <!-- Workspaces -->
            <div class="space-y-1">
              <span class="px-3 text-[10px] font-bold uppercase tracking-widest" style="color: var(--text-muted);">
                Workspaces
              </span>

              <RouterLink
                to="/"
                class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition"
                :style="route.path === '/' ? 'background-color: var(--accent-brass); color: var(--bg-primary);' : 'color: var(--text-secondary);'"
              >
                <span class="text-sm">⌂</span>
                <span>Home</span>
              </RouterLink>

              <RouterLink
                to="/download"
                class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition"
                :style="route.path === '/download' ? 'background-color: var(--accent-brass); color: var(--bg-primary);' : 'color: var(--text-secondary);'"
              >
                <span class="text-sm">↓</span>
                <span>Download</span>
              </RouterLink>

              <RouterLink
                to="/studio"
                class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition"
                :style="route.path.startsWith('/studio') ? 'background-color: var(--accent-brass); color: var(--bg-primary);' : 'color: var(--text-secondary);'"
              >
                <span class="text-sm">❖</span>
                <span>Studio Tools</span>
              </RouterLink>

              <RouterLink
                to="/library"
                class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition"
                :style="route.path === '/library' ? 'background-color: var(--accent-brass); color: var(--bg-primary);' : 'color: var(--text-secondary);'"
              >
                <span class="text-sm">▦</span>
                <span>Media Library</span>
              </RouterLink>
            </div>

            <!-- System -->
            <div class="space-y-1">
              <span class="px-3 text-[10px] font-bold uppercase tracking-widest" style="color: var(--text-muted);">
                System
              </span>

              <RouterLink
                to="/settings"
                class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition"
                :style="route.path === '/settings' ? 'background-color: var(--accent-brass); color: var(--bg-primary);' : 'color: var(--text-secondary);'"
              >
                <span class="text-sm">⚙</span>
                <span>Settings</span>
              </RouterLink>
            </div>
          </nav>
        </div>

        <!-- Sidebar Engine Health Footer -->
        <div class="pt-4 border-t space-y-2" style="border-color: var(--border-subtle);">
          <div class="flex items-center justify-between text-[11px]" style="color: var(--text-muted);">
            <div class="flex items-center gap-2">
              <span
                class="w-2 h-2 rounded-full"
                :style="{ backgroundColor: downloadStore.isConnected ? 'var(--status-success)' : 'var(--status-warning)' }"
              ></span>
              <span>{{ downloadStore.isConnected ? 'Core Connected' : 'Connecting...' }}</span>
            </div>
            <span class="font-mono text-[10px]">Tauri v2</span>
          </div>
        </div>
      </aside>

      <!-- Center Dynamic Router View -->
      <main class="flex-1 overflow-y-auto p-6 md:p-8" style="background-color: var(--bg-primary);">
        <RouterView />
      </main>

      <!-- Right 380px Task Queue Drawer Panel (P1-T3) -->
      <aside
        v-if="isQueueDrawerOpen"
        class="w-[380px] border-l flex flex-col justify-between shrink-0 shadow-2xl z-20 transition-all"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
      >
        <!-- Drawer Header -->
        <div class="p-4 border-b space-y-2" style="border-color: var(--border-subtle); background-color: var(--bg-card);">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="font-bold text-xs" style="color: var(--accent-brass);">☰ Task Queue</span>
            </div>
            <button
              @click="toggleQueueDrawer"
              class="text-xs hover:opacity-80 transition"
              style="color: var(--text-muted);"
            >
              ✕
            </button>
          </div>

          <!-- Drawer Stats -->
          <div class="text-[11px] flex items-center justify-between" style="color: var(--text-muted);">
            <span>Active: <strong style="color: var(--accent-brass);">{{ activeCount }}</strong></span>
            <span>Queued: <strong style="color: var(--text-secondary);">{{ queuedCount }}</strong></span>
            <span>Done: <strong style="color: var(--status-success);">{{ completedCount }}</strong></span>
            <button
              v-if="completedCount > 0"
              @click="clearCompletedTasks"
              class="text-[10px] underline hover:opacity-80"
              style="color: var(--text-secondary);"
            >
              Clear Done
            </button>
          </div>
        </div>

        <!-- Drawer Task Items List -->
        <div class="flex-1 overflow-y-auto p-3 space-y-2.5">
          <div
            v-if="downloadStore.tasks.length === 0"
            class="py-16 text-center space-y-2 text-xs"
            style="color: var(--text-muted);"
          >
            <div class="text-2xl">📂</div>
            <p class="font-semibold">Queue is empty</p>
            <p class="text-[10px]">Active jobs will appear here in real-time.</p>
          </div>

          <div
            v-for="task in downloadStore.tasks"
            :key="task.id"
            class="p-3 rounded-xl border flex flex-col gap-2 transition relative overflow-hidden"
            style="background-color: var(--bg-card); border-color: var(--border-subtle);"
          >
            <!-- Left Accent Bar -->
            <div
              class="absolute left-0 top-0 bottom-0 w-1"
              :style="{ backgroundColor: getStatusColor(task.status) }"
            ></div>

            <div class="flex items-center justify-between gap-2 pl-1.5">
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <!-- State Icon -->
                <span
                  v-if="task.status === 'running'"
                  class="animate-spin text-xs font-bold shrink-0"
                  style="color: var(--status-running);"
                >
                  ⟳
                </span>
                <span
                  v-else-if="task.status === 'completed'"
                  class="text-xs font-bold shrink-0"
                  style="color: var(--status-done);"
                >
                  ✓
                </span>
                <span
                  v-else-if="task.status === 'failed'"
                  class="text-xs font-bold shrink-0 animate-pulse"
                  style="color: var(--status-error);"
                >
                  ✕
                </span>
                <span
                  v-else
                  class="text-xs shrink-0"
                  style="color: var(--status-queued);"
                >
                  ⏳
                </span>

                <span class="text-xs font-bold truncate" style="color: var(--text-primary);">
                  {{ task.name }}
                </span>
              </div>

              <div class="flex items-center gap-1.5 shrink-0">
                <span
                  class="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded border"
                  :style="{ color: getStatusColor(task.status), borderColor: getStatusColor(task.status) }"
                >
                  {{ task.status }}
                </span>
                <button
                  v-if="task.status === 'running' || task.status === 'queued'"
                  @click="cancelTask(task.id)"
                  class="text-[10px] px-1.5 py-0.5 rounded cursor-pointer transition hover:opacity-80"
                  style="background-color: var(--error-bg); color: var(--status-error);"
                  title="Cancel Task"
                >
                  ✕
                </button>
              </div>
            </div>

            <!-- Running Progress Bar -->
            <div
              v-if="task.status === 'running'"
              class="w-full h-1 rounded-full overflow-hidden ml-1.5"
              style="background-color: var(--bg-input);"
            >
              <div
                class="h-full transition-all duration-300 rounded-full"
                :style="{ width: `${task.progress || 0}%`, backgroundColor: 'var(--accent-brass)' }"
              ></div>
            </div>

            <div class="flex items-center justify-between text-[10px] font-mono pl-1.5" style="color: var(--text-muted);">
              <span class="truncate max-w-[200px]">{{ task.progress_message || 'Processing...' }}</span>
              <span v-if="task.progress !== undefined">{{ task.progress }}%</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style>
@import "./style.css";
</style>