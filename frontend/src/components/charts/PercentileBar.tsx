import { formatNumber } from '../../lib/format'

/** Single-series percentile meter (0–100) with league average marked. */
export function PercentileBar({ percentile }: { percentile: number | null }) {
  if (percentile === null) return <span className="text-xs text-ink-faint">—</span>
  return (
    <div className="flex items-center gap-2" title={`Percentile ${formatNumber(percentile, 0)} nel campionato`}>
      <div className="relative h-1.5 w-24 rounded-full bg-navy-700">
        <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${percentile}%`, background: 'var(--color-series-1)' }} />
        <div className="absolute inset-y-[-3px] left-1/2 w-px bg-ink-faint" aria-hidden="true" />
      </div>
      <span className="w-8 text-right text-xs tabular-nums text-ink-muted">{formatNumber(percentile, 0)}</span>
    </div>
  )
}
