<template>
  <div
    v-if="visible"
    class="p-4 rounded-xl border space-y-3 shadow-lg transition-all"
    style="background-color: var(--error-bg); border-color: var(--status-error);"
  >
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-2 text-xs font-semibold" style="color: var(--status-error);">
        <span class="text-sm">⚠</span>
        <span>{{ message }}</span>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <button
          v-if="rawDetails"
          @click="showDetails = !showDetails"
          class="px-3 py-1.5 text-[11px] font-semibold rounded-lg border transition hover:opacity-90"
          style="background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-subtle);"
        >
          ℹ {{ showDetails ? t.hideDetails : t.technicalDetails }}
        </button>

        <button
          v-if="onRetry"
          @click="onRetry"
          class="px-3 py-1.5 text-[11px] font-semibold rounded-lg border transition hover:opacity-90"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-strong);"
        >
          ↻ {{ t.retry }}
        </button>

        <button
          @click="visible = false"
          class="px-2 py-1 text-xs hover:opacity-80 transition"
          style="color: var(--text-muted);"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- Technical Details Accordion -->
    <div
      v-if="showDetails && rawDetails"
      class="p-3 rounded-lg border font-mono text-[11px] max-h-40 overflow-y-auto whitespace-pre-wrap select-text"
      style="background-color: var(--bg-primary); border-color: var(--border-subtle); color: var(--text-secondary);"
    >
      {{ rawDetails }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  message?: string
  rawDetails?: string
  onRetry?: () => void
}>()

const t = {
  technicalDetails: 'Technical Details',
  hideDetails: 'Hide Details',
  retry: 'Retry'
}

const visible = ref(true)
const showDetails = ref(false)
</script>
