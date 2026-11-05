/** Convenience aliases over the types generated from the backend OpenAPI schema. */
import type { components } from './schema'

type S = components['schemas']

export type Competition = S['CompetitionOut']
export type Season = S['SeasonOut']
export type Source = S['SourceOut']
export type TeamRef = S['TeamRef']
export type Team = S['TeamOut']
export type MatchSummary = S['MatchOut']
export type MatchDetail = S['MatchDetail']
export type TeamStats = S['TeamStatsOut']
export type Lineup = S['LineupOut']
export type LineupEntry = S['LineupEntryOut']
export type Player = S['PlayerOut']
export type Overview = S['OverviewOut']
export type Standings = S['StandingsOut']
export type StandingRow = S['StandingRow']
export type TeamAnalytics = S['TeamAnalytics']
export type FormSummary = S['FormSummary']
export type SplitSummary = S['SplitSummary']
export type MetricSummary = S['MetricSummary']
export type SeriesPoint = S['SeriesPoint']
export type PlayerLeaders = S['PlayerLeadersOut']
export type PlayerLeader = S['PlayerLeader']
export type PlayerAnalytics = S['PlayerAnalytics']
export type MatchContext = S['MatchContext']
export type TeamContext = S['TeamContext']
export type AvailabilityItem = S['AvailabilityItem']

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}
