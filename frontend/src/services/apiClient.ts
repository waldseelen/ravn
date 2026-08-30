const API_BASE = 'http://127.0.0.1:7842/api/v1'
const WS_URL = 'ws://127.0.0.1:7842/ws/events'

export interface StartDownloadPayload {
  url: string
  output_dir: string
  format?: string
  quality?: string
  embed_metadata?: boolean
  embed_lyrics?: boolean
}

export const apiClient = {
  async getHealth() {
    const res = await fetch('http://127.0.0.1:7842/health')
    return res.json()
  },

  async extractInfo(url: string) {
    const res = await fetch(`${API_BASE}/downloads/info`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async extractPlaylistInfo(url: string) {
    const res = await fetch(`${API_BASE}/downloads/playlist/info`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async startDownload(payload: StartDownloadPayload) {
    const res = await fetch(`${API_BASE}/downloads/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async startBatchDownload(payload: { urls: string[]; output_dir: string; format?: string; quality?: string }) {
    const res = await fetch(`${API_BASE}/downloads/batch/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async startTorrentDownload(payload: { source: string; output_dir: string; mode?: string }) {
    const res = await fetch(`${API_BASE}/downloads/torrent/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getQueue() {
    const res = await fetch(`${API_BASE}/queue/`)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getHistory() {
    const res = await fetch(`${API_BASE}/history/downloads`)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getStats() {
    const res = await fetch(`${API_BASE}/history/stats`)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getRecentActivities(limit = 6) {
    const res = await fetch(`${API_BASE}/history/recent?limit=${limit}`)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getSettings() {
    const res = await fetch(`${API_BASE}/settings/`)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async patchSettings(data: Record<string, any>) {
    const res = await fetch(`${API_BASE}/settings/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data })
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  // Studio Workspace APIs
  async startConversion(payload: {
    input_file: string
    output_file?: string
    video_codec?: string
    audio_codec?: string
    video_quality?: string
    audio_bitrate?: string
    preset?: string
    hardware_accel?: string
  }) {
    const res = await fetch(`${API_BASE}/convert/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async downloadSubtitles(payload: {
    url: string
    output_dir?: string
    languages?: string[]
    auto_generated?: boolean
  }) {
    const res = await fetch(`${API_BASE}/subtitle/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async processSubtitles(payload: {
    action: string
    subtitle_file: string
    video_file?: string
    output_file?: string
    shift_seconds?: number
    output_format?: string
  }) {
    const res = await fetch(`${API_BASE}/subtitle/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async applyFilters(payload: {
    input_file: string
    output_file?: string
    brightness?: number
    contrast?: number
    saturation?: number
    blur?: number
    sharpen?: number
    rotate?: number
    flip_h?: boolean
    flip_v?: boolean
    grayscale?: boolean
    sepia?: boolean
    invert?: boolean
    deinterlace?: boolean
    denoise?: string
    lut_file?: string
  }) {
    const res = await fetch(`${API_BASE}/filters/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async runMixer(payload: {
    mode: string
    operation: string
    input_files: string[]
    output_file?: string
    options?: Record<string, any>
  }) {
    const res = await fetch(`${API_BASE}/mixer/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async runUtility(payload: {
    category: string
    operation: string
    input_file: string
    output_file?: string
    options?: Record<string, any>
  }) {
    const res = await fetch(`${API_BASE}/utilities/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  // Media Library Workspace APIs
  async searchLibrary(params?: { q?: string; tags?: string; format?: string; limit?: number; offset?: number }) {
    const url = new URL(`${API_BASE}/library/`)
    if (params?.q) url.searchParams.set('q', params.q)
    if (params?.tags) url.searchParams.set('tags', params.tags)
    if (params?.format && params.format.toLowerCase() !== 'all') url.searchParams.set('format', params.format)
    if (params?.limit) url.searchParams.set('limit', String(params.limit))
    if (params?.offset) url.searchParams.set('offset', String(params.offset))

    const res = await fetch(url.toString())
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async addMediaToLibrary(payload: { file_path: string; title?: string; tags?: string[] }) {
    const res = await fetch(`${API_BASE}/library/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async deleteMediaFromLibrary(id: number) {
    const res = await fetch(`${API_BASE}/library/${id}`, {
      method: 'DELETE'
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getLibraryStats() {
    const res = await fetch(`${API_BASE}/library/stats`)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async exportLibrary(payload: { format: string; output_file?: string }) {
    const res = await fetch(`${API_BASE}/library/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getCollections() {
    const res = await fetch(`${API_BASE}/library/collections`)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async createCollection(payload: { name: string; description?: string }) {
    const res = await fetch(`${API_BASE}/library/collections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async deleteCollection(id: number) {
    const res = await fetch(`${API_BASE}/library/collections/${id}`, {
      method: 'DELETE'
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getCollectionItems(id: number) {
    const res = await fetch(`${API_BASE}/library/collections/${id}/items`)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async addItemToCollection(collectionId: number, mediaId: number, position?: number) {
    const res = await fetch(`${API_BASE}/library/collections/${collectionId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ media_id: mediaId, position })
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getRecentLibrarySearches(limit = 10) {
    const res = await fetch(`${API_BASE}/library/recent-searches?limit=${limit}`)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async openFile(path: string) {
    const res = await fetch(`${API_BASE}/library/open-file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async openFolder(path: string) {
    const res = await fetch(`${API_BASE}/library/open-folder`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async deleteDownloadHistory(recordId: number) {
    const res = await fetch(`${API_BASE}/history/downloads/${recordId}`, {
      method: 'DELETE'
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async clearDownloadHistory() {
    const res = await fetch(`${API_BASE}/history/downloads`, {
      method: 'DELETE'
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  }
}



export function connectWebSocket(onEvent: (event: string, data: any) => void) {
  const ws = new WebSocket(WS_URL)

  ws.onopen = () => {
    console.log('Connected to RAVN WebSocket stream')
  }

  ws.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data)
      if (parsed.event) {
        onEvent(parsed.event, parsed.data)
      }
    } catch (e) {
      console.error('Failed to parse WS message:', e)
    }
  }

  ws.onerror = (err) => {
    console.error('WebSocket error:', err)
  }

  return ws
}
