// HTTP client for the MedBridge backend API.
// Vite proxies /api → http://localhost:8000 (see vite.config.ts).

export interface NavigatorMessage {
  role: 'user' | 'assistant'
  content: string
}

export async function navigatorChat(body: {
  messages: NavigatorMessage[]
  language?: string
  insurance_type?: string
}): Promise<{ reply: string }> {
  const res = await fetch('/api/navigator/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: body.messages,
      ...(body.language ? { language: body.language } : {}),
      ...(body.insurance_type ? { insurance_type: body.insurance_type } : {}),
    }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Navigator unavailable: ${res.status} ${text}`)
  }
  return res.json() as Promise<{ reply: string }>
}

export interface SearchStartRequest {
  name: string
  phone: string
  postal_code: string
  language: string
  insurance_type: 'ohip' | 'ifhp' | 'uhip' | 'waiting_period'
}

export interface SearchStartResponse {
  search_id: string
}

export async function startSearch(body: SearchStartRequest): Promise<SearchStartResponse> {
  const res = await fetch('/api/searches/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`startSearch failed: ${res.status} ${text}`)
  }
  return res.json() as Promise<SearchStartResponse>
}
