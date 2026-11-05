import { formatNumber } from '../../lib/format'
import { SERIES } from './chartTheme'

export interface CompareRow {
  label: string
  home: number | null
  away: number | null
  digits?: number
  suffix?: string
}

/** Head-to-head statistic bars: home in series-1, away in series-2, 2px gap between fills. */
export function StatCompare({ rows, homeLabel, awayLabel }: { rows: CompareRow[]; homeLabel: string; awayLabel: string }) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between text-xs text-ink-muted">
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-sm" style={{ background: SERIES.one }} />
          {homeLabel}
        </span>
        <span className="flex items-center gap-1.5">
          {awayLabel}
          <span className="inline-block size-2.5 rounded-sm" style={{ background: SERIES.two }} />
        </span>
      </div>
      <dl className="space-y-3">
        {rows.map((r) => {
          const available = r.home !== null && r.away !== null
          const total = available ? (r.home ?? 0) + (r.away ?? 0) : 0
          const homePct = available && total > 0 ? ((r.home ?? 0) / total) * 100 : 50
          return (
            <div key={r.label}>
              <div className="mb-1 flex items-center justify-between text-sm tabular-nums">
                <span className="font-semibold">{formatNumber(r.home, r.digits)}{r.home !== null ? r.suffix : ''}</span>
                <dt className="text-xs text-ink-muted">{r.label}</dt>
                <span className="font-semibold">{formatNumber(r.away, r.digits)}{r.away !== null ? r.suffix : ''}</span>
              </div>
              {available ? (
                <div className="flex h-2 gap-0.5" title={`${r.label}: ${formatNumber(r.home)} – ${formatNumber(r.away)}`}>
                  <div className="rounded-l-sm" style={{ width: `${homePct}%`, background: SERIES.one }} />
                  <div className="rounded-r-sm" style={{ width: `${100 - homePct}%`, background: SERIES.two }} />
                </div>
              ) : (
                <p className="text-center text-[11px] text-ink-faint">Non disponibile dalla fonte</p>
              )}
            </div>
          )
        })}
      </dl>
    </div>
  )
}
