# 03 — Database Schema Proposal (PostgreSQL)

Conventions: `bigint` identity PKs, `timestamptz` everywhere (UTC), `created_at`/`updated_at` on every table, snake_case. Nullable stat columns: **`NULL` = not available**, `0` = genuinely zero. All schema changes via Alembic.

## 1. Provenance & ingestion

| Table | Key columns | Purpose |
|---|---|---|
| `data_sources` | `id`, `key` (unique), `name`, `license_name`, `license_url`, `attribution_text`, `commercial_use_allowed` bool, `enabled` bool | Registered providers |
| `ingestion_runs` | `id`, `source_id` FK, `scope` jsonb (competition/season), `started_at`, `finished_at`, `status` (running/success/partial/failed), `records_upserted`, `records_rejected`, `error` | Audit trail of every import |
| `ingestion_issues` | `id`, `ingestion_run_id` FK, `entity_type`, `external_id`, `severity`, `message`, `payload` jsonb | Validation failures (never silently dropped) |
| `provider_cache` | `id`, `source_id` FK, `cache_key` (unique), `endpoint`, `params` jsonb, `response` jsonb, `etag`, `fetched_at`, `expires_at` | HTTP response cache |
| `rate_limit_state` | `source_id` PK, `window_start`, `requests_in_window`, `blocked_until` | Persisted quota tracking |
| `external_refs` | `id`, `source_id` FK, `entity_type`, `external_id`, `internal_id`; unique(`source_id`,`entity_type`,`external_id`) | Provider ID ↔ internal ID mapping |

Every fact table below also has: `source_id` FK, `fetched_at timestamptz`, `source_updated_at timestamptz NULL`.

## 2. Football domain

| Table | Key columns |
|---|---|
| `competitions` | `id`, `name`, `code`, `country`, `type` (league/cup/international), `gender`, `tier` |
| `seasons` | `id`, `competition_id` FK, `label` ("2025/26"), `start_date`, `end_date`, `is_current` |
| `teams` | `id`, `name`, `short_name`, `country`, `founded`, `crest_url` |
| `team_aliases` | `id`, `team_id` FK, `alias` (unique, case-insensitive) |
| `venues` | `id`, `name`, `city`, `country`, `capacity` |
| `players` | `id`, `full_name`, `known_as`, `birth_date`, `nationality`, `primary_position` |
| `squad_memberships` | `id`, `player_id`, `team_id`, `season_id`, `shirt_number`, `from_date`, `to_date` |
| `matches` | `id`, `season_id` FK, `matchday`, `stage`, `kickoff_at`, `venue_id`, `home_team_id`, `away_team_id`, `status` (scheduled/live/finished/postponed/cancelled), `home_score`, `away_score`, `home_score_ht`, `away_score_ht`, `neutral_venue` bool, `attendance`, `referee`; unique(`season_id`,`home_team_id`,`away_team_id`,`kickoff_at`) |
| `match_team_stats` | `id`, `match_id` FK, `team_id` FK, `is_home`, `xg`, `xga`, `shots`, `shots_on_target`, `possession_pct`, `corners`, `fouls`, `yellow_cards`, `red_cards`, `passes`, `pass_accuracy_pct`, `offsides`; unique(`match_id`,`team_id`) |
| `player_match_stats` | `id`, `match_id`, `player_id`, `team_id`, `minutes`, `started` bool, `position`, `goals`, `assists`, `shots`, `shots_on_target`, `xg`, `xa`, `key_passes`, `passes`, `pass_accuracy_pct`, `tackles`, `interceptions`, `yellow_cards`, `red_cards`, `rating` NULL |
| `lineups` | `id`, `match_id`, `team_id`, `formation` ("4-3-3"), `confirmed` bool, `announced_at` |
| `lineup_entries` | `id`, `lineup_id` FK, `player_id`, `role` (starter/substitute), `position`, `grid_x`, `grid_y`, `shirt_number` |
| `player_availability` | `id`, `player_id`, `team_id`, `type` (injury/suspension/international_duty/doubtful/other), `description`, `reported_at`, `expected_return` NULL, `source_url` NULL, `status` (active/resolved) |
| `match_events` (Phase 3+) | `id`, `match_id`, `team_id`, `player_id`, `minute`, `second`, `type` (shot/goal/card/sub…), `x`, `y`, `xg`, `outcome`, `payload` jsonb |

Indexes: `matches(season_id, kickoff_at)`, `matches(home_team_id, kickoff_at)`, `matches(away_team_id, kickoff_at)`, `player_match_stats(player_id, match_id)`, `player_availability(team_id, status)`.

Check constraints: scores ≥ 0; `possession_pct BETWEEN 0 AND 100`; `home_team_id <> away_team_id`; `minutes BETWEEN 0 AND 130`.

## 3. AI & analysis

| Table | Key columns | Purpose |
|---|---|---|
| `analysis_runs` | `id` (uuid), `match_id` FK, `status` (queued/running/completed/partial/failed), `data_hash`, `context_snapshot` jsonb, `requested_at`, `started_at`, `finished_at`, `error` | One orchestration execution |
| `agent_reports` | `id`, `analysis_run_id` FK, `agent` (match_analyst/statistics/team_intelligence/simulation/master), `status` (pending/running/completed/failed/skipped/cached), `prompt_version`, `model`, `cache_key`, `output` jsonb (validated `AgentReport`), `missing_information` jsonb, `confidence` (low/medium/high), `latency_ms`, `reused_from_report_id` NULL | Per-agent output |
| `final_reports` | `id`, `analysis_run_id` FK unique, `match_id`, `summary`, `key_findings` jsonb, `agreements` jsonb, `contradictions` jsonb, `missing_information` jsonb, `confidence`, `sources` jsonb, `disclaimer`, `created_at` | Master analyst output (Reports page) |
| `ai_cache` | `cache_key` PK, `agent`, `prompt_version`, `model`, `response` jsonb, `created_at`, `hit_count`, `last_hit_at` | Response reuse |
| `ai_usage` | `id`, `analysis_run_id` NULL, `agent`, `provider`, `model`, `input_tokens`, `output_tokens`, `cost_estimate`, `status`, `created_at` | Budget enforcement & Settings dashboard |

## 4. Simulation

| Table | Key columns |
|---|---|
| `simulation_runs` | `id` (uuid), `match_id` NULL (hypothetical fixtures allowed), `home_team_id`, `away_team_id`, `scenario` jsonb (availability changes, formations, venue), `assumptions` jsonb, `limitations` jsonb, `model_version`, `seed` bigint, `n_iterations`, `training_window` jsonb (date range, matches used), `results` jsonb (score distribution, summary metrics), `is_simulation` bool NOT NULL DEFAULT true CHECK (is_simulation), `created_at` |

## 5. Settings

| Table | Key columns |
|---|---|
| `app_settings` | `key` PK, `value` jsonb, `updated_at` — **non-secret** settings only (enabled competitions, budget limits, UI prefs). API keys live only in environment variables. |

## ER sketch

```
competitions 1─* seasons 1─* matches *─1 teams (home/away)
matches 1─* match_team_stats, player_match_stats, lineups 1─* lineup_entries, match_events
players 1─* squad_memberships *─1 teams ; players 1─* player_availability
matches 1─* analysis_runs 1─* agent_reports ; analysis_runs 1─1 final_reports
teams 1─* simulation_runs (home/away)
data_sources 1─* ingestion_runs 1─* ingestion_issues ; data_sources 1─* external_refs
```
