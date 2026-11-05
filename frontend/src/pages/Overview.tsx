import { useHealth } from '../api/health'
import { Card } from '../components/ui/Card'
import { ErrorState } from '../components/ui/ErrorState'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'
import { StatusDot } from '../components/ui/StatusDot'
import { NAV_ITEMS } from '../lib/navigation'

const COMPETITIONS = ['Serie A', 'Premier League', 'La Liga']

const ENVIRONMENTS: Record<string, string> = {
  development: 'sviluppo',
  test: 'test',
  production: 'produzione',
}

function SystemStatus() {
  const { data, isPending, isError, error, refetch } = useHealth()

  if (isPending) {
    return (
      <div className="space-y-3" data-testid="status-loading">
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-3/5" />
      </div>
    )
  }
  if (isError) {
    return (
      <ErrorState
        title="Backend non raggiungibile"
        message={error.message}
        onRetry={() => void refetch()}
      />
    )
  }

  const rows: [string, string, 'ok' | 'warn'][] = [
    ['API', `v${data.version} · ${ENVIRONMENTS[data.environment] ?? data.environment}`, 'ok'],
    ['Database', data.database === 'ok' ? 'Connesso' : 'Non disponibile', data.database === 'ok' ? 'ok' : 'warn'],
    ['Fornitore AI', data.ai_provider === 'mock' ? 'Simulato (offline)' : data.ai_provider, 'ok'],
  ]
  return (
    <dl className="divide-y divide-line">
      {rows.map(([label, value, status]) => (
        <div key={label} className="flex items-center justify-between py-2.5 text-sm">
          <dt className="text-ink-muted">{label}</dt>
          <dd className="flex items-center gap-2 font-medium">
            <StatusDot status={status} />
            {value}
          </dd>
        </div>
      ))}
    </dl>
  )
}

export function Overview() {
  return (
    <>
      <PageHeader
        title="Panoramica"
        description="Piattaforma professionale di analisi calcistica con cinque agenti AI specializzati."
      />
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <Card title="Stato del sistema">
          <SystemStatus />
        </Card>
        <Card title="Competizioni iniziali">
          <ul className="space-y-2 text-sm">
            {COMPETITIONS.map((c) => (
              <li key={c} className="flex items-center justify-between rounded-md bg-navy-850 px-3 py-2">
                <span className="font-medium">{c}</span>
                <span className="text-xs text-ink-faint">Dati in arrivo (Fase 2)</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Sezioni" className="md:col-span-2 xl:col-span-1">
          <ul className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2 xl:grid-cols-1">
            {NAV_ITEMS.slice(1).map(({ path, label, icon: Icon, phase }) => (
              <li key={path} className="flex items-center gap-2 text-ink-muted">
                <Icon className="size-4 text-accent" aria-hidden="true" />
                <span className="text-ink">{label}</span>
                <span className="ml-auto text-xs text-ink-faint">Fase {phase}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}
