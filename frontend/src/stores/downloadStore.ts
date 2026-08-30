import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface DownloadTask {
  id: string
  type: string
  name: string
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused'
  progress: number
  progress_message: string
  started_at?: string
  completed_at?: string
  output_path?: string
  error_message?: string
  result?: {
    success: boolean
    output_path?: string
    error_message?: string
    duration_seconds?: number
  }
}

export const useDownloadStore = defineStore('download', () => {
  const tasks = ref<DownloadTask[]>([])
  const isConnected = ref(false)

  function setTasks(newTasks: DownloadTask[]) {
    tasks.value = newTasks
  }

  function updateTaskProgress(taskId: string, progress: number, message: string) {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      task.progress = progress
      task.progress_message = message
      task.status = 'running'
    }
  }

  function completeTask(taskId: string, outputPath?: string, duration?: number) {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      task.status = 'completed'
      task.progress = 100
      if (!task.result) task.result = { success: true }
      task.result.output_path = outputPath
      task.result.duration_seconds = duration
    }
  }

  function failTask(taskId: string, errorMessage: string) {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      task.status = 'failed'
      if (!task.result) task.result = { success: false }
      task.result.error_message = errorMessage
    }
  }

  return {
    tasks,
    isConnected,
    setTasks,
    updateTaskProgress,
    completeTask,
    failTask,
  }
})
