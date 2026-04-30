import { Conversation } from '@elevenlabs/client'
import { useEffect, useRef, useState } from 'react'

const DEFAULT_AGENT_ID = import.meta.env.VITE_ELEVENLABS_AGENT_ID as string

type Status = 'idle' | 'connecting' | 'listening' | 'speaking' | 'error'
type Message = { role: 'user' | 'agent'; text: string }

/**
 * @param agentIdOverride - Per ElevenLabs agent (e.g. health navigator). Falls back to VITE_ELEVENLABS_AGENT_ID.
 */
export function useVoiceConversation(agentIdOverride?: string) {
  const [status, setStatus] = useState<Status>('idle')
  const [messages, setMessages] = useState<Message[]>([])
  const convRef = useRef<Awaited<ReturnType<typeof Conversation.startSession>> | null>(null)

  async function start() {
    const agentId = (agentIdOverride || DEFAULT_AGENT_ID || '').trim()
    if (!agentId) {
      setStatus('error')
      console.error('No ElevenLabs agent id. Set VITE_ELEVENLABS_AGENT_ID or pass an override.')
      return
    }
    setStatus('connecting')
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true })
      convRef.current = await Conversation.startSession({
        agentId,
        onConnect: () => setStatus('listening'),
        onDisconnect: () => setStatus('idle'),
        onError: () => setStatus('error'),
        onModeChange: ({ mode }) => setStatus(mode === 'speaking' ? 'speaking' : 'listening'),
        onMessage: ({ message, source }) =>
          setMessages((m) => [...m, { role: source === 'user' ? 'user' : 'agent', text: message }]),
      })
    } catch (e) {
      console.error(e)
      setStatus('error')
    }
  }

  async function stop() {
    await convRef.current?.endSession()
    convRef.current = null
    setStatus('idle')
  }

  useEffect(() => () => { convRef.current?.endSession() }, [])

  return { status, messages, start, stop }
}
