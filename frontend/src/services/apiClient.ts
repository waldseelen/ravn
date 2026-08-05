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

  async startDownload(payload: StartDownloadPayload) {
    const res = await fetch(`${API_BASE}/downloads/start`, {
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
