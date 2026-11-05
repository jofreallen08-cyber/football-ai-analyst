import { useMatches, useTeams } from '../api/queries'
import { MatchRow } from '../components/domain/MatchRow'
import { SeasonSelect } from '../components/domain/SeasonSelect'
import { SyntheticBadge } from '../components/domain/SyntheticBadge'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import { QueryState } from '../components/ui/QueryState'
import { Select } from '../components/ui/Select'
import { useNumberParam, useSeasonSelection } from '../lib/useSeasonSelection'
import { useSearchParams } from 'react-router'

const PAGE = 20

export function MatchCenter() {
  const { competitions, competition, season, setSeason } = useSeasonSelection()
  const [teamId, setTeamId] = useNumberParam('squadra')
  const [page, setPage] = useNumberParam('pagina')
  const [params, setParams] = useSearchParams()
  const status = params.get('stato') ?? ''
  const teams = useTeams(season?.id)
  const offset = ((page ?? 1) - 1) * PAGE
  const matches = useMatches(
    { season_id: season?.id, team_id: teamId, status: status || undefined, limit: PAGE, offset },
    season !== undefined,
  )

  const setStatus = (v: string) =>
    setParams((prev) => {
      const next = new URLSearchParams(prev)
      if (v) next.set('stato', v)
      else next.delete('stato')
      next.delete('pagina')
      return next
    }, { replace: true })

  return (
    <>
      <PageHeader title="Centro Partite" description="Calendario e risultati, con dettaglio statistico dove la fonte lo fornisce." />
      <Card className="mb-5">
        <QueryState query={competitions} rows={1}>
          {(list) => (
            <div className="grid gap-3 sm:grid-cols-3">
              <SeasonSelect competitions={list} seasonId={season?.id} onChange={setSeason} />
              <Select label="Squadra" value={String(teamId ?? '')} onChange={(v) => { setTeamId(v ? Number(v) : undefined); setPage(undefined) }}>
                <option value="">Tutte le squadre</option>
                {teams.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </Select>
              <Select label="Stato" value={status} onChange={setStatus}>
                <option value="">Tutte</option>
                <option value="finished">Terminate</option>
                <option value="scheduled">In programma</option>
              </Select>
            </div>
          )}
        </QueryState>
      </Card>

      <Card title={competition ? `${competition.name} ${season?.label ?? ''}` : 'Partite'} action={competition?.is_synthetic ? <SyntheticBadge /> : undefined}>
        <QueryState query={matches} rows={8}>
          {(data) => {
            if (data.items.length === 0) return <EmptyState title="Nessuna partita" message="Nessuna partita corrisponde ai filtri selezionati." />
            const groups = new Map<string, typeof data.items>()
            for (const m of data.items) {
              const key = m.matchday ? `Giornata ${m.matchday}` : 'Altre partite'
              groups.set(key, [...(groups.get(key) ?? []), m])
            }
            const pages = Math.max(1, Math.ceil(data.total / PAGE))
            const current = page ?? 1
            return (
              <>
                <div className="space-y-4">
                  {[...groups].map(([label, items]) => (
                    <section key={label}>
                      <h3 className="mb-1 text-xs font-semibold tracking-wide text-ink-faint uppercase">{label}</h3>
                      <div className="-mx-3 divide-y divide-line/50">{items.map((m) => <MatchRow key={m.id} match={m} />)}</div>
                    </section>
                  ))}
                </div>
                <nav aria-label="Paginazione" className="mt-4 flex items-center justify-between text-sm text-ink-muted">
                  <span>{data.total} partite · pagina {current} di {pages}</span>
                  <span className="flex gap-2">
                    <button type="button" disabled={current <= 1} onClick={() => setPage(current - 1)} className="rounded-md border border-line px-3 py-1 hover:bg-navy-800 disabled:opacity-40">Precedente</button>
                    <button type="button" disabled={current >= pages} onClick={() => setPage(current + 1)} className="rounded-md border border-line px-3 py-1 hover:bg-navy-800 disabled:opacity-40">Successiva</button>
                  </span>
                </nav>
              </>
            )
          }}
        </QueryState>
      </Card>
    </>
  )
}
