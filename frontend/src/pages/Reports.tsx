import { ArrowLeft, Download, FileText, Printer } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { useAnalyses, useAnalysis } from '../api/queries'
import { AgentStatusBadge, ConfidenceBadge } from '../components/domain/AgentStatusBadge'
import { SyntheticBadge } from '../components/domain/SyntheticBadge'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import { QueryState } from '../components/ui/QueryState'
import { formatDateTime } from '../lib/format'

const AGENT_TITLE: Record<string, string> = {
  match_analyst: 'Match Analyst',
  statistics: 'Statistics AI',
  team_intelligence: 'Team Intelligence',
  simulation: 'Simulation AI',
}

export function ReportsList() {
  const list = useAnalyses()
  return (
    <>
      <PageHeader title="Report" description="Report finali generati dal Master Analyst, con fonti, contraddizioni e informazioni mancanti." />
      <Card>
        <QueryState query={list} rows={6}>
          {(items) => items.length ? (
            <ul className="divide-y divide-line/60">
              {items.map((r) => (
                <li key={r.id}>
                  <Link to={`/report/${r.id}`} className="flex flex-col gap-1 py-3 hover:bg-navy-800/50 sm:flex-row sm:items-center sm:gap-4">
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2 font-medium">
                        {r.match.home_team.name} – {r.match.away_team.name}
                        {r.match.is_synthetic && <SyntheticBadge />}
                      </span>
                      <span className="block truncate text-xs text-ink-muted">{r.summary ?? 'Report non ancora disponibile'}</span>
                    </span>
                    <span className="flex shrink-0 items-center gap-2 text-xs text-ink-faint">
                      {formatDateTime(r.requested_at)}
                      <ConfidenceBadge value={r.confidence} />
                      {r.status !== 'completed' && <AgentStatusBadge status={r.status} />}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : <EmptyState icon={FileText} title="Nessun report" message="Avvia un'analisi dalla pagina Agenti AI per generare il primo report." />}
        </QueryState>
      </Card>
    </>
  )
}

export function ReportDetail() {
  const { id } = useParams()
  const analysis = useAnalysis(id)
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link to="/report" className="inline-flex items-center gap-1 text-sm text-accent hover:underline"><ArrowLeft className="size-4" /> Tutti i report</Link>
        <span className="flex gap-2">
          <a href={`/api/v1/analyses/${id}/report.md`} className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-navy-800"><Download className="size-4" /> Markdown</a>
          <button type="button" onClick={() => window.print()} className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-navy-800"><Printer className="size-4" /> Stampa / PDF</button>
        </span>
      </div>
      <QueryState query={analysis} rows={8}>
        {(a) => {
          const fr = a.final_report
          if (!fr) return <EmptyState title="Report non ancora disponibile" message="L'analisi è ancora in corso o non è riuscita." />
          const m = fr.match
          return (
            <>
              <header>
                <p className="text-xs text-ink-muted">{m.competition_name} {m.season_label}{m.matchday ? ` · Giornata ${m.matchday}` : ''} · {formatDateTime(m.kickoff_at)}</p>
                <h1 className="mt-1 flex flex-wrap items-center gap-2 text-2xl font-bold sm:text-3xl">
                  {m.home_team.name} – {m.away_team.name}
                  {m.home_score !== null && <span className="text-ink-muted">{m.home_score} – {m.away_score}</span>}
                </h1>
                <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
                  <ConfidenceBadge value={fr.confidence} />
                  {m.is_synthetic && <SyntheticBadge />}
                  <span>Dati al {formatDateTime(fr.data_as_of)} · {fr.generated_by === 'ai' ? `generato con AI (${fr.provider === 'mock' ? 'fornitore simulato' : fr.model})` : 'sintesi automatica senza AI'}</span>
                </p>
              </header>
              <Card title="Sintesi"><p className="text-sm leading-relaxed">{fr.summary}</p></Card>
              <div className="grid gap-5 lg:grid-cols-2">
                <Card title="Punti chiave">
                  <ul className="space-y-2 text-sm">
                    {fr.key_findings.map((k, i) => (
                      <li key={i} className="rounded-md bg-navy-850 px-3 py-2">
                        <span className="text-[11px] font-semibold text-accent uppercase">{AGENT_TITLE[k.agent ?? ''] ?? k.agent}</span>
                        <p>{k.finding}</p>
                      </li>
                    ))}
                  </ul>
                </Card>
                <Card title="Accordi e contraddizioni">
                  {fr.agreements.length > 0 && (
                    <ul className="mb-3 list-disc space-y-1 pl-5 text-sm">{fr.agreements.map((x) => <li key={x}>{x}</li>)}</ul>
                  )}
                  {fr.contradictions.length ? (
                    <ul className="space-y-2 text-sm">
                      {fr.contradictions.map((c, i) => (
                        <li key={i} className="rounded-md border border-warn/30 bg-warn/5 px-3 py-2">
                          <p>{String(c.description ?? '')}</p>
                          {c.assessment ? <p className="mt-1 text-xs text-ink-muted">Valutazione: {String(c.assessment)}</p> : null}
                        </li>
                      ))}
                    </ul>
                  ) : <p className="text-sm text-ink-faint">Nessuna contraddizione rilevata.</p>}
                </Card>
              </div>
              <div className="grid gap-5 lg:grid-cols-2">
                <Card title="Informazioni mancanti">
                  {fr.missing_information.length ? <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">{fr.missing_information.map((x) => <li key={x}>{x}</li>)}</ul> : <p className="text-sm text-ink-faint">Nessuna.</p>}
                </Card>
                <Card title="Agenti e fonti">
                  <ul className="space-y-1.5 text-sm">
                    {Object.keys(AGENT_TITLE).filter((k) => k in fr.agent_statuses).map((agent) => [agent, fr.agent_statuses[agent] ?? ''] as const).map(([agent, status]) => (
                      <li key={agent} className="flex items-center justify-between gap-2"><span>{AGENT_TITLE[agent] ?? agent}</span><AgentStatusBadge status={status} /></li>
                    ))}
                  </ul>
                  <ul className="mt-3 space-y-1 text-xs text-ink-faint">
                    {fr.sources.map((s, i) => <li key={i}>Fonte: {String(s.name ?? '')} — {String(s.attribution_text ?? '')}</li>)}
                  </ul>
                  <Link to={`/agenti?partita=${m.id}&analisi=${a.id}`} className="mt-3 inline-block text-xs text-accent hover:underline print:hidden">Vedi i report dei singoli agenti</Link>
                </Card>
              </div>
              <p className="rounded-lg border border-line bg-navy-900 p-3 text-xs text-ink-muted">{fr.disclaimer}</p>
            </>
          )
        }}
      </QueryState>
    </div>
  )
}
