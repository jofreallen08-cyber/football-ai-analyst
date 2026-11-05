import { Link } from 'react-router'

import type { MatchSummary } from '../../api/types'
import { formatDateTime, STATUS_LABEL, teamLabel } from '../../lib/format'
import { SyntheticBadge } from './SyntheticBadge'

export function MatchRow({ match, showCompetition = false }: { match: MatchSummary; showCompetition?: boolean }) {
  const played = match.home_score !== null && match.away_score !== null
  return (
    <Link
      to={`/partite/${match.id}`}
      className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-lg px-3 py-2.5 text-sm hover:bg-navy-800"
    >
      <span className="truncate text-right font-medium">{teamLabel(match.home_team)}</span>
      <span className="flex min-w-16 flex-col items-center">
        {played ? (
          <span className="rounded-md bg-navy-700 px-2 py-0.5 font-bold tabular-nums">
            {match.home_score} – {match.away_score}
          </span>
        ) : (
          <span className="text-xs text-ink-muted">
            {match.status === 'scheduled' ? formatDateTime(match.kickoff_at) : STATUS_LABEL[match.status]}
          </span>
        )}
      </span>
      <span className="truncate font-medium">{teamLabel(match.away_team)}</span>
      {showCompetition && (
        <span className="col-span-3 flex items-center justify-center gap-2 text-[11px] text-ink-faint">
          {match.competition_name} · {match.season_label}
          {played && ` · ${formatDateTime(match.kickoff_at)}`}
          {match.is_synthetic && <SyntheticBadge />}
        </span>
      )}
    </Link>
  )
}
