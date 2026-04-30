// Connects to /ws/searches/{searchId} and streams AgentStatus events.
// Vite proxies /ws → ws://localhost:8000 (see vite.config.ts).
//
// Returns the live list of agent statuses. The hook reconnects automatically
// if the socket closes unexpectedly (e.g. backend restart during demo).

import { useCallback, useEffect, useRef, useState } from 'react'

export type AgentSource = 'odhf' | 'cpso' | 'appletree' | 'mci' | 'ifhp'
export type AgentStatusValue = 'pending' | 'searching' | 'found' | 'calling' | 'confirmed' | 'failed'

export interface AgentStatus {
  source: AgentSource
  status: AgentStatusValue
  clinic_name: string | null
  message: string | null
  updated_at: string
}

export function useSearchWebSocket(searchId: string | null) {
  const [agents, setAgents] = useState<AgentStatus[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (!searchId) return

    // /ws proxied through Vite to ws://localhost:8000
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/searches/${searchId}`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (ev: MessageEvent) => {
      try {
        const event = JSON.parse(ev.data as string) as AgentStatus
        setAgents((prev) => {
          const idx = prev.findIndex((a) => a.source === event.source)
          if (idx === -1) return [...prev, event]
          const next = [...prev]
          next[idx] = event
          return next
        })
      } catch {
        // malformed event, ignore
      }
    }

    ws.onclose = () => {
      setConnected(false)
      // auto-reconnect after 2 s to survive backend restarts during demo
      reconnectTimer.current = setTimeout(connect, 2000)
    }

    ws.onerror = () => ws.close()
  }, [searchId])

  useEffect(() => {
    setAgents([])
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { agents, connected }
}
