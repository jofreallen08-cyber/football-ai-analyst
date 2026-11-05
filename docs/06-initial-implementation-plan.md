# 06 — Initial Implementation Plan (Phase 1: Foundation)

Goal: a running, tested skeleton — no football logic yet, no AI calls. Delivered as small commits on a feature branch.

## Steps

| # | Task | Output | Tests / checks |
|---|---|---|---|
| 1.1 | Repo hygiene | `.gitignore`, `.editorconfig`, `.env.example`, updated `README.md` (setup, scripts, no-betting statement) | — |
| 1.2 | Backend scaffold | `backend/pyproject.toml` (uv): fastapi, uvicorn, pydantic-settings, sqlalchemy 2, psycopg 3, alembic, pandas, numpy, structlog, httpx; dev: pytest, pytest-asyncio, ruff, mypy | `uv sync` succeeds |
| 1.3 | Core modules | `core/config.py` (env-driven settings, secrets as `SecretStr`), `core/logging.py` (JSON logs, redaction, request-id middleware), `core/errors.py`, `core/db.py` | Unit tests: config loads defaults, secrets never in `repr`/logs |
| 1.4 | App factory + health | `main.py`, `GET /api/v1/health` (app + DB status), CORS allowlist from env, problem+json error handler | API test with httpx `AsyncClient` |
| 1.5 | Database baseline | ORM models for provenance + domain tables (`data_sources`, `ingestion_runs`, `ingestion_issues`, `competitions`, `seasons`, `teams`, `team_aliases`, `players`, `matches`, `match_team_stats`, `player_match_stats`); first Alembic migration with constraints & indexes | Migration up/down on local Postgres 16; constraint tests (e.g. negative score rejected) |
| 1.6 | Frontend scaffold | Vite + React + TS (strict) + Tailwind + React Router + TanStack Query + Recharts; dark navy tokens | `pnpm build`, `tsc --noEmit`, eslint |
| 1.7 | App shell | Responsive sidebar + topbar, routes for all 8 pages with placeholder content, shared `Card`, `Skeleton`, `ErrorState`, `EmptyState`, health indicator calling `/api/v1/health` | Vitest + Testing Library: routes render, error state on failed fetch |
| 1.8 | Containers | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` (postgres:16, backend, frontend), healthchecks | Compose file validates (`docker compose config`); run on a host with Docker daemon |
| 1.9 | CI | GitHub Actions: ruff, mypy, pytest (Postgres service), eslint, tsc, vitest, build | Pipeline green |
| 1.10 | Docs | `docs/adr/0001-monorepo-and-stack.md`, backend & frontend module READMEs | — |

## Key decisions taken in this plan (open to change)

* **uv** for Python, **pnpm** for frontend.
* **psycopg 3** driver; SQLAlchemy 2.0 typed ORM; sync sessions in Phase 1, async where it matters later (I/O-bound providers/LLM use `httpx.AsyncClient` regardless).
* **Background work**: in-process asyncio tasks + `analysis_runs` status table initially; a queue (e.g. arq/Redis) only if needed later.
* **AI provider default**: Anthropic (model set via env var), with Mock provider for dev/CI; provider abstraction keeps others pluggable.
* **Package name**: `football_ai`.

## Open questions for approval

1. **AI provider** — confirm Anthropic as the default vendor (or name another).
2. **Initial competitions** — which 2–3 leagues should the sample dataset and first live imports focus on?
3. **Deployment target** — local/Docker only for now, or a specific cloud host?
4. **Authentication** — single-user tool, or multi-user accounts needed?
5. **Language** — English UI only, or also another language (e.g. Italian) from the start?
6. **Network** — OK to allowlist `api.football-data.org` (and GitHub raw for open datasets) in the cloud environment when we reach Phase 7?
