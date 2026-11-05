import type { LineupEntry } from '../../api/types'

interface Props {
  home?: { entries: LineupEntry[]; formation: string | null; label: string }
  away?: { entries: LineupEntry[]; formation: string | null; label: string }
}

const W = 680
const H = 440
const PAD = 20

function surname(name: string) {
  const parts = name.split(' ')
  return parts.length > 1 ? parts.slice(1).join(' ') : name
}

/**
 * Horizontal pitch: home team attacks left→right on the left half, away team mirrored.
 * Player grid coordinates (0–100 along own half → opponent goal) come from the data source.
 */
export function Pitch({ home, away }: Props) {
  const fieldW = W - PAD * 2
  const fieldH = H - PAD * 2
  const place = (e: LineupEntry, side: 'home' | 'away') => {
    const gx = (e.grid_x ?? 50) / 100
    const gy = (e.grid_y ?? 50) / 100
    const x = side === 'home' ? PAD + gx * (fieldW / 2) : W - PAD - gx * (fieldW / 2)
    const y = side === 'home' ? PAD + (1 - gy) * fieldH : PAD + gy * fieldH
    return { x, y }
  }
  const renderTeam = (team: Props['home'], side: 'home' | 'away') =>
    team?.entries
      .filter((e) => e.role === 'starter' && e.grid_x !== null)
      .map((e) => {
        const { x, y } = place(e, side)
        return (
          <g key={`${side}-${e.player_id}`}>
            <title>{`${e.player_name} · ${e.position ?? ''}`}</title>
            <circle cx={x} cy={y} r={13} fill={side === 'home' ? 'var(--color-series-1)' : 'var(--color-series-2)'} stroke="var(--color-navy-950)" strokeWidth={2} />
            <text x={x} y={y + 4} textAnchor="middle" fontSize={11} fontWeight={700} fill="#fff">
              {e.shirt_number ?? ''}
            </text>
            <text x={x} y={y + 27} textAnchor="middle" fontSize={10} fill="var(--color-ink)">
              {surname(e.player_name)}
            </text>
          </g>
        )
      })

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Formazioni in campo">
      <rect x={0} y={0} width={W} height={H} rx={10} fill="#0b3b2e" />
      {Array.from({ length: 8 }, (_, i) => (
        <rect key={i} x={PAD + (i * fieldW) / 8} y={PAD} width={fieldW / 8} height={fieldH} fill={i % 2 ? '#0d4535' : '#0b3b2e'} />
      ))}
      <g fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth={1.5}>
        <rect x={PAD} y={PAD} width={fieldW} height={fieldH} />
        <line x1={W / 2} y1={PAD} x2={W / 2} y2={H - PAD} />
        <circle cx={W / 2} cy={H / 2} r={45} />
        <rect x={PAD} y={H / 2 - 95} width={85} height={190} />
        <rect x={W - PAD - 85} y={H / 2 - 95} width={85} height={190} />
        <rect x={PAD} y={H / 2 - 40} width={30} height={80} />
        <rect x={W - PAD - 30} y={H / 2 - 40} width={30} height={80} />
      </g>
      {renderTeam(home, 'home')}
      {renderTeam(away, 'away')}
    </svg>
  )
}
