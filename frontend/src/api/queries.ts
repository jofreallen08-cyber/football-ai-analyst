import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiGet, apiPost, qs } from './client'
import type {
  Competition,
  MatchContext,
  MatchDetail,
  MatchSummary,
  Overview,
  Page,
  PlayerAnalytics,
  PlayerLeaders,
  Simulation,
  SimulationOptions,
  SimulationRequest,
  SimulationSummary,
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

export function useSimulationOptions(params: { match_id?: number; season_id?: number; home_team_id?: number; away_team_id?: number }) {
  const ready = params.match_id !== undefined || (params.season_id !== undefined && params.home_team_id !== undefined && params.away_team_id !== undefined && params.home_team_id !== params.away_team_id)
  return useQuery({
    queryKey: ['simulation-options', params],
    queryFn: ({ signal }) => apiGet<SimulationOptions>(`/simulations/options${qs({ ...params })}`, signal),
    enabled: ready,
  })
}

export function useSimulationHistory() {
  return useQuery({
    queryKey: ['simulations'],
    queryFn: ({ signal }) => apiGet<SimulationSummary[]>('/simulations?limit=10', signal),
  })
}

export function useSimulation(id: string | undefined) {
  return useQuery({
    queryKey: ['simulation', id],
    queryFn: ({ signal }) => apiGet<Simulation>(`/simulations/${id}`, signal),
    enabled: id !== undefined,
    staleTime: Infinity,
  })
}

export function useRunSimulation() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: SimulationRequest) => apiPost<Simulation>('/simulations', body),
    onSuccess: (sim) => {
      client.setQueryData(['simulation', sim.id], sim)
      void client.invalidateQueries({ queryKey: ['simulations'] })
    },
  })
}
