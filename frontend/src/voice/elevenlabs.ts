import { Conversation } from '@elevenlabs/client'
import { useEffect, useRef, useState } from 'react'

const AGENT_ID = import.meta.env.VITE_ELEVENLABS_AGENT_ID as string

type Status = 'idle' | 'connecting' | 'listening' | 'speaking' | 'error'
type Message = { role: 'user' | 'agent'; text: string }

export function useVoiceConversation() {
  const [status, setStatus] = useState<Status>('idle')
  const [messages, setMessages] = useState<Message[]>([])
  const convRef = useRef<Awaited<ReturnType<typeof Conversation.startSession>> | null>(null)

  async function start() {
    if (!AGENT_ID) {
      setStatus('error')
      console.error('VITE_ELEVENLABS_AGENT_ID is not set')
      return
    }
    setStatus('connecting')
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true })
      convRef.current = await Conversation.startSession({
        agentId: AGENT_ID,
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
