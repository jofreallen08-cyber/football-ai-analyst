import { useSearchParams } from 'react-router'

import { useCompetitions } from '../api/queries'
import type { Competition, Season } from '../api/types'

const DEFAULT_COMPETITION = 'SA'

/** Season selection persisted in the URL (`?stagione=<id>`), defaulting to Serie A. */
export function useSeasonSelection(fallbackSeasonId?: number) {
  const competitions = useCompetitions()
  const [params, setParams] = useSearchParams()
  const raw = params.get('stagione')

  const selected = ((): { competition?: Competition; season?: Season } => {
    const list = competitions.data ?? []
    for (const c of list) {
      const s = c.seasons.find((x) => String(x.id) === raw)
      if (s) return { competition: c, season: s }
    }
    const target = raw ?? (fallbackSeasonId !== undefined ? String(fallbackSeasonId) : null)
    for (const c of list) {
      const s = c.seasons.find((x) => String(x.id) === target)
      if (s) return { competition: c, season: s }
    }
    const fallback = list.find((c) => c.code === DEFAULT_COMPETITION) ?? list[0]
    return { competition: fallback, season: fallback?.seasons[0] }
  })()

  const setSeason = (seasonId: number) => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('stagione', String(seasonId))
        next.delete('squadra')
        next.delete('giocatore')
        next.delete('pagina')
        return next
      },
      { replace: true },
    )
  }

  return { ...selected, competitions, setSeason }
}

/** Read/write a numeric search param. */
export function useNumberParam(name: string): [number | undefined, (v: number | undefined) => void] {
  const [params, setParams] = useSearchParams()
  const raw = params.get(name)
  const value = raw && /^\d+$/.test(raw) ? Number(raw) : undefined
  const set = (v: number | undefined) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (v === undefined) next.delete(name)
        else next.set(name, String(v))
        return next
      },
      { replace: true },
    )
  return [value, set]
}
