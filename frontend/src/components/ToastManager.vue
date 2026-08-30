<template>
  <div class="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
    <transition-group
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="transform translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-4"
      enter-to-class="transform translate-y-0 opacity-100 sm:translate-x-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-for="toast in toastStore.toasts"
        :key="toast.id"
        class="pointer-events-auto p-4 rounded-xl border shadow-2xl flex items-start justify-between gap-3 text-xs"
        :style="{
          backgroundColor: getBgColor(toast.type),
          borderColor: getBorderColor(toast.type),
          color: 'var(--text-primary)'
        }"
      >
        <div class="flex items-center gap-2.5">
          <span class="text-base font-bold shrink-0" :style="{ color: getIconColor(toast.type) }">
            {{ getIcon(toast.type) }}
          </span>
          <span class="font-medium leading-relaxed">{{ toast.message }}</span>
        </div>
        <button
          @click="toastStore.remove(toast.id)"
          class="shrink-0 p-1 hover:opacity-80 transition"
          style="color: var(--text-muted);"
        >
          ✕
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { useToastStore, type ToastItem } from '../stores/toastStore'

const toastStore = useToastStore()

function getIcon(type: ToastItem['type']): string {
  switch (type) {
    case 'success': return '✓'
    case 'warning': return '⚠'
    case 'error': return '✕'
    case 'info': return 'ℹ'
  }
}

function getBgColor(type: ToastItem['type']): string {
  switch (type) {
    case 'success': return 'var(--success-bg)'
    case 'warning': return 'var(--warning-bg)'
    case 'error': return 'var(--error-bg)'
    case 'info': return 'var(--info-bg)'
  }
}

function getBorderColor(type: ToastItem['type']): string {
  switch (type) {
    case 'success': return 'var(--status-success)'
    case 'warning': return 'var(--status-warning)'
    case 'error': return 'var(--status-error)'
    case 'info': return 'var(--border-strong)'
  }
}

function getIconColor(type: ToastItem['type']): string {
  switch (type) {
    case 'success': return 'var(--status-success)'
    case 'warning': return 'var(--status-warning)'
    case 'error': return 'var(--status-error)'
    case 'info': return 'var(--accent-brass)'
  }
}
</script>
