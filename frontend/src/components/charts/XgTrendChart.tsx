import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { SeriesPoint, TeamRef } from '../../api/types'
import { formatNumber, formatShortDate, teamLabel } from '../../lib/format'
import { AXIS, legendText, SERIES } from './chartTheme'
import { TooltipBox } from './ChartTooltip'

interface Props {
  points: SeriesPoint[]
  teams: Record<string, TeamRef>
}

/** xG created vs conceded per match (thin lines, 3-match rolling average dashed). */
export function XgTrendChart({ points, teams }: Props) {
  const data = points.map((p) => ({
    ...p,
    label: p.matchday ? `G${p.matchday}` : formatShortDate(p.kickoff_at),
    opponent: teams[String(p.opponent_id)],
  }))
  return (
    <div className="h-72 w-full" role="img" aria-label="Andamento xG creati e concessi per partita">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
          <CartesianGrid stroke={AXIS.stroke} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tick={AXIS.tick} stroke={AXIS.stroke} tickLine={false} />
          <YAxis tick={AXIS.tick} stroke={AXIS.stroke} tickLine={false} allowDecimals />
          <Tooltip
            cursor={{ stroke: 'var(--color-ink-faint)', strokeWidth: 1 }}
            content={({ active, payload }) => {
              const p = active ? payload?.[0]?.payload : undefined
              if (!p) return null
              return (
                <TooltipBox
                  title={`${p.label} · ${p.is_home ? 'vs' : '@'} ${p.opponent ? teamLabel(p.opponent) : '—'} (${p.gf}–${p.ga})`}
                  rows={[
                    { label: 'xG creati', value: formatNumber(p.xg), color: SERIES.one },
                    { label: 'xG concessi', value: formatNumber(p.xga), color: SERIES.two },
                    { label: 'Media 3 partite (creati)', value: formatNumber(p.xg_rolling) },
                    { label: 'Media 3 partite (concessi)', value: formatNumber(p.xga_rolling) },
                  ]}
                />
              )
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} iconType="plainline" formatter={(v: string) => <span style={{ color: legendText(v).color }}>{v}</span>} />
          <Line name="xG creati" dataKey="xg" stroke={SERIES.one} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={false} />
          <Line name="xG concessi" dataKey="xga" stroke={SERIES.two} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={false} />
          <Line name="Media creati (3)" dataKey="xg_rolling" stroke={SERIES.one} strokeWidth={1.5} strokeDasharray="4 3" dot={false} legendType="none" isAnimationActive={false} />
          <Line name="Media concessi (3)" dataKey="xga_rolling" stroke={SERIES.two} strokeWidth={1.5} strokeDasharray="4 3" dot={false} legendType="none" isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
