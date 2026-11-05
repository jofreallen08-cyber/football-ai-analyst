import { Link } from 'react-router'

import { useHealth } from '../api/health'
import { useOverview } from '../api/queries'
import { MatchRow } from '../components/domain/MatchRow'
import { SyntheticBadge } from '../components/domain/SyntheticBadge'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import { QueryState } from '../components/ui/QueryState'
import { StatTile } from '../components/ui/StatTile'
import { StatusDot } from '../components/ui/StatusDot'
import { formatNumber } from '../lib/format'

const ENVIRONMENTS: Record<string, string> = { development: 'sviluppo', test: 'test', production: 'produzione' }

function SystemStatus() {
  const health = useHealth()
  return (
    <QueryState query={health} rows={3}>
      {(data) => {
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
      }}
    </QueryState>
  )
}

export function Overview() {
  const overview = useOverview()
  return (
    <>
      <PageHeader
        title="Panoramica"
        description="Analisi calcistica con dati verificati e cinque agenti AI specializzati."
      />
      <QueryState query={overview} rows={6}>
        {(data) => (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <StatTile label="Competizioni" value={formatNumber(data.totals.competitions)} />
              <StatTile label="Partite" value={formatNumber(data.totals.matches)} hint={`${formatNumber(data.totals.finished)} giocate`} />
              <StatTile label="Squadre" value={formatNumber(data.totals.teams)} />
              <StatTile label="Giocatori" value={formatNumber(data.totals.players)} hint="Solo fonti con dati individuali" />
            </div>
            <div className="grid gap-5 lg:grid-cols-2">
              <Card title="Risultati recenti" action={<Link to="/partite" className="text-xs text-accent hover:underline">Tutte le partite</Link>}>
                {data.recent.length ? (
                  <div className="-mx-3">{data.recent.map((m) => <MatchRow key={m.id} match={m} showCompetition />)}</div>
                ) : (
                  <EmptyState title="Nessun risultato" message="Non ci sono partite terminate nei dati importati." />
                )}
              </Card>
              <Card title="Prossime partite">
                {data.upcoming.length ? (
                  <div className="-mx-3">{data.upcoming.map((m) => <MatchRow key={m.id} match={m} showCompetition />)}</div>
                ) : (
                  <EmptyState title="Nessuna partita in programma" message="Le fonti importate non contengono partite future." />
                )}
              </Card>
            </div>
            <div className="grid gap-5 lg:grid-cols-[2fr_1fr]">
              <Card title="Fonti dati">
                <ul className="divide-y divide-line text-sm">
                  {data.sources.map((s) => (
                    <li key={s.key} className="py-2.5">
                      <p className="flex items-center gap-2 font-medium">
                        {s.name} {s.is_synthetic && <SyntheticBadge />}
                      </p>
                      <p className="text-xs text-ink-muted">{s.attribution_text}</p>
                      <p className="text-xs text-ink-faint">
                        Licenza: {s.license_url ? <a className="text-accent hover:underline" href={s.license_url} target="_blank" rel="noreferrer">{s.license_name}</a> : s.license_name}
                      </p>
                    </li>
                  ))}
                </ul>
              </Card>
              <Card title="Stato del sistema">
                <SystemStatus />
              </Card>
            </div>
          </div>
        )}
      </QueryState>
    </>
  )
}
