// Renders one card per agent source. Receives live AgentStatus events via
// the useSearchWebSocket hook and animates status transitions.
//
// Source codes and status strings match the frozen WS contract in prd.md §API.

import { CheckCircle2, Loader2, Phone, Search, XCircle, Clock } from 'lucide-react'
import type { AgentSource, AgentStatus, AgentStatusValue } from '@/hooks/useSearchWebSocket'

export type { AgentSource, AgentStatus, AgentStatusValue }

// Human-readable labels for the five fixed source codes
export const SOURCE_LABEL: Record<AgentSource, string> = {
  odhf: 'ODHF Database',
  cpso: 'CPSO Register',
  appletree: 'Appletree',
  ifhp: 'IFHP / Medavie',
  mci: 'MCI Clinics',
}

const ALL_SOURCES: AgentSource[] = ['odhf', 'cpso', 'appletree', 'ifhp', 'mci']

// Status → colour + icon
function StatusBadge({ status }: { status: AgentStatusValue }) {
  const map: Record<AgentStatusValue, { label: string; cls: string; icon: React.ReactNode }> = {
    pending: {
      label: 'Pending',
      cls: 'bg-slate-100 text-slate-500 border-slate-200',
      icon: <Clock className="w-3 h-3" />,
    },
    searching: {
      label: 'Searching…',
      cls: 'bg-blue-50 text-blue-700 border-blue-200',
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
    },
    found: {
      label: 'Match found',
      cls: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      icon: <Search className="w-3 h-3" />,
    },
    calling: {
      label: 'Calling…',
      cls: 'bg-amber-50 text-amber-700 border-amber-200',
      icon: <Phone className="w-3 h-3 animate-pulse" />,
    },
    confirmed: {
      label: 'Confirmed',
      cls: 'bg-emerald-100 text-emerald-800 border-emerald-300',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    failed: {
      label: 'No match',
      cls: 'bg-rose-50 text-rose-600 border-rose-200',
      icon: <XCircle className="w-3 h-3" />,
    },
  }
  const { label, cls, icon } = map[status]
  return (
    <span className={`inline-flex items-center gap-1 border text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${cls}`}>
      {icon}
      {label}
    </span>
  )
}

// Card border highlight by status
function cardBorder(status: AgentStatusValue): string {
  if (status === 'confirmed') return 'border-emerald-300 shadow-emerald-100'
  if (status === 'calling') return 'border-amber-300 shadow-amber-100'
  if (status === 'failed') return 'border-rose-200'
  if (status === 'searching' || status === 'found') return 'border-blue-200'
  return 'border-slate-200'
}

interface Props {
  agentMap: Partial<Record<AgentSource, AgentStatus>>
}

export function AgentGrid({ agentMap }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {ALL_SOURCES.map((src) => {
        const agent = agentMap[src]
        const status: AgentStatusValue = agent?.status ?? 'pending'
        return (
          <div
            key={src}
            className={`bg-white rounded-xl p-4 border shadow-sm transition-all duration-300 ${cardBorder(status)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-slate-900">{SOURCE_LABEL[src]}</span>
              <StatusBadge status={status} />
            </div>
            {agent?.clinic_name && (
              <p className="text-xs font-medium text-slate-700 mb-1">{agent.clinic_name}</p>
            )}
            {agent?.message && (
              <p className="text-xs text-slate-500 leading-relaxed">{agent.message}</p>
            )}
            {!agent && (
              <p className="text-xs text-slate-400">Waiting to start…</p>
            )}
          </div>
        )
      })}
    </div>
  )
}
