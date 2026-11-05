import { useStandings, useTeamAnalytics, useTeams } from '../api/queries'
import type { SplitSummary } from '../api/types'
import { PercentileBar } from '../components/charts/PercentileBar'
import { XgTrendChart } from '../components/charts/XgTrendChart'
import { FormStrip } from '../components/domain/ResultBadge'
import { SeasonSelect } from '../components/domain/SeasonSelect'
import { StandingsTable } from '../components/domain/StandingsTable'
import { SyntheticBadge } from '../components/domain/SyntheticBadge'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import { QueryState } from '../components/ui/QueryState'
import { Select } from '../components/ui/Select'
import { StatTile } from '../components/ui/StatTile'
import { capitalize, formatNumber } from '../lib/format'
import { useNumberParam, useSeasonSelection } from '../lib/useSeasonSelection'

function SplitRow({ label, s }: { label: string; s: SplitSummary }) {
  return (
    <tr className="border-b border-line/50">
      <th scope="row" className="py-2 text-left font-medium">{label}</th>
      <td className="text-center">{s.played}</td>
      <td className="text-center">{s.wins}-{s.draws}-{s.losses}</td>
      <td className="text-center">{formatNumber(s.ppg)}</td>
      <td className="text-center">{formatNumber(s.goals_for_pg)} / {formatNumber(s.goals_against_pg)}</td>
      <td className="text-center" title={s.xg_coverage < s.played ? `xG disponibili per ${s.xg_coverage} partite su ${s.played}` : undefined}>
        {s.xg_pg !== null ? `${formatNumber(s.xg_pg)} / ${formatNumber(s.xga_pg)}` : '—'}
      </td>
    </tr>
  )
}

export function TeamAnalytics() {
  const { competitions, competition, season, setSeason } = useSeasonSelection()
  const teams = useTeams(season?.id)
  const standings = useStandings(season?.id)
  const [paramTeam, setTeam] = useNumberParam('squadra')
  const teamId = paramTeam ?? standings.data?.rows[0]?.team_id
  const analytics = useTeamAnalytics(teamId, season?.id)

  return (
    <>
      <PageHeader title="Analisi Squadre" description="Forma, rendimento in casa e in trasferta, xG e statistiche rispetto alla media del campionato." />
      <Card className="mb-5">
        <QueryState query={competitions} rows={1}>
          {(list) => (
            <div className="grid gap-3 sm:grid-cols-2">
              <SeasonSelect competitions={list} seasonId={season?.id} onChange={setSeason} />
              <Select label="Squadra" value={String(teamId ?? '')} onChange={(v) => setTeam(Number(v))}>
                {teams.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </Select>
            </div>
          )}
        </QueryState>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1fr_22rem]">
        <div className="min-w-0 space-y-5">
          <QueryState query={analytics} rows={8}>
            {(a) => (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-xl font-bold">{a.team.name}</h2>
                  {a.season.is_synthetic && <SyntheticBadge />}
                </div>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <StatTile label="Posizione" value={a.position ? `${a.position}°` : '—'} />
                  <StatTile label="Punti a partita" value={formatNumber(a.splits.all?.ppg)} hint={`${a.splits.all?.played ?? 0} partite`} />
                  <StatTile label="Gol fatti / subiti a partita" value={`${formatNumber(a.splits.all?.goals_for_pg, 1)} / ${formatNumber(a.splits.all?.goals_against_pg, 1)}`} />
                  <StatTile label="xG creati / concessi a partita" value={a.has_xg ? `${formatNumber(a.splits.all?.xg_pg, 1)} / ${formatNumber(a.splits.all?.xga_pg, 1)}` : '—'} hint={a.has_xg ? undefined : 'Non disponibile dalla fonte'} />
                </div>
                <Card title="Forma (ultime 10, dalla più vecchia)">
                  <FormStrip results={a.form_last10.matches.map((m) => m.result).reverse()} />
                  <p className="mt-2 text-sm text-ink-muted">
                    Ultime 5: {a.form_last5.points} punti, {a.form_last5.goals_for} gol fatti e {a.form_last5.goals_against} subiti.
                  </p>
                </Card>
                <Card title="Casa e trasferta">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm tabular-nums">
                      <thead className="text-xs text-ink-faint">
                        <tr className="border-b border-line">
                          <th className="py-2 text-left font-medium" />
                          <th className="font-medium">G</th>
                          <th className="font-medium">V-N-P</th>
                          <th className="font-medium">Punti/partita</th>
                          <th className="font-medium">Gol fatti/subiti</th>
                          <th className="font-medium">xG creati/concessi</th>
                        </tr>
                      </thead>
                      <tbody>
                        {a.splits.home && <SplitRow label="Casa" s={a.splits.home} />}
                        {a.splits.away && <SplitRow label="Trasferta" s={a.splits.away} />}
                      </tbody>
                    </table>
                  </div>
                </Card>
                <Card title="xG per partita">
                  {a.has_xg ? <XgTrendChart points={a.xg_series} teams={a.teams} /> : <EmptyState title="xG non disponibile" message="La fonte di questa competizione non fornisce gli expected goals. Nessun valore viene stimato." />}
                </Card>
                <Card title="Statistiche rispetto al campionato">
                  <table className="w-full text-sm tabular-nums">
                    <thead className="text-xs text-ink-faint">
                      <tr className="border-b border-line">
                        <th className="py-2 text-left font-medium">Metrica (a partita)</th>
                        <th className="text-right font-medium">Squadra</th>
                        <th className="text-right font-medium">Media</th>
                        <th className="pl-4 text-left font-medium">Percentile</th>
                      </tr>
                    </thead>
                    <tbody>
                      {a.stats.metrics.filter((x) => x.per_match !== null).map((x) => (
                        <tr key={x.key} className="border-b border-line/50">
                          <td className="py-2">{capitalize(x.label)}{x.lower_is_better && <span className="text-ink-faint"> (meno è meglio)</span>}</td>
                          <td className="text-right">{formatNumber(x.per_match)}</td>
                          <td className="text-right text-ink-muted">{formatNumber(x.league_avg)}</td>
                          <td className="pl-4"><PercentileBar percentile={x.percentile} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {a.missing.length > 0 && <p className="mt-3 text-xs text-ink-faint">Non disponibili dalla fonte: {a.missing.map((m) => m.split(':')[0]).join(', ')}.</p>}
                </Card>
              </>
            )}
          </QueryState>
        </div>
        <Card title={`Classifica ${competition?.name ?? ''}`}>
          <QueryState query={standings} rows={10}>
            {(s) => <StandingsTable data={s} highlight={teamId} onSelect={(id) => setTeam(id)} />}
          </QueryState>
        </Card>
      </div>
    </>
  )
}
