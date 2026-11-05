import { Bot, FileText, Play, RefreshCw } from 'lucide-react'
import { Link, useSearchParams } from 'react-router'

import { useAgentCatalogue, useAIUsage, useAnalysis, useMatch, useMatches, useStartAnalysis } from '../api/queries'
import { AgentReportView } from '../components/domain/AgentReportView'
import { AgentStatusBadge, ConfidenceBadge } from '../components/domain/AgentStatusBadge'
import { SeasonSelect } from '../components/domain/SeasonSelect'
import { SyntheticBadge } from '../components/domain/SyntheticBadge'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { PageHeader } from '../components/ui/PageHeader'
import { QueryState } from '../components/ui/QueryState'
import { Select } from '../components/ui/Select'
import { formatDateTime, formatNumber, teamLabel } from '../lib/format'
import { useNumberParam, useSeasonSelection } from '../lib/useSeasonSelection'

function UsagePanel() {
  const usage = useAIUsage()
  return (
    <Card title="Utilizzo AI oggi">
      <QueryState query={usage} rows={3}>
        {(u) => (
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-ink-muted">Fornitore</dt><dd>{u.provider === 'mock' ? 'Simulato (offline, gratuito)' : `${u.provider} · ${u.model}`}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-muted">Sforzo</dt><dd>{u.effort}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-muted">Chiamate</dt><dd className="tabular-nums">{formatNumber(u.today_calls)} / {formatNumber(u.limits.daily_calls)}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-muted">Token</dt><dd className="tabular-nums">{formatNumber(u.today_tokens)} / {formatNumber(u.limits.daily_tokens)}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-muted">Max chiamate per analisi</dt><dd className="tabular-nums">{u.limits.calls_per_analysis}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-muted">Risposte in cache (riutilizzi)</dt><dd className="tabular-nums">{formatNumber(u.cache_entries)} ({formatNumber(u.cache_hits)})</dd></div>
          </dl>
        )}
      </QueryState>
    </Card>
  )
}

function MatchPicker({ onPick, selected, seasonId }: { onPick: (id: number) => void; selected?: number; seasonId?: number }) {
  const { competitions, season, setSeason } = useSeasonSelection(seasonId)
  const matches = useMatches({ season_id: season?.id, order: 'desc', limit: 200 }, season !== undefined)
  return (
    <QueryState query={competitions} rows={2}>
      {(list) => (
        <div className="grid gap-3 sm:grid-cols-2">
          <SeasonSelect competitions={list} seasonId={season?.id} onChange={setSeason} />
          <Select label="Partita" value={String(selected ?? '')} onChange={(v) => onPick(Number(v))}>
            <option value="">Seleziona una partita…</option>
            {matches.data?.items.map((m) => (
              <option key={m.id} value={m.id}>
                {m.matchday ? `G${m.matchday} · ` : ''}{teamLabel(m.home_team)} – {teamLabel(m.away_team)}
                {m.home_score !== null ? ` (${m.home_score}-${m.away_score})` : ' (in programma)'}
              </option>
            ))}
          </Select>
        </div>
      )}
    </QueryState>
  )
}

export function AIAgents() {
  const catalogue = useAgentCatalogue()
  const [matchId, setMatchId] = useNumberParam('partita')
  const [params, setParams] = useSearchParams()
  const analysisId = params.get('analisi') ?? undefined
  const match = useMatch(matchId)
  const start = useStartAnalysis()
  const analysis = useAnalysis(analysisId)

  const launch = (force = false) => {
    if (!matchId) return
    start.mutate({ match_id: matchId, force }, {
      onSuccess: (a) => setParams((prev) => { const n = new URLSearchParams(prev); n.set('analisi', a.id); return n }, { replace: true }),
    })
  }

  return (
    <>
      <PageHeader title="Agenti AI" description="Cinque agenti analizzano solo dati verificati; il Master Analyst confronta i loro report, segnala contraddizioni e lacune." />
      <QueryState query={catalogue} rows={2}>
        {(agents) => (
          <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {agents.map((a, i) => (
              <div key={a.name} className="rounded-xl border border-line bg-navy-900/80 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <span className="flex size-6 items-center justify-center rounded-md bg-navy-700 text-xs text-accent">{i + 1}</span>
                  {a.title}
                </p>
                <p className="mt-2 text-xs text-ink-muted">{a.description}</p>
                <p className="mt-2 text-[11px] text-ink-faint">Dati: {a.data_needs.join(', ')}</p>
              </div>
            ))}
          </div>
        )}
      </QueryState>

      <div className="grid gap-5 xl:grid-cols-[1fr_20rem]">
        <div className="min-w-0 space-y-5">
          <Card title="Analizza una partita">
            <MatchPicker selected={matchId} seasonId={match.data?.season_id} onPick={(id) => { setMatchId(id); setParams((prev) => { const n = new URLSearchParams(prev); n.set('partita', String(id)); n.delete('analisi'); return n }, { replace: true }) }} />
            {match.data && (
              <p className="mt-3 flex flex-wrap items-center gap-2 text-sm text-ink-muted">
                {match.data.home_team.name} – {match.data.away_team.name} · {match.data.competition_name} · {formatDateTime(match.data.kickoff_at)}
                {match.data.is_synthetic && <SyntheticBadge />}
              </p>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" disabled={!matchId || start.isPending} onClick={() => launch(false)} className="inline-flex items-center gap-2 rounded-lg bg-accent/80 px-4 py-2 text-sm font-semibold text-navy-950 hover:bg-accent disabled:opacity-50">
                <Play className="size-4" /> {start.isPending ? 'Avvio…' : 'Avvia analisi'}
              </button>
              {analysis.data && !['queued', 'running'].includes(analysis.data.status) && (
                <button type="button" disabled={start.isPending} onClick={() => launch(true)} className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm hover:bg-navy-800" title="Ricalcola: le risposte identiche sono comunque servite dalla cache">
                  <RefreshCw className="size-4" /> Rianalizza
                </button>
              )}
            </div>
            <p className="mt-2 text-xs text-ink-faint">Se i dati non sono cambiati, viene riutilizzata l'analisi precedente senza nuove chiamate AI.</p>
            {start.isError && <div className="mt-3"><ErrorState title="Analisi non avviata" message={start.error.message} /></div>}
          </Card>

          {analysisId ? (
            <QueryState query={analysis} rows={6}>
              {(a) => (
                <>
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <AgentStatusBadge status={a.status} />
                    {a.reused && <span className="rounded-full border border-line px-2 py-0.5 text-[11px] text-ink-muted">Analisi riutilizzata</span>}
                    <span className="text-ink-faint">Richiesta {formatDateTime(a.requested_at)} · {a.provider === 'mock' ? 'fornitore simulato' : a.model}</span>
                  </div>
                  {a.error && <p className="text-xs text-warn">{a.error}</p>}
                  <div className="grid gap-5 lg:grid-cols-2">
                    {a.agents.map((slot) => (
                      <Card key={slot.agent} title={slot.title} action={<AgentStatusBadge status={slot.status} />}>
                        {slot.report ? <AgentReportView report={slot.report} /> : <p className="text-sm text-ink-faint">{slot.status === 'failed' ? 'Nessun report.' : 'In elaborazione…'}</p>}
                      </Card>
                    ))}
                  </div>
                  <Card title="Master Analyst" action={a.final_report ? <ConfidenceBadge value={a.final_report.confidence} /> : <AgentStatusBadge status={a.status === 'running' || a.status === 'queued' ? 'pending' : 'failed'} />}>
                    {a.final_report ? (
                      <div className="space-y-3 text-sm">
                        <p>{a.final_report.summary}</p>
                        {a.final_report.generated_by === 'automatic' && <p className="text-xs text-warn">Sintesi automatica senza AI: il Master Analyst non era disponibile.</p>}
                        <Link to={`/report/${a.id}`} className="inline-flex items-center gap-1.5 text-accent hover:underline"><FileText className="size-4" /> Apri il report completo</Link>
                      </div>
                    ) : <p className="text-sm text-ink-faint">Il report finale sarà disponibile al termine degli agenti.</p>}
                  </Card>
                </>
              )}
            </QueryState>
          ) : (
            <Card><EmptyState icon={Bot} title="Nessuna analisi selezionata" message="Scegli una partita e avvia l'analisi, oppure aprila dal Centro Partite." /></Card>
          )}
        </div>
        <UsagePanel />
      </div>
    </>
  )
}
