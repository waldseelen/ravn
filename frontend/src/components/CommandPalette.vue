<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/60 backdrop-blur-sm transition-opacity"
    @click.self="close"
  >
    <div
      class="w-full max-w-2xl rounded-2xl border shadow-2xl overflow-hidden flex flex-col max-h-[70vh] transition-transform"
      style="background-color: var(--bg-surface); border-color: var(--border-strong);"
    >
      <!-- Search Input Header -->
      <div class="p-4 border-b flex items-center gap-3" style="border-color: var(--border-subtle); background-color: var(--bg-card);">
        <span class="text-base" style="color: var(--accent-brass);">🔍</span>
        <input
          ref="inputRef"
          v-model="searchQuery"
          type="text"
          :placeholder="t.placeholder"
          class="flex-1 bg-transparent text-sm font-medium focus:outline-none"
          style="color: var(--text-primary);"
          @keydown.down.prevent="navigateDown"
          @keydown.up.prevent="navigateUp"
          @keydown.enter.prevent="executeSelected"
          @keydown.esc.prevent="close"
        />
        <kbd
          class="px-2 py-0.5 text-[10px] font-mono rounded border font-semibold"
          style="background-color: var(--bg-input); border-color: var(--border-subtle); color: var(--text-muted);"
        >
          ESC
        </kbd>
      </div>

      <!-- Commands Result List -->
      <div class="overflow-y-auto p-2 space-y-1 flex-1">
        <div
          v-if="filteredCommands.length === 0"
          class="p-8 text-center text-xs"
          style="color: var(--text-muted);"
        >
          {{ t.noResults }}
        </div>

        <div
          v-for="(cmd, idx) in filteredCommands"
          :key="cmd.id"
          @click="executeCommand(cmd)"
          @mouseenter="selectedIndex = idx"
          class="p-3 rounded-xl flex items-center justify-between gap-3 cursor-pointer transition"
          :style="selectedIndex === idx ? 'background-color: var(--accent-brass); color: var(--bg-primary);' : 'background-color: transparent; color: var(--text-primary);'"
        >
          <div class="flex items-center gap-3 min-w-0">
            <span class="text-base shrink-0">{{ cmd.icon }}</span>
            <div class="min-w-0">
              <div class="text-xs font-bold truncate" :style="selectedIndex === idx ? 'color: var(--bg-primary);' : 'color: var(--text-primary);'">
                {{ cmd.title }}
              </div>
              <div class="text-[11px] truncate" :style="selectedIndex === idx ? 'color: var(--bg-primary); opacity: 0.85;' : 'color: var(--text-muted);'">
                {{ cmd.subtitle }}
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <span
              class="px-2 py-0.5 text-[10px] uppercase font-bold rounded"
              :style="selectedIndex === idx ? 'background-color: var(--bg-primary); color: var(--accent-brass);' : 'background-color: var(--bg-card); color: var(--text-secondary);'"
            >
              {{ cmd.category }}
            </span>
            <kbd
              v-if="cmd.shortcut"
              class="px-1.5 py-0.5 text-[10px] font-mono rounded border"
              :style="selectedIndex === idx ? 'border-color: var(--bg-primary); color: var(--bg-primary);' : 'border-color: var(--border-subtle); color: var(--text-muted);'"
            >
              {{ cmd.shortcut }}
            </kbd>
          </div>
        </div>
      </div>

      <!-- Footer Quick Tips -->
      <div class="p-3 border-t flex items-center justify-between text-[11px]" style="border-color: var(--border-subtle); background-color: var(--bg-card); color: var(--text-muted);">
        <div class="flex items-center gap-3">
          <span><kbd class="px-1 py-0.5 rounded border text-[10px]">↑</kbd> <kbd class="px-1 py-0.5 rounded border text-[10px]">↓</kbd> {{ t.navigate }}</span>
          <span><kbd class="px-1 py-0.5 rounded border text-[10px]">↵</kbd> {{ t.select }}</span>
        </div>
        <span>{{ filteredCommands.length }} {{ t.commandsFound }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'toggleTheme'): void
  (e: 'toggleLang'): void
  (e: 'toggleQueue'): void
  (e: 'pasteUrl'): void
}>()

const router = useRouter()
const inputRef = ref<HTMLInputElement | null>(null)
const searchQuery = ref('')
const selectedIndex = ref(0)

const t = {
  placeholder: 'Type a command or search actions...',
  noResults: 'No matching commands found.',
  navigate: 'Navigate',
  select: 'Execute',
  commandsFound: 'actions available'
}

interface CommandItem {
  id: string
  title: string
  subtitle: string
  category: string
  icon: string
  shortcut?: string
  action: () => void
}

const allCommands: CommandItem[] = [
  {
    id: 'nav-home',
    title: 'Go to Home Workspace',
    subtitle: 'View recent activities, quick links & system status',
    category: 'Navigation',
    icon: '⌂',
    action: () => router.push('/')
  },
  {
    id: 'nav-download',
    title: 'Go to Download Workspace',
    subtitle: 'Download video, audio, playlists and torrents',
    category: 'Navigation',
    icon: '↓',
    action: () => router.push('/download')
  },
  {
    id: 'nav-studio',
    title: 'Go to Studio Tools',
    subtitle: 'Converter, Subtitles, Filters, Mixer, Utilities',
    category: 'Navigation',
    icon: '❖',
    action: () => router.push('/studio')
  },
  {
    id: 'nav-library',
    title: 'Go to Media Library',
    subtitle: 'Browse local files, tags, collections and history',
    category: 'Navigation',
    icon: '▦',
    action: () => router.push('/library')
  },
  {
    id: 'nav-settings',
    title: 'Open Settings',
    subtitle: 'Manage download defaults, cookies, themes and tools',
    category: 'Navigation',
    icon: '⚙',
    shortcut: 'Ctrl+,',
    action: () => router.push('/settings')
  },
  {
    id: 'action-paste',
    title: 'Paste URL & Download',
    subtitle: 'Read clipboard URL and switch to Download tab',
    category: 'Action',
    icon: '📋',
    action: () => emit('pasteUrl')
  },
  {
    id: 'action-queue',
    title: 'Toggle Task Queue Drawer',
    subtitle: 'Open or close the live background task monitor',
    category: 'Action',
    icon: '☰',
    action: () => emit('toggleQueue')
  },
  {
    id: 'action-theme',
    title: 'Toggle Theme (Dark / Light)',
    subtitle: 'Switch between Nordic Dark and Nordic Light palettes',
    category: 'Theme',
    icon: '◐',
    action: () => emit('toggleTheme')
  },
  {
    id: 'action-lang',
    title: 'Switch Language (TR / EN)',
    subtitle: 'Change interface localization',
    category: 'System',
    icon: '🌐',
    action: () => emit('toggleLang')
  }
]

const filteredCommands = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return allCommands
  return allCommands.filter(cmd =>
    cmd.title.toLowerCase().includes(q) ||
    cmd.subtitle.toLowerCase().includes(q) ||
    cmd.category.toLowerCase().includes(q)
  )
})

watch(() => props.isOpen, (open) => {
  if (open) {
    searchQuery.value = ''
    selectedIndex.value = 0
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})

function close() {
  emit('close')
}

function navigateDown() {
  if (filteredCommands.value.length === 0) return
  selectedIndex.value = (selectedIndex.value + 1) % filteredCommands.value.length
}

function navigateUp() {
  if (filteredCommands.value.length === 0) return
  selectedIndex.value = (selectedIndex.value - 1 + filteredCommands.value.length) % filteredCommands.value.length
}

function executeSelected() {
  const selected = filteredCommands.value[selectedIndex.value]
  if (selected) {
    executeCommand(selected)
  }
}

function executeCommand(cmd: CommandItem) {
  cmd.action()
  close()
}
</script>
