import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { usePlayerAnalytics, usePlayerLeaders, useTeams } from '../api/queries'
import { AXIS, SERIES } from '../components/charts/chartTheme'
import { TooltipBox } from '../components/charts/ChartTooltip'
import { SeasonSelect } from '../components/domain/SeasonSelect'
import { SyntheticBadge } from '../components/domain/SyntheticBadge'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import { QueryState } from '../components/ui/QueryState'
import { Select } from '../components/ui/Select'
import { StatTile } from '../components/ui/StatTile'
import { formatNumber, formatShortDate, POSITION_LABEL } from '../lib/format'
import { useNumberParam, useSeasonSelection } from '../lib/useSeasonSelection'
import { useSearchParams } from 'react-router'

const METRICS: [string, string][] = [
  ['goals', 'Gol'],
  ['assists', 'Assist'],
  ['xg', 'xG'],
  ['xa', 'xA'],
  ['shots', 'Tiri'],
  ['shots_on_target', 'Tiri in porta'],
  ['key_passes', 'Passaggi chiave'],
  ['tackles', 'Contrasti'],
  ['interceptions', 'Intercetti'],
]

function PlayerPanel({ playerId, seasonId, name }: { playerId: number; seasonId: number; name: string }) {
  const q = usePlayerAnalytics(playerId, seasonId)
  return (
    <Card title={name}>
      <QueryState query={q} rows={6}>
        {(p) =>
          p.aggregate ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                <StatTile label="Presenze (da titolare)" value={`${p.aggregate.appearances} (${p.aggregate.starts})`} />
                <StatTile label="Minuti" value={formatNumber(p.aggregate.minutes)} />
                <StatTile label="Gol / Assist" value={`${formatNumber(p.aggregate.totals.goals)} / ${formatNumber(p.aggregate.totals.assists)}`} />
                <StatTile label="xG / xA" value={`${formatNumber(p.aggregate.totals.xg, 1)} / ${formatNumber(p.aggregate.totals.xa, 1)}`} />
              </div>
              {!p.aggregate.per90_reliable && <p className="text-xs text-warn">Meno di 270 minuti: valori per 90' non calcolati.</p>}
              <div className="h-48" role="img" aria-label="xG per partita del giocatore">
                <ResponsiveContainer>
                  <BarChart data={p.match_log.map((x) => ({ ...x, label: formatShortDate(x.kickoff_at) }))} margin={{ top: 4, right: 4, bottom: 0, left: -24 }}>
                    <CartesianGrid stroke={AXIS.stroke} strokeDasharray="2 4" vertical={false} />
                    <XAxis dataKey="label" tick={AXIS.tick} stroke={AXIS.stroke} tickLine={false} interval="preserveStartEnd" />
                    <YAxis tick={AXIS.tick} stroke={AXIS.stroke} tickLine={false} />
                    <Tooltip
                      cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                      content={({ active, payload }) => {
                        const d = active ? payload?.[0]?.payload : undefined
                        return d ? (
                          <TooltipBox title={d.label} rows={[
                            { label: 'xG', value: formatNumber(d.xg), color: SERIES.one },
                            { label: 'Gol', value: formatNumber(d.goals) },
                            { label: 'Minuti', value: formatNumber(d.minutes) },
                          ]} />
                        ) : null
                      }}
                    />
                    <Bar dataKey="xg" name="xG" fill={SERIES.one} radius={[4, 4, 0, 0]} maxBarSize={18} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="text-xs text-ink-faint">xG per partita · {p.match_log.length} partite con statistiche</p>
            </div>
          ) : (
            <EmptyState title="Nessuna statistica" message={p.missing.join(' ')} />
          )
        }
      </QueryState>
    </Card>
  )
}

export function PlayerAnalytics() {
  const { competitions, competition, season, setSeason } = useSeasonSelection()
  const teams = useTeams(season?.id)
  const [teamId, setTeamId] = useNumberParam('squadra')
  const [playerId, setPlayerId] = useNumberParam('giocatore')
  const [params, setParams] = useSearchParams()
  const metric = params.get('metrica') ?? 'goals'
  const per90 = params.get('per90') === '1'
  const leaders = usePlayerLeaders(season?.id, { metric, per90, team_id: teamId, limit: 20 })
  const setParam = (k: string, v: string | null) =>
    setParams((prev) => {
      const next = new URLSearchParams(prev)
      if (v === null) next.delete(k)
      else next.set(k, v)
      return next
    }, { replace: true })
  const metricLabel = METRICS.find(([k]) => k === metric)?.[1] ?? metric

  return (
    <>
      <PageHeader title="Analisi Giocatori" description="Classifiche individuali e valori per 90 minuti (minimo 270 minuti giocati)." />
      <Card className="mb-5">
        <QueryState query={competitions} rows={1}>
          {(list) => (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr]">
              <SeasonSelect competitions={list} seasonId={season?.id} onChange={setSeason} />
              <Select label="Squadra" value={String(teamId ?? '')} onChange={(v) => setTeamId(v ? Number(v) : undefined)}>
                <option value="">Tutte</option>
                {teams.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </Select>
              <Select label="Metrica" value={metric} onChange={(v) => setParam('metrica', v)}>
                {METRICS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
              </Select>
              <Select label="Valori" value={per90 ? '1' : '0'} onChange={(v) => setParam('per90', v === '1' ? '1' : null)}>
                <option value="0">Totali</option>
                <option value="1">Per 90 minuti</option>
              </Select>
            </div>
          )}
        </QueryState>
      </Card>
      <div className="grid gap-5 xl:grid-cols-[1fr_24rem]">
        <Card title={`${metricLabel}${per90 ? " per 90'" : ''} — ${competition?.name ?? ''} ${season?.label ?? ''}`} action={competition?.is_synthetic ? <SyntheticBadge /> : undefined}>
          <QueryState query={leaders} rows={10}>
            {(d) =>
              d.items.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm tabular-nums">
                    <thead className="text-xs text-ink-faint">
                      <tr className="border-b border-line">
                        <th className="py-2 text-left font-medium">#</th>
                        <th className="text-left font-medium">Giocatore</th>
                        <th className="hidden text-left font-medium sm:table-cell">Squadra</th>
                        <th className="text-right font-medium">Minuti</th>
                        <th className="text-right font-medium">{metricLabel}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.items.map((i, idx) => (
                        <tr key={i.player_id} className={`border-b border-line/50 ${i.player_id === playerId ? 'bg-navy-700/60' : ''}`}>
                          <td className="py-2 text-ink-faint">{idx + 1}</td>
                          <td>
                            <button type="button" onClick={() => setPlayerId(i.player_id)} className="text-left hover:text-accent">
                              {i.player_name}
                              <span className="block text-xs text-ink-faint">{i.position ? POSITION_LABEL[i.position] : ''}</span>
                            </button>
                          </td>
                          <td className="hidden text-ink-muted sm:table-cell">{i.team.short_name ?? i.team.name}</td>
                          <td className="text-right text-ink-muted">{formatNumber(i.aggregate.minutes)}</td>
                          <td className="text-right font-semibold">{formatNumber(per90 ? i.aggregate.per90[metric] : i.aggregate.totals[metric])}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="Statistiche individuali non disponibili" message="La fonte di questa competizione non fornisce dati sui singoli giocatori. Prova la Lega Dimostrativa per vedere la funzione." />
              )
            }
          </QueryState>
        </Card>
        {playerId && season ? (
          <PlayerPanel playerId={playerId} seasonId={season.id} name={leaders.data?.items.find((i) => i.player_id === playerId)?.player_name ?? 'Giocatore'} />
        ) : (
          <Card title="Dettaglio giocatore">
            <EmptyState title="Seleziona un giocatore" message="Clicca un nome nella tabella per vedere il dettaglio." />
          </Card>
        )}
      </div>
    </>
  )
}
