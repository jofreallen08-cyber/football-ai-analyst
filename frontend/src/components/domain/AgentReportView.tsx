import type { AgentReport } from '../../api/types'

const STRENGTH: Record<string, string> = { low: 'debole', medium: 'media', high: 'forte' }

export function AgentReportView({ report }: { report: AgentReport }) {
  return (
    <div className="space-y-3 text-sm">
      <p className="font-semibold">{report.headline}</p>
      {report.findings.length > 0 && (
        <ul className="space-y-2">
          {report.findings.map((f, i) => (
            <li key={i} className="rounded-md bg-navy-850 px-3 py-2">
              <p>{f.claim}</p>
              <p className="mt-1 flex flex-wrap items-center gap-1 text-[11px] text-ink-faint">
                <span>Evidenza {STRENGTH[f.strength] ?? f.strength} · dati:</span>
                {f.evidence_keys.map((k) => (
                  <code key={k} className="rounded bg-navy-700 px-1 py-px font-mono text-[10px] text-ink-muted">{k}</code>
                ))}
              </p>
            </li>
          ))}
        </ul>
      )}
      {report.missing_information.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-ink-muted uppercase">Informazioni mancanti</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-ink-muted">
            {report.missing_information.map((m) => <li key={m}>{m}</li>)}
          </ul>
        </div>
      )}
      {report.limitations.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-ink-muted uppercase">Limitazioni</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-ink-muted">
            {report.limitations.map((m) => <li key={m}>{m}</li>)}
          </ul>
        </div>
      )}
      {(report.rejected_findings ?? 0) > 0 && (
        <p className="text-xs text-warn">{report.rejected_findings} affermazioni scartate perché non supportate dai dati.</p>
      )}
      <p className="text-[11px] text-ink-faint">
        {report.provider} · {report.model} · prompt {report.prompt_version} · fonti: {report.sources.join(', ') || '—'}
      </p>
    </div>
  )
}
