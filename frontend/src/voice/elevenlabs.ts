import { Conversation } from '@elevenlabs/client'

const AGENT_ID = import.meta.env.VITE_ELEVENLABS_AGENT_ID as string

export async function startVoiceSession() {
  const conversation = await Conversation.startSession({
    agentId: AGENT_ID,
  })
  return conversation
}

export async function endVoiceSession(conversation: Awaited<ReturnType<typeof startVoiceSession>>) {
  await conversation.endSession()
}
