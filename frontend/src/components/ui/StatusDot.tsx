export type Status = 'ok' | 'warn' | 'error' | 'loading'

const COLORS: Record<Status, string> = {
  ok: 'bg-pitch',
  warn: 'bg-warn',
  error: 'bg-danger',
  loading: 'bg-ink-faint animate-pulse',
}

export function StatusDot({ status }: { status: Status }) {
  return <span aria-hidden="true" className={`inline-block size-2.5 rounded-full ${COLORS[status]}`} />
}
