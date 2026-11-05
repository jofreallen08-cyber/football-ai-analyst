import { useHealth } from '../../api/health'
import { type Status, StatusDot } from '../ui/StatusDot'

export function HealthIndicator() {
  const { data, isPending, isError } = useHealth()

  let status: Status = 'loading'
  let label = 'Verifica connessione…'
  if (isError) {
    status = 'error'
    label = 'Server non raggiungibile'
  } else if (data) {
    status = data.status === 'ok' ? 'ok' : 'warn'
    label = data.status === 'ok' ? 'Sistema operativo' : 'Database non disponibile'
  } else if (!isPending) {
    status = 'warn'
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-2 rounded-full border border-line bg-navy-850 px-3 py-1 text-xs text-ink-muted"
    >
      <StatusDot status={status} />
      <span>{label}</span>
    </div>
  )
}
