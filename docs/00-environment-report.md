# 00 — Development Environment Report

Inspected: 2026-11-05

## Repository

| Item | State |
|---|---|
| Branch | `main`, clean, 1 commit (`Initial commit`) |
| Contents | `README.md` only (one line). No existing code — nothing to overwrite. |

## Toolchain

| Tool | Version | Notes |
|---|---|---|
| Python | 3.13.18 | Target runtime for backend |
| uv | installed | Chosen Python package/venv manager (fast, lockfile) |
| poetry | installed | Not used (uv preferred) |
| Node.js | 22.23.4 | Frontend runtime |
| npm / pnpm / yarn | 10.9.9 / installed / installed | **pnpm** chosen for frontend |
| PostgreSQL | 16.15 | Installed, cluster `16/main` is **down** (can be started locally) |
| Docker | 29.9.2 CLI | **Daemon not running** in this container |
| Git | 2.43.0 | |
| Chromium + Playwright | pre-installed | Usable for frontend E2E/screenshot checks |
| Hardware | 4 CPU, 15 GiB RAM | Ample |

## Network reachability (via environment proxy)

| Host | Result | Impact |
|---|---|---|
| pypi.org, registry.npmjs.org | OK | Dependencies installable |
| raw.githubusercontent.com | OK | Open datasets hosted on GitHub (openfootball, StatsBomb open-data) reachable |
| api.anthropic.com | OK | AI provider reachable (key required) |
| api.football-data.org | **Blocked / timeout** | Needs allowlisting in the cloud environment before live ingestion |
| www.football-data.co.uk | **Blocked / timeout** | Same |

## Consequences for the plan

1. **Local development without Docker in this sandbox**: tests run against the locally installed PostgreSQL 16 (or SQLite for pure unit tests). `docker-compose.yml` is still authored for users' machines and CI.
2. **Sample-data-first**: Phase 1–3 run fully on bundled local sample datasets; live providers are added behind feature flags once their hosts are allowlisted and API keys are configured.
3. **AI offline mode**: a deterministic `MockLLMProvider` lets the whole pipeline run and be tested without any API key or network call.
