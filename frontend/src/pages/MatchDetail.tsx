import { ArrowLeft, FlaskConical, Info } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { useMatch, useMatchContext } from '../api/queries'
import type { MatchDetail as Match, TeamContext } from '../api/types'
import { StatCompare } from '../components/charts/StatCompare'
import { FormStrip } from '../components/domain/ResultBadge'
import { SourceAttribution } from '../components/domain/SourceAttribution'
import { SyntheticBadge } from '../components/domain/SyntheticBadge'
import { Pitch } from '../components/pitch/Pitch'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { QueryState } from '../components/ui/QueryState'
import { AVAILABILITY_LABEL, formatDate, formatDateTime, formatNumber, formatPercent, STATUS_LABEL, teamLabel } from '../lib/format'

function Scoreboard({ m }: { m: Match }) {
  const played = m.home_score !== null && m.away_score !== null
  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-center gap-2 text-xs text-ink-muted">
        <span>{m.competition_name} {m.season_label}</span>
        {m.matchday && <span>· Giornata {m.matchday}</span>}
        <span>· {formatDateTime(m.kickoff_at)}</span>
        {m.is_synthetic && <SyntheticBadge />}
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        <h1 className="text-right text-lg font-bold sm:text-2xl">{m.home_team.name}</h1>
        <div className="text-center">
          {played ? (
            <p className="rounded-lg bg-navy-700 px-4 py-2 text-3xl font-black tabular-nums sm:text-4xl">{m.home_score} – {m.away_score}</p>
          ) : (
            <p className="rounded-lg bg-navy-800 px-4 py-2 text-sm font-semibold">{STATUS_LABEL[m.status]}</p>
          )}
          {m.home_score_ht !== null && <p className="mt-1 text-xs text-ink-faint">1° tempo {m.home_score_ht} – {m.away_score_ht}</p>}
        </div>
        <h1 className="text-lg font-bold sm:text-2xl">{m.away_team.name}</h1>
      </div>
    </Card>
  )
}

function TeamPreview({ ctx, venue }: { ctx: TeamContext; venue: 'casa' | 'trasferta' }) {
  return (
    <div className="space-y-3 text-sm">
      <h3 className="font-semibold">{ctx.team.name}</h3>
      <dl className="grid grid-cols-2 gap-2">
        <dt className="text-ink-muted">Posizione</dt>
        <dd className="text-right tabular-nums">{ctx.position ? `${ctx.position}° (${ctx.points} pt)` : '—'}</dd>
        <dt className="text-ink-muted">Ultime 5</dt>
        <dd className="text-right"><FormStrip results={ctx.form_last5.matches.map((x) => x.result).reverse()} /></dd>
        <dt className="text-ink-muted">Ultime 5 in {venue}</dt>
        <dd className="text-right"><FormStrip results={ctx.venue_form_last5.matches.map((x) => x.result).reverse()} /></dd>
        <dt className="text-ink-muted">Gol fatti/subiti (ultime 5)</dt>
        <dd className="text-right tabular-nums">{ctx.form_last5.sample_size ? `${ctx.form_last5.goals_for} / ${ctx.form_last5.goals_against}` : '—'}</dd>
        <dt className="text-ink-muted">xG creati/concessi (ultime 5)</dt>
        <dd className="text-right tabular-nums">{ctx.form_last5.xg_for !== null ? `${formatNumber(ctx.form_last5.xg_for)} / ${formatNumber(ctx.form_last5.xg_against)}` : 'Non disponibile'}</dd>
        <dt className="text-ink-muted">Ultimo modulo</dt>
        <dd className="text-right">{ctx.last_lineup?.formation ?? 'Non disponibile'}</dd>
      </dl>
      <div>
        <p className="mb-1 text-xs font-semibold text-ink-muted uppercase">Indisponibili (fonte verificata)</p>
        {ctx.availability.length ? (
          <ul className="space-y-1">
            {ctx.availability.map((a) => (
              <li key={a.player_id} className="rounded-md bg-navy-850 px-2.5 py-1.5 text-xs">
                <span className="font-medium text-ink">{a.player_name}</span> · {AVAILABILITY_LABEL[a.type] ?? a.type}
                {a.description && <span className="text-ink-muted"> — {a.description}</span>}
                <span className="block text-ink-faint">
                  Segnalato il {formatDate(a.reported_at)} · {formatPercent(a.minutes_share ? a.minutes_share * 100 : null)} dei minuti
                  {a.xg_share !== null && ` · ${formatPercent(a.xg_share * 100)} degli xG`}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-ink-faint">Nessuna indisponibilità segnalata dalle fonti.</p>
        )}
      </div>
    </div>
  )
}

export function MatchDetail() {
  const { id } = useParams()
  const matchId = id && /^\d+$/.test(id) ? Number(id) : undefined
  const match = useMatch(matchId)
  const context = useMatchContext(matchId)

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/partite" className="inline-flex items-center gap-1 text-sm text-accent hover:underline">
          <ArrowLeft className="size-4" /> Centro Partite
        </Link>
        {matchId && (
          <Link to={`/simulazioni?partita=${matchId}`} className="inline-flex items-center gap-1.5 rounded-md border border-sim/50 px-3 py-1.5 text-sm text-sim hover:bg-sim/10">
            <FlaskConical className="size-4" /> Simula questa partita
          </Link>
        )}
      </div>
      <QueryState query={match} rows={6}>
        {(m) => {
          const [hs, as] = [m.team_stats.find((s) => s.is_home), m.team_stats.find((s) => !s.is_home)]
          const lineupFor = (teamId: number) => m.lineups.find((l) => l.team_id === teamId)
          const hl = lineupFor(m.home_team.id)
          const al = lineupFor(m.away_team.id)
          return (
            <>
              <Scoreboard m={m} />
              <div className="grid gap-5 lg:grid-cols-2">
                <Card title="Statistiche della partita">
                  {hs && as ? (
                    <StatCompare
                      homeLabel={teamLabel(m.home_team)}
                      awayLabel={teamLabel(m.away_team)}
                      rows={[
                        { label: 'xG', home: hs.xg, away: as.xg },
                        { label: 'Tiri', home: hs.shots, away: as.shots },
                        { label: 'Tiri in porta', home: hs.shots_on_target, away: as.shots_on_target },
                        { label: 'Possesso', home: hs.possession_pct, away: as.possession_pct, digits: 0, suffix: '%' },
                        { label: "Calci d'angolo", home: hs.corners, away: as.corners },
                        { label: 'Falli', home: hs.fouls, away: as.fouls },
                        { label: 'Ammonizioni', home: hs.yellow_cards, away: as.yellow_cards },
                        { label: 'Fuorigioco', home: hs.offsides, away: as.offsides },
                      ]}
                    />
                  ) : (
                    <EmptyState title="Statistiche non disponibili" message={m.status === 'finished' ? 'La fonte di questa competizione fornisce solo il risultato.' : 'Le statistiche saranno disponibili dopo la partita, se fornite dalla fonte.'} />
                  )}
                </Card>
                <Card title="Formazioni">
                  {hl || al ? (
                    <>
                      <div className="mb-2 flex justify-between text-xs text-ink-muted">
                        <span>{teamLabel(m.home_team)} · {hl?.formation ?? '—'}</span>
                        <span>{al?.formation ?? '—'} · {teamLabel(m.away_team)}</span>
                      </div>
                      <Pitch
                        home={hl && { entries: hl.entries, formation: hl.formation, label: m.home_team.name }}
                        away={al && { entries: al.entries, formation: al.formation, label: m.away_team.name }}
                      />
                      <p className="mt-2 text-xs text-ink-faint">{hl?.confirmed ? 'Formazioni ufficiali.' : 'Formazioni non confermate.'}</p>
                    </>
                  ) : (
                    <EmptyState title="Formazioni non disponibili" message="La fonte non fornisce le formazioni per questa partita." />
                  )}
                </Card>
              </div>
              <Card title="Situazione prima del calcio d'inizio">
                <QueryState query={context} rows={5}>
                  {(ctx) => (
                    <>
                      <div className="grid gap-6 md:grid-cols-2">
                        <TeamPreview ctx={ctx.home} venue="casa" />
                        <TeamPreview ctx={ctx.away} venue="trasferta" />
                      </div>
                      <p className="mt-4 text-sm">
                        <span className="text-ink-muted">Scontri diretti disponibili: </span>
                        {ctx.head_to_head.sample_size
                          ? `${ctx.head_to_head.sample_size} — ${teamLabel(m.home_team)} ${ctx.head_to_head.team_a_wins} vittorie, ${ctx.head_to_head.draws} pareggi, ${teamLabel(m.away_team)} ${ctx.head_to_head.team_b_wins} vittorie`
                          : 'nessuno nei dati importati'}
                      </p>
                      {ctx.missing.length > 0 && (
                        <div className="mt-4 rounded-lg border border-warn/30 bg-warn/5 p-3 text-xs">
                          <p className="mb-1 flex items-center gap-1.5 font-semibold text-warn"><Info className="size-3.5" /> Informazioni mancanti</p>
                          <ul className="list-disc space-y-0.5 pl-5 text-ink-muted">{ctx.missing.map((x) => <li key={x}>{x}</li>)}</ul>
                        </div>
                      )}
                    </>
                  )}
                </QueryState>
              </Card>
              <SourceAttribution source={m.source} attribution={m.attribution} fetchedAt={m.provenance.fetched_at} updatedAt={m.provenance.source_updated_at} />
            </>
          )
        }}
      </QueryState>
    </div>
  )
}
