import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToastItem {
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  message: string
  duration?: number
}

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<ToastItem[]>([])

  function show(type: ToastItem['type'], message: string, duration = 3500) {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    toasts.value.push({ id, type, message, duration })

    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }
  }

  function remove(id: string) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  function success(message: string, duration = 3000) {
    show('success', message, duration)
  }

  function error(message: string, duration = 5000) {
    show('error', message, duration)
  }

  function warning(message: string, duration = 4000) {
    show('warning', message, duration)
  }

  function info(message: string, duration = 3000) {
    show('info', message, duration)
  }

  return { toasts, show, remove, success, error, warning, info }
})
