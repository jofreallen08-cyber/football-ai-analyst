# 05 — Development Roadmap

Each phase ends with passing tests, updated docs and a demo-able result. Approval checkpoint between phases.

| Phase | Name | Scope | Exit criteria |
|---|---|---|---|
| **0** ✅ | Planning | Architecture, structure, schema, agent specs, roadmap | Approved by product owner |
| **1** ✅ | Foundation | Monorepo skeleton, FastAPI app + health endpoint, config/logging, SQLAlchemy + Alembic, core domain tables, Docker Compose, CI, frontend shell (Vite/Tailwind, dark layout, sidebar with 8 routes, placeholder pages, loading/error components) | `pytest` + `pnpm test` green; app boots locally; CI passes |
| **2** | Data layer v1 | `DataProvider` protocol, registry, cache, rate limiter, validator, normaliser; `LocalSampleProvider` with bundled sample dataset (2–3 leagues, 1–2 seasons); ingestion CLI + `ingestion_runs`; read APIs: competitions, seasons, matches, teams, players | Sample data ingested reproducibly; invalid rows logged in `ingestion_issues`; API tested |
| **3** | Analytics & dashboard data pages | Feature builders (form, splits, xG/stat trends, player per-90); Overview, Match Center, Team Analytics, Player Analytics pages with Recharts, pitch/formation component, source attribution | Pages render real sample data; features unit-tested incl. missing-data cases |
| **4** | AI layer & agents 1–3 | LLMProvider (Anthropic + Mock), prompt registry, AI cache, budget, `ai_usage`; agents 1–3 with validation & grounding checks | Agents run offline with mock; one live smoke test with real key; cache hit verified (0 calls on rerun) |
| **5** | Simulation Lab & agent 4 | Strength model, seeded Monte Carlo, scenarios (availability, formation, venue), `simulation_runs`; Simulation Lab page with assumptions/limitations & SIMULATION banner; Simulation agent | Same seed → identical results (tested); banner present everywhere |
| **6** | Orchestration & Master Analyst | Orchestrator workflow, contradiction detector, master agent, `final_reports`; AI Agents page (live status), Reports page (list/detail/export to Markdown/PDF) | End-to-end analysis of a sample match; partial-failure path tested |
| **7** | Live providers & hardening | OpenFootball, StatsBomb Open, football-data.org (requires host allowlist + key); scheduled ingestion; Settings page (providers, budgets, usage); optional admin auth; API rate limiting; security review | Live import within rate limits; attribution displayed; security checklist done |
| **8** | Polish & release | Performance (indexes, query tuning, pagination), accessibility pass, responsive QA, Playwright E2E, docs, v1.0 tag | Release candidate |

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Free providers lack xG / lineups / injuries for many leagues | Capability flags per provider; UI and agents degrade gracefully and show "unavailable" |
| Licensing restrictions (e.g. non-commercial open data) | License recorded per source; commercial-use flag surfaced in Settings; attribution in UI |
| LLM hallucination | Deterministic features, evidence-key validation, master cannot add facts |
| AI cost overrun | Hard budgets, caching, skip rules, mock provider in dev/CI |
| Provider hosts blocked in cloud sandbox | Sample-data-first; allowlist hosts before Phase 7 |
| Scope creep | Phase gates with explicit exit criteria |
