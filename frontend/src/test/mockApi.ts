import { vi } from 'vitest'

/* Minimal fixtures shaped like the backend responses (see api/schema.d.ts). */
const team = (id: number, name: string) => ({ id, name, short_name: name })
const H = team(1, 'Aquile')
const A = team(2, 'Borgo')

export const health = { status: 'ok', version: '0.1.0', environment: 'test', database: 'ok', ai_provider: 'mock' }

export const competitions = [
  { id: 1, name: 'Serie A', code: 'SA', country: 'Italia', type: 'league', source: 'openfootball', is_synthetic: false,
    seasons: [{ id: 10, label: '2025/26', start_date: null, end_date: null, is_current: false }] },
  { id: 2, name: 'Lega Dimostrativa', code: 'DEMO', country: 'Demo', type: 'league', source: 'local_sample', is_synthetic: true,
    seasons: [{ id: 20, label: '2026/27', start_date: null, end_date: null, is_current: true }] },
]

const match = (id: number, status: string, hs: number | null, as: number | null, synthetic = false) => ({
  id, season_id: synthetic ? 20 : 10, competition_code: synthetic ? 'DEMO' : 'SA',
  competition_name: synthetic ? 'Lega Dimostrativa' : 'Serie A', season_label: '2025/26', matchday: 1,
  kickoff_at: '2026-01-10T17:00:00Z', status, home_team: H, away_team: A, home_score: hs, away_score: as,
  home_score_ht: null, away_score_ht: null, has_team_stats: synthetic, source: synthetic ? 'local_sample' : 'openfootball',
  is_synthetic: synthetic,
})

const form = (results: string[]) => ({
  sample_size: results.length, wins: 1, draws: 0, losses: 0, points: 3, ppg: 3, goals_for: 2, goals_against: 0,
  xg_for: null, xg_against: null,
  matches: results.map((r, i) => ({ match_id: i, kickoff_at: '2026-01-01T00:00:00Z', opponent_id: 2, is_home: true, gf: 2, ga: 0, result: r, xg: null, xga: null })),
})
const split = { played: 1, wins: 1, draws: 0, losses: 0, ppg: 3, goals_for_pg: 2, goals_against_pg: 0, xg_pg: null, xga_pg: null, xg_coverage: 0 }

const teamCtx = (t: typeof H) => ({
  team: t, position: 1, points: 3, form_last5: form(['W']), venue_form_last5: form(['W']), splits: { home: split, away: split, all: split },
  stats: { matches: 1, metrics: [], missing: [] }, availability: [], last_lineup: null, formation_usage: {},
})

const agentReport = {
  agent: 'match_analyst', status: 'completed', headline: 'Casa in forma', confidence: 'medium',
  findings: [{ claim: 'Aquile ha 3 punti nelle ultime partite', evidence_keys: ['home.form5.points'], strength: 'medium' }],
  missing_information: ['Formazioni non disponibili dalla fonte'], limitations: [], sources: ['openfootball'],
  provider: 'mock', model: 'mock-offline-v1', prompt_version: 'v1', rejected_findings: 0, is_simulation: false, error: null,
}

const analysis = {
  id: 'run-1', match: match(100, 'finished', 2, 0), status: 'completed', reused: false, provider: 'mock', model: 'mock-offline-v1',
  requested_at: '2026-11-05T10:00:00Z', started_at: '2026-11-05T10:00:01Z', finished_at: '2026-11-05T10:00:05Z', error: null,
  agents: [
    { agent: 'match_analyst', title: 'Match Analyst', status: 'completed', report: agentReport },
    { agent: 'statistics', title: 'Statistics AI', status: 'skipped', report: { ...agentReport, agent: 'statistics', status: 'skipped', headline: 'Analisi non eseguita: dati insufficienti', findings: [] } },
  ],
  final_report: {
    id: 1, analysis_run_id: 'run-1', match: match(100, 'finished', 2, 0), created_at: '2026-11-05T10:00:05Z', generated_by: 'ai',
    provider: 'mock', model: 'mock-offline-v1', summary: 'Sintesi di prova.',
    key_findings: [{ agent: 'match_analyst', finding: 'Aquile ha 3 punti nelle ultime partite' }],
    agreements: [], contradictions: [{ description: 'Classifica e simulazione divergono', agents: ['match_analyst'], assessment: 'Campione ridotto' }],
    detected_contradictions: [], missing_information: ['Formazioni non disponibili dalla fonte'], confidence: 'medium',
    agent_statuses: { match_analyst: 'completed', statistics: 'skipped' }, sources: [{ name: 'openfootball', attribution_text: 'Risultati: openfootball' }],
    data_as_of: '2026-01-10T17:00:00Z', disclaimer: 'Report a scopo educativo. Nessun consiglio di scommessa.',
  },
}

export const fixtures: Record<string, unknown> = {
  '/health': health,
  '/competitions': competitions,
  '/overview': {
    totals: { competitions: 2, matches: 2, finished: 1, teams: 2, players: 0 },
    recent: [match(100, 'finished', 2, 0)],
    upcoming: [match(101, 'scheduled', null, null)],
    sources: [{ key: 'openfootball', name: 'openfootball', license_name: 'CC0', license_url: null, attribution_text: 'Risultati: openfootball', commercial_use_allowed: true, is_synthetic: false }],
  },
  '/matches': { items: [match(100, 'finished', 2, 0), match(101, 'scheduled', null, null)], total: 2, limit: 20, offset: 0 },
  '/teams': [ { ...H, country: null, founded: null, source: 'openfootball', is_synthetic: false }, { ...A, country: null, founded: null, source: 'openfootball', is_synthetic: false } ],
  '/matches/100': {
    ...match(100, 'finished', 2, 0), attendance: null, referee: null, team_stats: [], lineups: [],
    provenance: { source: 'openfootball', is_synthetic: false, fetched_at: '2026-11-05T00:00:00Z', source_updated_at: null },
    attribution: 'Risultati e calendari: openfootball',
  },
  '/matches/100/context': {
    match: match(100, 'finished', 2, 0), as_of: '2026-01-10T17:00:00Z', home: teamCtx(H), away: teamCtx(A),
    head_to_head: { sample_size: 0, team_a_wins: 0, draws: 0, team_b_wins: 0, team_a_goals: 0, team_b_goals: 0, matches: [] },
    teams: { 1: H, 2: A }, sources: [], capabilities: { xg: false, lineups: false, player_stats: false, availability: false },
    missing: ['xG e statistiche di squadra non disponibili dalla fonte'],
  },
  '/seasons/10/standings': {
    season: { id: 10, label: '2025/26', competition_id: 1, competition_name: 'Serie A', competition_code: 'SA', is_synthetic: false },
    teams: { 1: H, 2: A }, tie_break_note: 'Nota parità',
    rows: [
      { position: 1, team_id: 1, played: 1, wins: 1, draws: 0, losses: 0, goals_for: 2, goals_against: 0, goal_difference: 2, points: 3, form: ['W'] },
      { position: 2, team_id: 2, played: 1, wins: 0, draws: 0, losses: 1, goals_for: 0, goals_against: 2, goal_difference: -2, points: 0, form: ['L'] },
    ],
  },
  '/teams/1/analytics': {
    team: H, season: { id: 10, label: '2025/26', competition_id: 1, competition_name: 'Serie A', competition_code: 'SA', is_synthetic: false },
    teams: { 1: H, 2: A }, position: 1, form_last5: form(['W']), form_last10: form(['W']), splits: { home: split, away: split, all: split },
    stats: { matches: 1, metrics: [], missing: ['xG: non disponibile dalla fonte'] }, xg_series: [], has_xg: false,
    missing: ['xG non disponibile per questa competizione'],
  },
  '/simulations': [],
  '/simulations/options': {
    season_id: 20, home_team: H, away_team: A, home_usual_formation: '4-3-3', away_usual_formation: '4-4-2',
    formations: ['4-3-3', '4-4-2', '5-4-1'], as_of: '2026-01-10T17:00:00Z',
    home_players: [{ player_id: 7, name: 'Mario Bomber', position: 'FWD', minutes: 900, minutes_share: 0.9, xg_share: 0.4, reported_unavailable: true }],
    away_players: [],
  },
  'POST /simulations': {
    id: 'sim-1', is_simulation: true, label: 'SIMULAZIONE — scenario ipotetico, non un risultato reale né garantito',
    created_at: '2026-11-05T10:00:00Z', match_id: 100, season_id: 20, home_team: H, away_team: A, venue: 'home',
    model_version: 'poisson-v1', seed: 2026, n_iterations: 20000,
    training_window: { matches_used: 50, start: '2026-08-22T00:00:00Z', end: '2026-10-31T00:00:00Z', as_of: '2026-11-07T00:00:00Z', uses_xg: true, home_matches: 10, away_matches: 10 },
    strengths: { home: { attack: 1.2, defence: 0.9 }, away: { attack: 0.9, defence: 1.1 } },
    baseline: { expected_goals_home: 1.8, expected_goals_away: 1.0, home_win_share: 0.55, draw_share: 0.24, away_win_share: 0.21, mean_goals_home: 1.8, mean_goals_away: 1, home_clean_sheet_share: 0.37, away_clean_sheet_share: 0.17, both_score_share: 0.52, top_scorelines: [['1-0', 0.12], ['2-1', 0.1]], goals_distribution_home: [0.17, 0.3, 0.27, 0.16, 0.07, 0.02, 0.01], goals_distribution_away: [0.37, 0.37, 0.18, 0.06, 0.02, 0, 0] },
    scenario: null, scenario_description: {}, assumptions: ['Modello poisson-v1: forze calcolate su 50 partite.'],
    limitations: ['Le percentuali sono frequenze sulle simulazioni eseguite.'], is_synthetic_data: true,
  },
  '/agents': [
    { name: 'match_analyst', title: 'Match Analyst', description: 'Forma e contesto.', data_needs: ['risultati'], is_simulation: false },
    { name: 'master', title: 'Master Analyst', description: 'Sintesi finale.', data_needs: ['report'], is_simulation: false },
  ],
  '/ai/usage': { provider: 'mock', model: 'mock-offline-v1', effort: 'medium', billable: false, today_calls: 3, today_tokens: 0, by_agent: {}, limits: { daily_calls: 100, daily_tokens: 500000, calls_per_analysis: 5 }, cache_entries: 4, cache_hits: 2 },
  'POST /analyses': analysis,
  '/analyses/run-1': analysis,
  '/analyses': [{ id: 'run-1', match: match(100, 'finished', 2, 0), status: 'completed', requested_at: '2026-11-05T10:00:00Z', finished_at: '2026-11-05T10:00:05Z', confidence: 'medium', summary: 'Sintesi di prova.', generated_by: 'ai' }],
  '/seasons/10/player-leaders': { season: {}, metric: 'goals', per90: false, min_minutes_per90: 270, items: [] },
}

/** Install a fetch mock that answers by API path; `overrides` replace or fail specific paths. */
export function mockApi(overrides: Record<string, unknown | Error> = {}) {
  const table = { ...fixtures, ...overrides }
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    const path = url.pathname.replace(/^\/api\/v1/, '')
    const method = init?.method ?? 'GET'
    const body = method === 'GET' ? table[path] : table[`${method} ${path}`]
    if (body instanceof Error) throw body
    if (body === undefined) {
      return new Response(JSON.stringify({ title: 'Risorsa non trovata', status: 404, detail: 'Non trovato' }), { status: 404 })
    }
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}
