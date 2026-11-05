import type { Competition } from '../../api/types'
import { Select } from '../ui/Select'

interface Props {
  competitions: Competition[]
  seasonId: number | undefined
  onChange: (seasonId: number) => void
}

export function SeasonSelect({ competitions, seasonId, onChange }: Props) {
  return (
    <Select label="Competizione e stagione" value={String(seasonId ?? '')} onChange={(v) => onChange(Number(v))}>
      {competitions.map((c) => (
        <optgroup key={c.id} label={c.is_synthetic ? `${c.name} (dati sintetici)` : c.name}>
          {c.seasons.map((s) => (
            <option key={s.id} value={s.id}>
              {c.name} {s.label}
              {c.is_synthetic ? ' — sintetico' : ''}
            </option>
          ))}
        </optgroup>
      ))}
    </Select>
  )
}
