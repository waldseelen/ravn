<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- P2-T1: Tool Health Banner (Shows if overall_status is degraded or critical) -->
    <div
      v-if="toolHealth && toolHealth.overall_status !== 'healthy'"
      class="p-4 rounded-2xl border shadow-lg space-y-3 transition-all"
      :style="{
        backgroundColor: toolHealth.overall_status === 'critical' ? 'var(--error-bg)' : 'var(--warning-bg)',
        borderColor: toolHealth.overall_status === 'critical' ? 'var(--status-error)' : 'var(--status-warning)'
      }"
    >
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 font-bold text-xs" :style="{ color: toolHealth.overall_status === 'critical' ? 'var(--status-error)' : 'var(--status-warning)' }">
          <span class="text-sm">{{ toolHealth.overall_status === 'critical' ? '✕' : '⚠' }}</span>
          <span>{{ toolHealth.overall_status === 'critical' ? t.toolHealthCritical : t.toolHealthDegraded }}</span>
        </div>
        <RouterLink
          to="/settings"
          class="px-3 py-1.5 rounded-xl border text-[11px] font-bold transition hover:opacity-90 cursor-pointer"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          ⚙ {{ t.fixInSettings }}
        </RouterLink>
      </div>

      <!-- Missing Tools and Affected Features -->
      <div class="space-y-1 text-xs" style="color: var(--text-secondary);">
        <div v-if="toolHealth.missing_required && toolHealth.missing_required.length > 0">
          <strong style="color: var(--status-error);">{{ t.missingRequired }}:</strong>
          <span class="ml-1.5 font-mono">{{ toolHealth.missing_required.join(', ') }}</span>
        </div>
        <div v-if="toolHealth.missing_optional && toolHealth.missing_optional.length > 0">
          <strong style="color: var(--status-warning);">{{ t.missingOptional }}:</strong>
          <span class="ml-1.5 font-mono">{{ toolHealth.missing_optional.join(', ') }}</span>
        </div>
        <div v-if="toolHealth.unavailable_features && toolHealth.unavailable_features.length > 0" class="text-[11px]" style="color: var(--text-muted);">
          <strong>{{ t.affectedFeatures }}:</strong>
          <span class="ml-1.5">{{ toolHealth.unavailable_features.slice(0, 5).join(', ') }}</span>
          <span v-if="toolHealth.unavailable_features.length > 5"> +{{ toolHealth.unavailable_features.length - 5 }} {{ t.more }}</span>
        </div>
      </div>
    </div>

    <!-- P2-T2: 6 Quick Action Cards Grid -->
    <div class="space-y-3">
      <h2 class="text-xs font-bold uppercase tracking-wider flex items-center gap-2" style="color: var(--text-muted);">
        <span style="color: var(--accent-brass);">❖</span>
        <span>{{ t.quickActionsTitle }}</span>
      </h2>

      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div
          v-for="action in quickActions"
          :key="action.id"
          @click="action.handler"
          class="p-4 rounded-2xl border transition space-y-2 cursor-pointer shadow-sm hover:opacity-95"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-xl border flex items-center justify-center text-lg shrink-0 font-bold"
              style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
            >
              {{ action.icon }}
            </div>
            <div class="min-w-0">
              <h3 class="text-xs font-bold truncate" style="color: var(--text-primary);">
                {{ action.title }}
              </h3>
              <p class="text-[11px] truncate leading-tight" style="color: var(--text-muted);">
                {{ action.detail }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- P2-T3: 4 Summary Overview Cards Grid -->
    <div class="space-y-3">
      <h2 class="text-xs font-bold uppercase tracking-wider flex items-center gap-2" style="color: var(--text-muted);">
        <span style="color: var(--accent-brass);">📊</span>
        <span>{{ t.overviewTitle }}</span>
      </h2>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <!-- 1. Downloads -->
        <div
          class="p-4 rounded-2xl border space-y-1 shadow-sm"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between text-xs font-semibold" style="color: var(--text-muted);">
            <span>{{ t.cardDownloads }}</span>
            <span style="color: var(--accent-brass);">↓</span>
          </div>
          <div class="text-2xl font-black" style="color: var(--text-primary);">
            {{ stats.total_downloads }}
          </div>
          <div class="text-[10px] truncate" style="color: var(--text-secondary);">
            {{ stats.successful_downloads }} {{ t.successful }}
          </div>
        </div>

        <!-- 2. Conversions -->
        <div
          class="p-4 rounded-2xl border space-y-1 shadow-sm"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between text-xs font-semibold" style="color: var(--text-muted);">
            <span>{{ t.cardConversions }}</span>
            <span style="color: var(--accent-brass);">⇄</span>
          </div>
          <div class="text-2xl font-black" style="color: var(--text-primary);">
            {{ stats.total_conversions }}
          </div>
          <div class="text-[10px] truncate" style="color: var(--text-secondary);">
            {{ t.completedTranscodes }}
          </div>
        </div>

        <!-- 3. Operations -->
        <div
          class="p-4 rounded-2xl border space-y-1 shadow-sm"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between text-xs font-semibold" style="color: var(--text-muted);">
            <span>{{ t.cardOperations }}</span>
            <span style="color: var(--accent-brass);">❖</span>
          </div>
          <div class="text-2xl font-black" style="color: var(--text-primary);">
            {{ stats.total_operations }}
          </div>
          <div class="text-[10px] truncate" style="color: var(--text-secondary);">
            {{ t.studioTasks }}
          </div>
        </div>

        <!-- 4. Active Queue Tasks -->
        <div
          class="p-4 rounded-2xl border space-y-1 shadow-sm"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
        >
          <div class="flex items-center justify-between text-xs font-semibold" style="color: var(--text-muted);">
            <span>{{ t.cardQueue }}</span>
            <span style="color: var(--accent-brass);">☰</span>
          </div>
          <div class="text-2xl font-black" style="color: var(--accent-brass);">
            {{ downloadStore.tasks.length }}
          </div>
          <div class="text-[10px] truncate" style="color: var(--text-secondary);">
            {{ activeTaskCount }} {{ t.running }}, {{ queuedTaskCount }} {{ t.queued }}
          </div>
        </div>
      </div>
    </div>

    <!-- P2-T4: Recent Activity Panel -->
    <div
      class="rounded-2xl border overflow-hidden shadow-xl"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div
        class="p-4 border-b flex items-center justify-between"
        style="background-color: var(--bg-card); border-color: var(--border-subtle);"
      >
        <div class="flex items-center gap-2">
          <span style="color: var(--accent-brass);">◷</span>
          <h2 class="text-xs font-bold uppercase tracking-wider" style="color: var(--text-primary);">
            {{ t.recentActivityTitle }}
          </h2>
        </div>
        <RouterLink
          to="/library"
          class="px-3 py-1.5 rounded-xl border text-[11px] font-semibold transition hover:opacity-90"
          style="background-color: var(--bg-surface); color: var(--text-secondary); border-color: var(--border-subtle);"
        >
          {{ t.viewAllHistory }} →
        </RouterLink>
      </div>

      <!-- Activity Items List -->
      <div class="p-4">
        <div
          v-if="recentActivities.length === 0"
          class="py-12 text-center text-xs space-y-1"
          style="color: var(--text-muted);"
        >
          <div class="text-xl">📂</div>
          <p>{{ t.noRecentActivity }}</p>
        </div>

        <div v-else class="space-y-2">
          <div
            v-for="item in recentActivities"
            :key="item.id"
            class="p-3 rounded-xl border flex items-center justify-between gap-3 text-xs transition"
            style="background-color: var(--bg-card); border-color: var(--border-subtle);"
          >
            <div class="flex items-center gap-3 min-w-0">
              <span class="text-base shrink-0">{{ getActivityIcon(item.type, item.category) }}</span>
              <div class="min-w-0">
                <div class="font-bold truncate" style="color: var(--text-primary);">
                  {{ item.title }}
                </div>
                <div class="text-[10px] font-mono truncate" style="color: var(--text-muted);">
                  {{ item.detail }}
                </div>
              </div>
            </div>

            <div class="flex items-center gap-3 shrink-0">
              <span class="text-[10px] hidden sm:inline font-mono" style="color: var(--text-muted);">
                {{ formatTimestamp(item.timestamp) }}
              </span>
              <span
                class="text-[9px] uppercase font-mono px-2 py-0.5 rounded border font-bold"
                :style="{
                  color: getStatusColor(item.status),
                  borderColor: getStatusColor(item.status),
                  backgroundColor: 'var(--bg-input)'
                }"
              >
                {{ item.status }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDownloadStore } from '../stores/downloadStore'
import { useToastStore } from '../stores/toastStore'
import { apiClient } from '../services/apiClient'

const router = useRouter()
const downloadStore = useDownloadStore()
const toastStore = useToastStore()

const t = {
  toolHealthCritical: 'External Tool Health Critical — Core media tools missing',
  toolHealthDegraded: 'External Tool Health Degraded — Optional media tools missing',
  fixInSettings: 'Fix in Settings',
  missingRequired: 'Missing Required Tools',
  missingOptional: 'Missing Optional Tools',
  affectedFeatures: 'Affected Features',
  more: 'more',
  quickActionsTitle: 'Quick Actions',
  overviewTitle: 'Overview & Statistics',
  cardDownloads: 'Downloads',
  cardConversions: 'Conversions',
  cardOperations: 'Operations',
  cardQueue: 'Task Queue',
  successful: 'successful',
  completedTranscodes: 'transcoded media',
  studioTasks: 'studio workflows',
  running: 'running',
  queued: 'queued',
  recentActivityTitle: 'Recent Activity',
  viewAllHistory: 'View Full Library',
  noRecentActivity: 'No recent activity records found.'
}

const toolHealth = ref<any>(null)
const stats = ref({
  total_downloads: 0,
  successful_downloads: 0,
  total_conversions: 0,
  total_operations: 0
})
const recentActivities = ref<any[]>([])

const activeTaskCount = computed(() => downloadStore.tasks.filter(t => t.status === 'running').length)
const queuedTaskCount = computed(() => downloadStore.tasks.filter(t => t.status === 'queued' || t.status === 'pending').length)

const quickActions = [
  {
    id: 'paste-url',
    title: 'Paste URL & Download',
    detail: 'Download single media URLs directly',
    icon: '↓',
    handler: async () => {
      try {
        const text = await navigator.clipboard.readText()
        if (text && (text.startsWith('http://') || text.startsWith('https://') || text.startsWith('magnet:'))) {
          router.push({ path: '/download', query: { url: text } })
          toastStore.success('Clipboard URL pasted into Download workspace')
        } else {
          router.push('/download')
        }
      } catch {
        router.push('/download')
      }
    }
  },
  {
    id: 'playlist',
    title: 'Playlist Downloader',
    detail: 'Acquire complete audio & video playlists',
    icon: '≡',
    handler: () => router.push({ path: '/download', query: { tab: 'playlist' } })
  },
  {
    id: 'torrent',
    title: 'Torrent / Magnet',
    detail: 'Stream or fetch torrents with aria2',
    icon: '⊕',
    handler: () => router.push({ path: '/download', query: { tab: 'torrent' } })
  },
  {
    id: 'convert',
    title: 'Convert Format',
    detail: 'Transcode containers, audio & video codecs',
    icon: '⇄',
    handler: () => router.push({ path: '/studio', query: { tab: 'converter' } })
  },
  {
    id: 'filters',
    title: 'Apply Filters & EQ',
    detail: 'Color grade, crop, rotate & balance media',
    icon: '◫',
    handler: () => router.push({ path: '/studio', query: { tab: 'filters' } })
  },
  {
    id: 'library',
    title: 'Media Library',
    detail: 'Search and manage your offline library',
    icon: '▦',
    handler: () => router.push('/library')
  }
]

function getActivityIcon(type: string, category: string): string {
  if (type === 'download') return '↓'
  if (category === 'converter') return '⇄'
  if (category === 'subtitles') return '≡'
  if (category === 'filters') return '◫'
  if (category === 'mixer') return '∿'
  if (category === 'utilities') return '✂'
  return '❖'
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

function formatTimestamp(ts: string): string {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    if (isNaN(d.getTime())) return ts.substring(0, 16)
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ts
  }
}

async function loadDashboardData() {
  try {
    const [healthRes, statsRes, recentRes] = await Promise.allSettled([
      apiClient.getHealth(),
      apiClient.getStats(),
      apiClient.getRecentActivities(6)
    ])

    if (healthRes.status === 'fulfilled' && healthRes.value?.tools) {
      toolHealth.value = healthRes.value.tools
    }

    if (statsRes.status === 'fulfilled' && statsRes.value) {
      stats.value = {
        total_downloads: statsRes.value.total_downloads || 0,
        successful_downloads: statsRes.value.successful_downloads || 0,
        total_conversions: statsRes.value.total_conversions || 0,
        total_operations: statsRes.value.total_operations || 0
      }
    }

    if (recentRes.status === 'fulfilled' && Array.isArray(recentRes.value)) {
      recentActivities.value = recentRes.value
    }
  } catch (e) {
    console.error('Failed to load dashboard data:', e)
  }
}

onMounted(() => {
  loadDashboardData()
})
</script>
