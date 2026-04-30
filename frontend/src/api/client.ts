// HTTP client for the MedBridge backend API.
// Vite proxies /api → http://localhost:8000 (see vite.config.ts).

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
