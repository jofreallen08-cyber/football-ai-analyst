# 01 — Technical Architecture

## 1. Guiding principles

1. **Facts first, language second.** Every number shown to the user is computed deterministically in Python (Pandas/NumPy) from stored, attributed data. The LLM interprets pre-computed features; it never produces statistics itself.
2. **Provenance everywhere.** Each stored fact carries `source`, `fetched_at` and (where known) `source_updated_at`. Missing data is stored as `NULL` and reported as *unavailable* — never imputed silently, never invented.
3. **No wagering.** No odds, bookmaker data, stakes, "value", tips or real-money predictions. Odds columns present in some free datasets are dropped at ingestion. Simulations are labelled *SIMULATED* end to end.
4. **Cheap by default.** AI calls are cached, budgeted and skipped when inputs haven't changed.
5. **Small, testable modules** with explicit interfaces (Python `Protocol`s) so providers, LLM vendors and agents can be swapped independently.

## 2. System overview

```
┌──────────────────────────── Frontend (React + TS + Tailwind) ────────────────────────────┐
│ Overview · Match Center · Team · Player · AI Agents · Simulation Lab · Reports · Settings │
│        TanStack Query  ──►  typed API client (generated from OpenAPI)                     │
└───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                            │ HTTPS / JSON (no secrets in the browser)
┌───────────────────────────────────────────▼──────────────────────────────────────────────┐
│                                FastAPI backend (/api/v1)                                  │
│  routers ─► services ─► repositories (SQLAlchemy 2.0) ─► PostgreSQL                       │
│                                                                                           │
│  ┌─────────────── Data layer ───────────────┐   ┌──────────── AI layer ─────────────────┐ │
│  │ ProviderRegistry                          │   │ Orchestrator                          │ │
│  │  ├ LocalSampleProvider (CSV/JSON)         │   │  ├ MatchAnalystAgent                  │ │
│  │  ├ OpenFootballProvider (CC0 fixtures)    │   │  ├ StatisticsAgent                    │ │
│  │  ├ StatsBombOpenProvider (events, xG)     │   │  ├ TeamIntelligenceAgent              │ │
│  │  └ FootballDataOrgProvider (free tier)    │   │  ├ SimulationAgent ─► SimulationEngine│ │
│  │ RateLimiter · ResponseCache · Validator   │   │  └ MasterAnalystAgent                 │ │
│  │ Normalizer ─► IngestionService            │   │ LLMProvider (Anthropic | Mock | …)    │ │
│  └───────────────────────────────────────────┘   │ PromptRegistry · AICache · Budget     │ │
│                                                  └───────────────────────────────────────┘ │
│  Feature builders (Pandas): form, home/away splits, xG trends, player aggregates          │
│  Background runner (asyncio tasks + analysis_runs status table)                           │
│  Structured logging (JSON) · Settings (pydantic-settings, env vars)                       │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Backend layers

| Layer | Responsibility | Rules |
|---|---|---|
| `api/` (routers) | HTTP, request validation, response models | Thin. No business logic. Pydantic v2 schemas for every input/output. |
| `services/` | Use-cases (ingest competition, analyse match, run simulation) | Transaction boundaries live here. |
| `repositories/` | Database access | Only place that touches SQLAlchemy sessions. |
| `providers/` | External/local data sources | Implement `DataProvider` protocol, declare capabilities and license. |
| `features/` | Deterministic analytics (Pandas/NumPy) | Pure functions, fully unit-tested, return values + `missing` lists. |
| `agents/` | Five AI agents | Each: `build_context()` → `run()` → validated `AgentReport`. |
| `orchestration/` | Workflow, caching, budget, persistence | Single entry point `Orchestrator.analyse_match()`. |
| `simulation/` | Monte Carlo engine | Seeded, versioned, reproducible. |
| `core/` | Config, logging, errors, DB session | |

## 4. Data provider architecture

```python
class DataProvider(Protocol):
    key: str                       # "local_sample", "football_data_org", ...
    license: ProviderLicense       # name, url, attribution text, commercial_use flag
    capabilities: set[Capability]  # COMPETITIONS, FIXTURES, RESULTS, TEAM_STATS,
                                   # PLAYER_STATS, XG, LINEUPS, INJURIES, EVENTS
    rate_limit: RateLimitPolicy    # e.g. 10 req / 60 s

    async def list_competitions(self) -> list[RawCompetition]: ...
    async def get_matches(self, competition, season) -> list[RawMatch]: ...
    async def get_match_detail(self, external_id) -> RawMatchDetail: ...
    # optional methods raise CapabilityNotSupported
```

Pipeline: **fetch → cache → validate → normalise → upsert → log ingestion run**.

* **ResponseCache**: keyed by `(provider, endpoint, params_hash)`, TTL per endpoint (finished matches: ~immutable; fixtures: hours; lineups: minutes near kick-off). Stored in Postgres (`provider_cache`), honours ETag/Last-Modified when the provider supports them.
* **RateLimiter**: token bucket per provider, persisted counters so restarts don't reset quotas; exponential backoff with jitter on 429/5xx; circuit breaker after repeated failures.
* **Validator**: Pydantic raw models per provider + domain checks (score ≥ 0, possession 0–100 and both sides sum ≈ 100, kick-off timezone-aware, team ids resolvable). Invalid records go to `ingestion_issues`, never silently dropped.
* **Normaliser / entity resolution**: provider IDs map to internal IDs via `external_refs`; team name aliases resolved through `team_aliases`.
* **Licensing guard**: each provider declares license + attribution; UI shows attribution next to data; providers marked non-commercial are flagged in Settings.

### Initial providers (free / open)

| Provider | Data | Access | Notes |
|---|---|---|---|
| LocalSampleProvider | Curated sample leagues, matches, team & player stats | Bundled files | Default; drives tests and demo |
| OpenFootball (football.json) | Fixtures & results, many leagues | GitHub raw, CC0 | No advanced stats |
| StatsBomb Open Data | Event data incl. shot xG, lineups | GitHub raw, free w/ attribution, non-commercial terms | Limited competitions/seasons |
| football-data.org (free tier) | Competitions, fixtures, results, standings | API key, 10 req/min | Host currently blocked in sandbox |

(football-data.co.uk CSVs contain bookmaker odds; if ever used, odds columns are discarded at ingestion.)

## 5. AI layer

* **LLMProvider protocol** — `complete(system, messages, json_schema, max_tokens) -> LLMResult(text, parsed, usage)`. Implementations: `AnthropicProvider` (default, model configurable via env), `MockLLMProvider` (deterministic, offline). Others can be added without touching agents.
* **PromptRegistry** — prompts live in versioned files `prompts/<agent>/v1.md`; prompt version is part of the cache key and stored with each report.
* **Structured output** — every agent returns JSON validated against a Pydantic `AgentReport` schema; one repair retry on validation failure, then the report is marked `failed` (no fabricated fallback).
* **AICache** — key = `sha256(agent, prompt_version, model, canonical_json(context))`. Same inputs → reuse stored report, zero API calls.
* **Budget guard** — env-configured limits: max calls per analysis, max tokens per call, daily call/token cap. Enforced before each call; every call logged in `ai_usage`.
* **Grounding rule** — agents receive only the context bundle; prompts instruct them to cite feature keys they used and to list missing information explicitly. Post-validation rejects reports that cite numbers not present in the context.

## 6. Orchestration workflow

```
POST /api/v1/analyses {match_id}
  1. create analysis_run (status=queued) → return run id (202)
  2. DataSnapshotService: load verified data for match → ContextBundle
       (+ data_hash, sources, timestamps, missing-fields list)
  3. if a completed run exists with same data_hash & prompt versions → reuse, done
  4. run agents 1–4 concurrently (asyncio.gather, per-agent timeout)
       each: AICache hit? → reuse : budget check → LLM call → validate → store
  5. MasterAnalyst receives the 4 reports + deterministic comparison
       (contradiction detector: e.g. form says "strong" vs stats "declining xG")
  6. FinalReport (summary, agreements, contradictions, missing info,
       confidence, sources, disclaimers) → saved
  7. analysis_run status=completed | partial | failed
GET /api/v1/analyses/{id}  → frontend polls; agent status indicators per agent
```

A failing agent does not fail the run: the master report is produced with that agent marked *unavailable* and the run status set to `partial`.

## 7. Simulation engine

* Team attack/defence strengths estimated from historical goals and (where available) xG, with time-decay weighting and home-advantage term (Poisson / Dixon–Coles style).
* Monte Carlo with explicit `seed` (NumPy `Generator(PCG64)`), `n_iterations`, `model_version` → identical inputs reproduce identical outputs.
* Scenario modifiers are **explicit, user-visible assumptions**: player unavailable (removes the player's share of team xG/xGA contribution, bounded), formation change (configurable multiplier with stated rationale), venue swap.
* Output: distribution of simulated scorelines and summary metrics, assumptions, limitations, sample sizes. Every response carries `is_simulation: true`; UI renders a persistent *SIMULATION — not a real result* banner. No odds conversion.

## 8. Frontend architecture

* Vite + React 18 + TypeScript (strict) + Tailwind CSS; React Router; TanStack Query for server state; Recharts for charts; custom SVG pitch component for formations/shot maps.
* Typed API client generated from FastAPI's OpenAPI schema (`openapi-typescript`) — no hand-written drift.
* Design tokens (dark navy palette, spacing, typography) in Tailwind config; shared components: `Card`, `StatTile`, `AgentStatusBadge`, `SourceAttribution`, `SimulationBanner`, `EmptyState`, `ErrorState`, `Skeleton`.
* No secrets in the bundle: the frontend only knows the backend base URL.

## 9. Cross-cutting concerns

| Concern | Approach |
|---|---|
| Config & secrets | `pydantic-settings`; `.env` (git-ignored) + `.env.example`; keys never returned by API |
| Logging | `structlog` JSON logs with request id, provider, agent, run id; secrets redacted |
| Errors | Typed domain exceptions → consistent problem+json responses |
| Input validation | Pydantic on all endpoints; ID/enum/range checks; pagination limits |
| Security | CORS allowlist, request size limits, basic API rate limiting; optional single-admin auth for Settings (Phase 7) |
| Testing | Pytest (unit, repository tests on Postgres, API tests with httpx), provider tests with recorded fixtures, Vitest + Testing Library on frontend, Playwright smoke tests |
| Migrations | Alembic |
| Quality gates | ruff, mypy (strict on core packages), eslint, tsc, prettier; CI via GitHub Actions |
| Containers | `docker-compose.yml` with `db`, `backend`, `frontend` |
