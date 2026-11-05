import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { apiGet, qs } from './client'
import type {
  Competition,
  MatchContext,
  MatchDetail,
  MatchSummary,
  Overview,
  Page,
  PlayerAnalytics,
  PlayerLeaders,
  Standings,
  Team,
  TeamAnalytics,
} from './types'

export function useCompetitions() {
  return useQuery({
    queryKey: ['competitions'],
    queryFn: ({ signal }) => apiGet<Competition[]>('/competitions', signal),
    staleTime: 5 * 60_000,
  })
}

export function useOverview() {
  return useQuery({
    queryKey: ['overview'],
    queryFn: ({ signal }) => apiGet<Overview>('/overview', signal),
  })
}

export interface MatchFilters {
  season_id?: number
  team_id?: number
  status?: string
  order?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export function useMatches(filters: MatchFilters, enabled = true) {
  return useQuery({
    queryKey: ['matches', filters],
    queryFn: ({ signal }) => apiGet<Page<MatchSummary>>(`/matches${qs({ ...filters })}`, signal),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useMatch(id: number | undefined) {
  return useQuery({
    queryKey: ['match', id],
    queryFn: ({ signal }) => apiGet<MatchDetail>(`/matches/${id}`, signal),
    enabled: id !== undefined,
  })
}

export function useMatchContext(id: number | undefined) {
  return useQuery({
    queryKey: ['match-context', id],
    queryFn: ({ signal }) => apiGet<MatchContext>(`/matches/${id}/context`, signal),
    enabled: id !== undefined,
  })
}

export function useTeams(seasonId: number | undefined) {
  return useQuery({
    queryKey: ['teams', seasonId],
    queryFn: ({ signal }) => apiGet<Team[]>(`/teams${qs({ season_id: seasonId })}`, signal),
    enabled: seasonId !== undefined,
  })
}

export function useStandings(seasonId: number | undefined) {
  return useQuery({
    queryKey: ['standings', seasonId],
    queryFn: ({ signal }) => apiGet<Standings>(`/seasons/${seasonId}/standings`, signal),
    enabled: seasonId !== undefined,
  })
}

export function useTeamAnalytics(teamId: number | undefined, seasonId: number | undefined) {
  return useQuery({
    queryKey: ['team-analytics', teamId, seasonId],
    queryFn: ({ signal }) =>
      apiGet<TeamAnalytics>(`/teams/${teamId}/analytics${qs({ season_id: seasonId })}`, signal),
    enabled: teamId !== undefined && seasonId !== undefined,
  })
}

export function usePlayerLeaders(
  seasonId: number | undefined,
  params: { metric: string; per90: boolean; team_id?: number; limit?: number },
) {
  return useQuery({
    queryKey: ['player-leaders', seasonId, params],
    queryFn: ({ signal }) =>
      apiGet<PlayerLeaders>(`/seasons/${seasonId}/player-leaders${qs({ ...params })}`, signal),
    enabled: seasonId !== undefined,
    placeholderData: keepPreviousData,
  })
}

export function usePlayerAnalytics(playerId: number | undefined, seasonId: number | undefined) {
  return useQuery({
    queryKey: ['player-analytics', playerId, seasonId],
    queryFn: ({ signal }) =>
      apiGet<PlayerAnalytics>(`/players/${playerId}/analytics${qs({ season_id: seasonId })}`, signal),
    enabled: playerId !== undefined && seasonId !== undefined,
  })
}
