import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { SimulationOutcome } from '../../api/types'
import { formatPercent } from '../../lib/format'
import { AXIS, legendText, SERIES } from './chartTheme'
import { TooltipBox } from './ChartTooltip'

export function GoalsDistributionChart({ outcome, homeLabel, awayLabel }: { outcome: SimulationOutcome; homeLabel: string; awayLabel: string }) {
  const data = outcome.goals_distribution_home.map((h, i) => ({
    goals: i === outcome.goals_distribution_home.length - 1 ? `${i}+` : String(i),
    home: h * 100,
    away: (outcome.goals_distribution_away[i] ?? 0) * 100,
  }))
  return (
    <div className="h-64" role="img" aria-label="Distribuzione simulata dei gol per squadra">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }} barGap={2}>
          <CartesianGrid stroke={AXIS.stroke} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="goals" tick={AXIS.tick} stroke={AXIS.stroke} tickLine={false} label={{ value: 'Gol segnati', position: 'insideBottom', offset: -2, fill: 'var(--color-ink-faint)', fontSize: 11 }} height={36} />
          <YAxis tick={AXIS.tick} stroke={AXIS.stroke} tickLine={false} unit="%" />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            content={({ active, payload }) => {
              const d = active ? payload?.[0]?.payload : undefined
              return d ? (
                <TooltipBox title={`${d.goals} gol`} rows={[
                  { label: homeLabel, value: formatPercent(d.home, 1), color: SERIES.one },
                  { label: awayLabel, value: formatPercent(d.away, 1), color: SERIES.two },
                ]} />
              ) : null
            }}
          />
          <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12 }} formatter={(v: string) => <span style={{ color: legendText(v).color }}>{v}</span>} />
          <Bar name={homeLabel} dataKey="home" fill={SERIES.one} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          <Bar name={awayLabel} dataKey="away" fill={SERIES.two} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
