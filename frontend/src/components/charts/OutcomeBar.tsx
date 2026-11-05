import type { SimulationOutcome } from '../../api/types'
import { formatPercent } from '../../lib/format'
import { SERIES } from './chartTheme'

interface Props {
  label: string
  outcome: SimulationOutcome
  homeLabel: string
  awayLabel: string
}

/** 100% bar of simulated outcome frequencies, directly labelled, 2px gaps between segments. */
export function OutcomeBar({ label, outcome, homeLabel, awayLabel }: Props) {
  const parts = [
    { key: 'home', name: `Vittoria ${homeLabel}`, value: outcome.home_win_share, color: SERIES.one },
    { key: 'draw', name: 'Pareggio', value: outcome.draw_share, color: SERIES.three },
    { key: 'away', name: `Vittoria ${awayLabel}`, value: outcome.away_win_share, color: SERIES.two },
  ]
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-ink-muted">{label}</p>
      <div className="flex h-8 gap-0.5" role="img" aria-label={`${label}: ${parts.map((p) => `${p.name} ${formatPercent(p.value * 100, 1)}`).join(', ')}`}>
        {parts.map((p, i) => (
          <div
            key={p.key}
            title={`${p.name}: ${formatPercent(p.value * 100, 1)} delle simulazioni`}
            className={`flex items-center justify-center overflow-hidden text-xs font-semibold text-white ${i === 0 ? 'rounded-l-md' : ''} ${i === parts.length - 1 ? 'rounded-r-md' : ''}`}
            style={{ width: `${p.value * 100}%`, background: p.color, minWidth: p.value > 0 ? 2 : 0 }}
          >
            {p.value >= 0.08 ? formatPercent(p.value * 100, 0) : ''}
          </div>
        ))}
      </div>
    </div>
  )
}

export function OutcomeLegend({ homeLabel, awayLabel }: { homeLabel: string; awayLabel: string }) {
  const items = [
    [`Vittoria ${homeLabel}`, SERIES.one],
    ['Pareggio', SERIES.three],
    [`Vittoria ${awayLabel}`, SERIES.two],
  ]
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
      {items.map(([name, color]) => (
        <li key={name} className="flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-sm" style={{ background: color }} />
          {name}
        </li>
      ))}
    </ul>
  )
}
