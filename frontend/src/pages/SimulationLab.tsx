import { FlaskConical, History, Play, RotateCcw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'

import { ApiError } from '../api/client'
import { useMatch, useRunSimulation, useSimulation, useSimulationHistory, useSimulationOptions, useTeams } from '../api/queries'
import type { PlayerOption, Simulation } from '../api/types'
import { GoalsDistributionChart } from '../components/charts/GoalsDistributionChart'
import { OutcomeBar, OutcomeLegend } from '../components/charts/OutcomeBar'
import { SeasonSelect } from '../components/domain/SeasonSelect'
import { SyntheticBadge } from '../components/domain/SyntheticBadge'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { LoadingBlock } from '../components/ui/LoadingCard'
import { PageHeader } from '../components/ui/PageHeader'
import { QueryState } from '../components/ui/QueryState'
import { Select } from '../components/ui/Select'
import { SimulationBanner } from '../components/ui/SimulationBanner'
import { formatDate, formatDateTime, formatNumber, formatPercent, POSITION_LABEL, teamLabel } from '../lib/format'
import { useNumberParam, useSeasonSelection } from '../lib/useSeasonSelection'

const VENUES: [string, string][] = [
  ['home', 'Campo della squadra di casa'],
  ['neutral', 'Campo neutro'],
  ['swapped', 'Campi invertiti'],
]
const ITERATIONS = [5_000, 20_000, 50_000, 100_000]

function PlayerChecklist({ title, players, selected, toggle }: { title: string; players: PlayerOption[]; selected: Set<number>; toggle: (id: number) => void }) {
  if (players.length === 0) {
    return (
      <div>
        <p className="mb-1 text-xs font-semibold text-ink-muted uppercase">{title}</p>
        <p className="text-xs text-ink-faint">Nessun dato individuale disponibile dalla fonte.</p>
      </div>
    )
  }
  return (
    <fieldset>
      <legend className="mb-1 text-xs font-semibold text-ink-muted uppercase">{title}</legend>
      <ul className="max-h-60 space-y-0.5 overflow-y-auto pr-1">
        {players.map((p) => (
          <li key={p.player_id}>
            <label className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 text-sm hover:bg-navy-800">
              <input type="checkbox" checked={selected.has(p.player_id)} onChange={() => toggle(p.player_id)} className="accent-[var(--color-series-1)]" />
              <span className="min-w-0 flex-1 truncate">
                {p.name}
                {p.reported_unavailable && <span className="ml-1.5 text-[10px] font-semibold text-warn uppercase">segnalato indisponibile</span>}
              </span>
              <span className="text-xs text-ink-faint tabular-nums" title="Quota degli xG della squadra">
                {p.position ? POSITION_LABEL[p.position]?.slice(0, 3) : ''} · xG {formatPercent(p.xg_share !== null ? p.xg_share * 100 : null)}
              </span>
            </label>
          </li>
        ))}
      </ul>
    </fieldset>
  )
}

function Results({ sim }: { sim: Simulation }) {
  const h = teamLabel(sim.home_team)
  const a = teamLabel(sim.away_team)
  const shown = sim.scenario ?? sim.baseline
  const w = sim.training_window
  return (
    <div className="space-y-5">
      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="rounded-md border border-sim/50 bg-sim/15 px-2 py-0.5 text-xs font-bold tracking-wide text-sim">SIMULAZIONE</span>
          <h2 className="text-lg font-bold">{sim.home_team.name} – {sim.away_team.name}</h2>
          {sim.is_synthetic_data && <SyntheticBadge />}
        </div>
        <p className="mb-4 text-sm text-ink-muted">{sim.label}. Le percentuali indicano in quante simulazioni si è verificato ciascun esito.</p>
        <div className="space-y-3">
          <OutcomeBar label="Scenario base" outcome={sim.baseline} homeLabel={h} awayLabel={a} />
          {sim.scenario && <OutcomeBar label="Scenario modificato" outcome={sim.scenario} homeLabel={h} awayLabel={a} />}
          <OutcomeLegend homeLabel={h} awayLabel={a} />
        </div>
        <dl className="mt-5 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          {[
            ['Gol attesi (modello)', `${formatNumber(shown.expected_goals_home)} – ${formatNumber(shown.expected_goals_away)}`],
            ['Entrambe a segno', formatPercent(shown.both_score_share * 100, 1)],
            [`Porta inviolata ${h}`, formatPercent(shown.home_clean_sheet_share * 100, 1)],
            [`Porta inviolata ${a}`, formatPercent(shown.away_clean_sheet_share * 100, 1)],
          ].map(([k, v]) => (
            <div key={k} className="rounded-lg bg-navy-850 px-3 py-2">
              <dt className="text-xs text-ink-muted">{k}</dt>
              <dd className="font-semibold tabular-nums">{v}</dd>
            </div>
          ))}
        </dl>
      </Card>
      <div className="grid gap-5 lg:grid-cols-[2fr_1fr]">
        <Card title={`Distribuzione dei gol${sim.scenario ? ' (scenario modificato)' : ''}`}>
          <GoalsDistributionChart outcome={shown} homeLabel={h} awayLabel={a} />
        </Card>
        <Card title="Punteggi più frequenti">
          <table className="w-full text-sm tabular-nums">
            <tbody>
              {shown.top_scorelines.map(([score, share]) => (
                <tr key={score} className="border-b border-line/50">
                  <td className="py-1.5 font-semibold">{score.replace('-', ' – ')}</td>
                  <td className="text-right text-ink-muted">{formatPercent(share * 100, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Ipotesi">
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">{sim.assumptions.map((x) => <li key={x}>{x}</li>)}</ul>
        </Card>
        <Card title="Limitazioni">
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">{sim.limitations.map((x) => <li key={x}>{x}</li>)}</ul>
        </Card>
      </div>
      <Card title="Riproducibilità">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
          <div><dt className="text-xs text-ink-faint">Modello</dt><dd>{sim.model_version}</dd></div>
          <div><dt className="text-xs text-ink-faint">Seme casuale</dt><dd className="tabular-nums">{sim.seed}</dd></div>
          <div><dt className="text-xs text-ink-faint">Iterazioni</dt><dd className="tabular-nums">{formatNumber(sim.n_iterations)}</dd></div>
          <div><dt className="text-xs text-ink-faint">Partite usate</dt><dd className="tabular-nums">{w.matches_used} ({h}: {w.home_matches}, {a}: {w.away_matches})</dd></div>
          <div><dt className="text-xs text-ink-faint">Periodo dati</dt><dd>{w.start && w.end ? `${formatDate(w.start)} – ${formatDate(w.end)}` : '—'}</dd></div>
          <div><dt className="text-xs text-ink-faint">xG nei dati</dt><dd>{w.uses_xg ? 'Sì' : 'No'}</dd></div>
        </dl>
        <p className="mt-3 text-xs text-ink-faint">Con gli stessi dati, lo stesso seme e le stesse iterazioni la simulazione produce sempre lo stesso risultato. ID: {sim.id}</p>
      </Card>
    </div>
  )
}

export function SimulationLab() {
  const { competitions, season, setSeason } = useSeasonSelection()
  const [params, setParams] = useSearchParams()
  const [matchId] = useNumberParam('partita')
  const simId = params.get('simulazione') ?? undefined
  const match = useMatch(matchId)
  const teams = useTeams(season?.id)
  const [home, setHome] = useState<number | undefined>()
  const [away, setAway] = useState<number | undefined>()
  const [venue, setVenue] = useState('home')
  const [homeFormation, setHomeFormation] = useState('')
  const [awayFormation, setAwayFormation] = useState('')
  const [seed, setSeed] = useState(2026)
  const [iterations, setIterations] = useState(20_000)
  const [absent, setAbsent] = useState<Set<number>>(new Set())

  // Default to the first two teams of the season until the user picks.
  const homeId = home ?? teams.data?.[0]?.id
  const awayId = away ?? teams.data?.[1]?.id

  const optionsParams = matchId ? { match_id: matchId } : { season_id: season?.id, home_team_id: homeId, away_team_id: awayId }
  const options = useSimulationOptions(optionsParams)
  const run = useRunSimulation()
  const stored = useSimulation(simId)
  const history = useSimulationHistory()
  const result = run.data ?? stored.data

  const toggle = (id: number) =>
    setAbsent((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  const reported = useMemo(
    () => [...(options.data?.home_players ?? []), ...(options.data?.away_players ?? [])].filter((p) => p.reported_unavailable).map((p) => p.player_id),
    [options.data],
  )

  const submit = () => {
    run.mutate(
      {
        ...(matchId ? { match_id: matchId } : { season_id: season?.id, home_team_id: homeId, away_team_id: awayId }),
        venue: venue as 'home' | 'neutral' | 'swapped',
        unavailable_player_ids: [...absent],
        home_formation: homeFormation || null,
        away_formation: awayFormation || null,
        seed,
        n_iterations: iterations,
      },
      {
        onSuccess: (sim) =>
          setParams((prev) => {
            const next = new URLSearchParams(prev)
            next.set('simulazione', sim.id)
            return next
          }, { replace: true }),
      },
    )
  }

  const runError = run.error instanceof ApiError ? run.error.message : run.error?.message

  return (
    <>
      <PageHeader title="Laboratorio Simulazioni" description="Scenari tattici virtuali basati su dati storici: assenze, moduli e campo di gioco. Le simulazioni non sono risultati reali." />
      <SimulationBanner />
      <div className="grid gap-5 xl:grid-cols-[24rem_1fr]">
        <div className="space-y-5">
          <Card title="Scenario">
            <div className="space-y-3">
              {matchId ? (
                <div className="rounded-lg bg-navy-850 p-3 text-sm">
                  <p className="text-xs text-ink-muted">Partita selezionata</p>
                  {match.data ? (
                    <p className="font-semibold">{match.data.home_team.name} – {match.data.away_team.name}<span className="block text-xs font-normal text-ink-faint">{match.data.competition_name} · {formatDateTime(match.data.kickoff_at)} · dati fino al calcio d'inizio</span></p>
                  ) : <LoadingBlock rows={1} />}
                  <button type="button" className="mt-2 text-xs text-accent hover:underline" onClick={() => setParams(new URLSearchParams(), { replace: true })}>Scegli squadre liberamente</button>
                </div>
              ) : (
                <QueryState query={competitions} rows={2}>
                  {(list) => (
                    <>
                      <SeasonSelect competitions={list} seasonId={season?.id} onChange={(id) => { setSeason(id); setHome(undefined); setAway(undefined); setAbsent(new Set()) }} />
                      <Select label="Squadra di casa" value={String(homeId ?? '')} onChange={(v) => { setHome(Number(v)); setAbsent(new Set()) }}>
                        {teams.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                      </Select>
                      <Select label="Squadra ospite" value={String(awayId ?? '')} onChange={(v) => { setAway(Number(v)); setAbsent(new Set()) }}>
                        {teams.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                      </Select>
                      {homeId !== undefined && homeId === awayId && <p className="text-xs text-danger">Scegli due squadre diverse.</p>}
                    </>
                  )}
                </QueryState>
              )}
              <Select label="Campo" value={venue} onChange={setVenue}>
                {VENUES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
              </Select>
              <div className="grid grid-cols-2 gap-3">
                <Select label="Modulo casa" value={homeFormation} onChange={setHomeFormation}>
                  <option value="">Abituale{options.data?.home_usual_formation ? ` (${options.data.home_usual_formation})` : ''}</option>
                  {options.data?.formations.map((f) => <option key={f} value={f}>{f}</option>)}
                </Select>
                <Select label="Modulo ospite" value={awayFormation} onChange={setAwayFormation}>
                  <option value="">Abituale{options.data?.away_usual_formation ? ` (${options.data.away_usual_formation})` : ''}</option>
                  {options.data?.formations.map((f) => <option key={f} value={f}>{f}</option>)}
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
                  Seme casuale
                  <input type="number" min={0} max={2147483647} value={seed} onChange={(e) => setSeed(Math.max(0, Math.min(2147483647, Number(e.target.value) || 0)))} className="h-9 rounded-md border border-line bg-navy-850 px-2.5 text-sm text-ink tabular-nums" />
                </label>
                <Select label="Iterazioni" value={String(iterations)} onChange={(v) => setIterations(Number(v))}>
                  {ITERATIONS.map((n) => <option key={n} value={n}>{formatNumber(n)}</option>)}
                </Select>
              </div>
            </div>
          </Card>
          <Card title="Giocatori assenti (scenario)" action={reported.length ? <button type="button" className="text-xs text-accent hover:underline" onClick={() => setAbsent(new Set(reported))}>Usa indisponibili segnalati</button> : undefined}>
            {options.isPending && options.fetchStatus !== 'idle' ? <LoadingBlock rows={5} /> : options.isError ? (
              <ErrorState message={options.error.message} onRetry={() => void options.refetch()} />
            ) : options.data ? (
              <div className="space-y-4">
                <PlayerChecklist title={options.data.home_team.name} players={options.data.home_players} selected={absent} toggle={toggle} />
                <PlayerChecklist title={options.data.away_team.name} players={options.data.away_players} selected={absent} toggle={toggle} />
                {absent.size > 0 && (
                  <button type="button" className="inline-flex items-center gap-1 text-xs text-ink-muted hover:text-ink" onClick={() => setAbsent(new Set())}><RotateCcw className="size-3" /> Azzera assenze</button>
                )}
              </div>
            ) : <p className="text-sm text-ink-faint">Seleziona le squadre.</p>}
          </Card>
          <button
            type="button"
            onClick={submit}
            disabled={run.isPending || (!matchId && (homeId === undefined || awayId === undefined || homeId === awayId))}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-sim/80 px-4 py-2.5 font-semibold text-white hover:bg-sim disabled:opacity-50"
          >
            <Play className="size-4" /> {run.isPending ? 'Simulazione in corso…' : 'Esegui simulazione'}
          </button>
          <Card title="Simulazioni recenti" action={<History className="size-4 text-ink-faint" />}>
            <QueryState query={history} rows={3}>
              {(items) => items.length ? (
                <ul className="divide-y divide-line/50 text-sm">
                  {items.map((s) => (
                    <li key={s.id}>
                      <button type="button" className="w-full py-2 text-left hover:text-accent" onClick={() => { run.reset(); setParams((prev) => { const n = new URLSearchParams(prev); n.set('simulazione', s.id); return n }, { replace: true }) }}>
                        {teamLabel(s.home_team)} – {teamLabel(s.away_team)}
                        <span className="block text-xs text-ink-faint">{formatDateTime(s.created_at)} · seme {s.seed}{s.has_scenario ? ' · scenario' : ''}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : <p className="text-sm text-ink-faint">Nessuna simulazione eseguita.</p>}
            </QueryState>
          </Card>
        </div>
        <div className="min-w-0">
          {runError ? (
            <ErrorState title="Simulazione non eseguita" message={runError} />
          ) : result ? (
            <Results sim={result} />
          ) : stored.isPending && simId ? (
            <LoadingBlock rows={8} />
          ) : (
            <Card>
              <EmptyState icon={FlaskConical} title="Nessuna simulazione" message="Configura lo scenario e premi «Esegui simulazione». Puoi anche partire da una partita dal Centro Partite." />
            </Card>
          )}
        </div>
      </div>
    </>
  )
}
