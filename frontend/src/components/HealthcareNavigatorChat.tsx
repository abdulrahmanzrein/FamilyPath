import { useCallback, useState } from 'react'
import { Button } from '@/components/ui/button'
import { navigatorChat, type NavigatorMessage } from '@/api/client'
import { LifeBuoy, Loader2, MessageCircle, Send } from 'lucide-react'

const LANG_NAMES: Record<string, string> = {
  punjabi: 'Punjabi',
  arabic: 'Arabic',
  tagalog: 'Tagalog',
  spanish: 'Spanish',
  english: 'English',
  french: 'French',
  hindi: 'Hindi',
}

const IDEA_PROMPTS = [
  'What is OHIP and how do I apply?',
  'IFHP or refugee health coverage in Ontario',
  'UHIP for international students',
  'Family doctor vs walk in clinic. What is the difference?',
  'What is Health Care Connect?',
  'Who can I call for free health advice (811)?',
]

export function HealthcareNavigatorChat({
  preferredLanguage,
  insuranceType,
}: {
  preferredLanguage: string
  insuranceType: string
}) {
  const [messages, setMessages] = useState<NavigatorMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const langName = preferredLanguage ? LANG_NAMES[preferredLanguage] ?? preferredLanguage : ''

  const send = useCallback(async () => {
    const text = input.trim()
    if (!text || loading) return
    setError(null)
    const nextThread: NavigatorMessage[] = [...messages, { role: 'user', content: text }]
    setMessages(nextThread)
    setInput('')
    setLoading(true)
    try {
      const { reply } = await navigatorChat({
        messages: nextThread,
        language: 'english',
        insurance_type: insuranceType || undefined,
      })
      setMessages((m) => [...m, { role: 'assistant', content: reply }])
    } catch (e) {
      setMessages((m) => m.slice(0, -1))
      setInput(text)
      setError(e instanceof Error ? e.message : 'Could not reach the navigator. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [input, loading, messages, insuranceType])

  const onPickIdea = (q: string) => {
    setInput(q)
  }

  return (
    <div className="rounded-xl border border-teal-200 bg-gradient-to-b from-teal-50/80 to-white p-4 flex flex-col gap-3 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-10 h-10 rounded-xl bg-teal-100 border border-teal-200 flex items-center justify-center">
          <LifeBuoy className="w-5 h-5 text-teal-800" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold text-slate-900">Ontario healthcare questions and answers</p>
          <p className="text-[11px] text-slate-600 leading-relaxed mt-0.5">
            Ask in English about how the system works (OHIP, IFHP, UHIP, finding care). The guide always replies in
            English.
            {preferredLanguage ? (
              <>
                {' '}
                Your intake form lists preferred language as{' '}
                <span className="font-semibold text-teal-900">{langName || preferredLanguage}</span> for search only.
              </>
            ) : null}{' '}
            This is general information only, not a live search result or booking confirmation.
          </p>
        </div>
      </div>

      <div className="rounded-lg bg-white/90 border border-teal-100 px-3 py-2.5">
        <p className="text-[10px] font-semibold text-teal-900 uppercase tracking-wide mb-1.5 flex items-center gap-1">
          <MessageCircle className="w-3 h-3" />
          Example questions (tap to fill)
        </p>
        <div className="flex flex-wrap gap-1.5">
          {IDEA_PROMPTS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => onPickIdea(q)}
              className="text-left text-[10px] leading-snug px-2 py-1 rounded-md bg-teal-50 text-teal-900 border border-teal-100 hover:bg-teal-100 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      <p className="text-[10px] text-slate-500 leading-relaxed border-l-2 border-amber-200 pl-2.5">
        Not medical advice. Emergencies: <span className="font-semibold">911</span>. Non urgent:{' '}
        <span className="font-semibold">811</span> (Telehealth Ontario). Answers are educational, not confirmations
        from clinics or insurers.
      </p>

      <div
        className="max-h-52 min-h-[120px] overflow-y-auto text-[11px] space-y-2.5 bg-white rounded-lg border border-teal-100 p-3 leading-relaxed"
        aria-live="polite"
      >
        {messages.length === 0 && !loading && (
          <p className="text-slate-400">
            Ask a question below. The navigator uses your backend (OpenAI, or Claude through nexos or Anthropic).
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded-lg px-2.5 py-2 ${m.role === 'user' ? 'bg-slate-100 text-slate-900 ml-4' : 'bg-teal-50 text-teal-950 mr-4 border border-teal-100'}`}
          >
            <p className="text-[10px] font-bold uppercase tracking-wide opacity-70 mb-0.5">
              {m.role === 'user' ? 'You' : 'Guide'}
            </p>
            <p className="whitespace-pre-wrap">{m.content}</p>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-teal-800 text-[11px] py-1">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Thinking…
          </div>
        )}
      </div>

      {error && (
        <p className="text-[11px] text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-2.5 py-2">{error}</p>
      )}

      <div className="flex gap-2 items-end">
        <textarea
          className="flex-1 min-h-[72px] max-h-32 border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white placeholder:text-slate-400 focus:outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100 resize-y"
          placeholder="e.g. How do I get OHIP if I just moved to Ontario?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send()
            }
          }}
          disabled={loading}
        />
        <Button
          type="button"
          className="shrink-0 bg-teal-700 text-white hover:bg-teal-800 h-auto py-2.5 px-3"
          onClick={() => void send()}
          disabled={loading || !input.trim()}
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>
      <p className="text-[10px] text-slate-500">
        Backend needs <span className="font-mono">OPENAI_API_KEY</span> (recommended for this chat) or Claude via{' '}
        <span className="font-mono">NEXOS_API_KEY</span> / <span className="font-mono">ANTHROPIC_API_KEY</span> and{' '}
        <span className="font-mono">BYPASS_NEXOS=true</span>.
      </p>
    </div>
  )
}
