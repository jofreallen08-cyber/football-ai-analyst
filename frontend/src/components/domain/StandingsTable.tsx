import type { Standings } from '../../api/types'
import { FormStrip } from './ResultBadge'

export function StandingsTable({ data, highlight, onSelect }: { data: Standings; highlight?: number; onSelect?: (teamId: number) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm tabular-nums">
        <caption className="sr-only">Classifica {data.season.competition_name} {data.season.label}</caption>
        <thead className="text-xs text-ink-faint">
          <tr className="border-b border-line">
            <th className="py-2 pr-2 text-left font-medium">#</th>
            <th className="py-2 text-left font-medium">Squadra</th>
            <th className="px-1.5 py-2 font-medium" title="Partite giocate">G</th>
            <th className="px-1.5 py-2 font-medium" title="Differenza reti">DR</th>
            <th className="px-1.5 py-2 font-medium" title="Punti">Pt</th>
            <th className="hidden py-2 pl-2 text-left font-medium sm:table-cell">Forma</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r) => {
            const team = data.teams[String(r.team_id)]
            const active = r.team_id === highlight
            return (
              <tr key={r.team_id} className={`border-b border-line/50 ${active ? 'bg-navy-700/60' : ''}`}>
                <td className="py-1.5 pr-2 text-ink-faint">{r.position}</td>
                <td className="max-w-40 truncate py-1.5">
                  {onSelect ? (
                    <button type="button" className="truncate text-left hover:text-accent" onClick={() => onSelect(r.team_id)}>
                      {team?.short_name ?? team?.name}
                    </button>
                  ) : (team?.short_name ?? team?.name)}
                </td>
                <td className="px-1.5 py-1.5 text-center">{r.played}</td>
                <td className="px-1.5 py-1.5 text-center">{r.goal_difference > 0 ? `+${r.goal_difference}` : r.goal_difference}</td>
                <td className="px-1.5 py-1.5 text-center font-semibold">{r.points}</td>
                <td className="hidden py-1.5 pl-2 sm:table-cell"><FormStrip results={r.form} small /></td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="mt-2 text-[11px] text-ink-faint">{data.tie_break_note}</p>
    </div>
  )
}
