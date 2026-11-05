import { AlertCircle, CheckCircle2, Clock, Database, Loader2, MinusCircle } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const STATUS: Record<string, { label: string; className: string; icon: LucideIcon; spin?: boolean }> = {
  pending: { label: 'In attesa', className: 'border-line text-ink-muted', icon: Clock },
  queued: { label: 'In coda', className: 'border-line text-ink-muted', icon: Clock },
  running: { label: 'In corso', className: 'border-accent/50 text-accent', icon: Loader2, spin: true },
  completed: { label: 'Completato', className: 'border-pitch/50 text-pitch', icon: CheckCircle2 },
  cached: { label: 'Da cache', className: 'border-pitch/50 text-pitch', icon: Database },
  skipped: { label: 'Saltato: dati insufficienti', className: 'border-warn/50 text-warn', icon: MinusCircle },
  partial: { label: 'Parziale', className: 'border-warn/50 text-warn', icon: AlertCircle },
  failed: { label: 'Non riuscito', className: 'border-danger/50 text-danger', icon: AlertCircle },
}

/** Status pill: icon + label, never colour alone. */
export function AgentStatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? STATUS.pending!
  const Icon = s.icon
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${s.className}`}>
      <Icon className={`size-3 ${s.spin ? 'animate-spin' : ''}`} aria-hidden="true" />
      {s.label}
    </span>
  )
}

const CONF: Record<string, [string, string]> = {
  low: ['Confidenza bassa', 'border-warn/50 text-warn'],
  medium: ['Confidenza media', 'border-accent/50 text-accent'],
  high: ['Confidenza alta', 'border-pitch/50 text-pitch'],
}

export function ConfidenceBadge({ value }: { value: string | null | undefined }) {
  if (!value) return null
  const [label, cls] = CONF[value] ?? [value, 'border-line text-ink-muted']
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${cls}`}>{label}</span>
}
