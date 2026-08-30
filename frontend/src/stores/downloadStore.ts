import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiClient } from '../services/apiClient'

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
  const isQueueLoading = ref(false)

  function setTasks(newTasks: DownloadTask[]) {
    tasks.value = newTasks
  }

  function addTask(task: DownloadTask) {
    const existingIdx = tasks.value.findIndex(t => t.id === task.id)
    if (existingIdx >= 0) {
      tasks.value[existingIdx] = { ...tasks.value[existingIdx], ...task }
    } else {
      tasks.value.unshift(task)
    }
  }

  async function fetchQueue() {
    isQueueLoading.value = true
    try {
      const data = await apiClient.getQueueSnapshot()
      const merged: DownloadTask[] = []

      // Active
      if (Array.isArray(data.active)) {
        for (const item of data.active) {
          merged.push({
            id: item.id,
            name: item.name || 'Active Task',
            type: item.task_type || item.type || 'download',
            status: 'running',
            progress: item.progress || 0,
            progress_message: item.progress_message || 'Processing...',
            started_at: item.started_at
          })
        }
      }

      // Queued
      if (Array.isArray(data.queued)) {
        for (const item of data.queued) {
          merged.push({
            id: item.id,
            name: item.name || 'Queued Task',
            type: item.task_type || item.type || 'download',
            status: 'queued',
            progress: 0,
            progress_message: 'Waiting in queue...'
          })
        }
      }

      // Completed / History
      if (Array.isArray(data.completed)) {
        for (const item of data.completed) {
          merged.push({
            id: item.id,
            name: item.name || 'Completed Task',
            type: item.task_type || item.type || 'download',
            status: item.status || 'completed',
            progress: 100,
            progress_message: item.status === 'failed' ? (item.result?.error_message || 'Failed') : 'Completed',
            output_path: item.result?.output_path || item.output_path,
            completed_at: item.completed_at,
            result: item.result
          })
        }
      }

      tasks.value = merged
    } catch {
      // Backend not yet reachable, keep local tasks
    } finally {
      isQueueLoading.value = false
    }
  }

  function updateTaskProgress(taskId: string, progress: number, message: string) {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      task.progress = progress
      task.progress_message = message
      task.status = 'running'
    } else {
      addTask({
        id: taskId,
        name: 'Task ' + taskId.substring(0, 8),
        type: 'download',
        status: 'running',
        progress,
        progress_message: message
      })
    }
  }

  function completeTask(taskId: string, outputPath?: string, duration?: number) {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      task.status = 'completed'
      task.progress = 100
      task.output_path = outputPath
      if (!task.result) task.result = { success: true }
      task.result.output_path = outputPath
      task.result.duration_seconds = duration
      task.progress_message = outputPath ? `Saved: ${outputPath.split(/[\\/]/).pop()}` : 'Completed'
    } else {
      addTask({
        id: taskId,
        name: outputPath ? outputPath.split(/[\\/]/).pop() || taskId : taskId,
        type: 'download',
        status: 'completed',
        progress: 100,
        progress_message: 'Completed',
        output_path: outputPath,
        result: { success: true, output_path: outputPath, duration_seconds: duration }
      })
    }
  }

  function failTask(taskId: string, errorMessage: string) {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      task.status = 'failed'
      task.progress_message = errorMessage
      task.error_message = errorMessage
      if (!task.result) task.result = { success: false }
      task.result.error_message = errorMessage
    } else {
      addTask({
        id: taskId,
        name: 'Failed Task',
        type: 'download',
        status: 'failed',
        progress: 0,
        progress_message: errorMessage,
        error_message: errorMessage,
        result: { success: false, error_message: errorMessage }
      })
    }
  }

  return {
    tasks,
    isConnected,
    isQueueLoading,
    setTasks,
    addTask,
    fetchQueue,
    updateTaskProgress,
    completeTask,
    failTask,
  }
})

