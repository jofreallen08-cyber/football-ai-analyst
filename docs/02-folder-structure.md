# 02 — Project Folder Structure

Monorepo with independent backend and frontend packages.

```
football-ai-analyst/
├── README.md
├── docker-compose.yml               # db + backend + frontend
├── .env.example                     # every variable documented, no real values
├── .gitignore
├── .github/workflows/ci.yml         # lint, type-check, tests (backend + frontend)
├── docs/                            # architecture, ADRs, agent specs, roadmap
│   └── adr/                         # Architecture Decision Records
│
├── backend/
│   ├── pyproject.toml               # uv-managed; ruff, mypy, pytest config
│   ├── uv.lock
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── src/football_ai/
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── core/
│   │   │   ├── config.py            # pydantic-settings
│   │   │   ├── logging.py           # structlog setup, redaction
│   │   │   ├── db.py                # engine, session dependency
│   │   │   └── errors.py            # domain exceptions + handlers
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic API + domain schemas
│   │   ├── repositories/            # DB access per aggregate
│   │   ├── api/v1/
│   │   │   ├── competitions.py
│   │   │   ├── matches.py
│   │   │   ├── teams.py
│   │   │   ├── players.py
│   │   │   ├── analyses.py          # orchestration runs + reports
│   │   │   ├── simulations.py
│   │   │   ├── providers.py         # status, attribution, ingestion triggers
│   │   │   └── settings.py          # non-secret settings, AI usage
│   │   ├── services/                # ingestion, analysis, simulation use-cases
│   │   ├── providers/
│   │   │   ├── base.py              # DataProvider protocol, capabilities, license
│   │   │   ├── registry.py
│   │   │   ├── cache.py             # ResponseCache
│   │   │   ├── rate_limit.py        # token bucket, backoff, circuit breaker
│   │   │   ├── validation.py
│   │   │   ├── normalize.py         # entity resolution
│   │   │   ├── local_sample.py
│   │   │   ├── openfootball.py
│   │   │   ├── statsbomb_open.py
│   │   │   └── football_data_org.py
│   │   ├── features/                # pure Pandas/NumPy analytics
│   │   │   ├── form.py
│   │   │   ├── splits.py            # home/away
│   │   │   ├── team_stats.py        # xG, shots, possession, corners
│   │   │   └── player_stats.py
│   │   ├── ai/
│   │   │   ├── llm/
│   │   │   │   ├── base.py          # LLMProvider protocol
│   │   │   │   ├── anthropic.py
│   │   │   │   └── mock.py
│   │   │   ├── prompts/             # versioned prompt files per agent
│   │   │   │   ├── match_analyst/v1.md
│   │   │   │   ├── statistics/v1.md
│   │   │   │   ├── team_intelligence/v1.md
│   │   │   │   ├── simulation/v1.md
│   │   │   │   └── master/v1.md
│   │   │   ├── prompt_registry.py
│   │   │   ├── cache.py             # AICache
│   │   │   └── budget.py            # usage limits
│   │   ├── agents/
│   │   │   ├── base.py              # BaseAgent, AgentReport schema
│   │   │   ├── match_analyst.py
│   │   │   ├── statistics.py
│   │   │   ├── team_intelligence.py
│   │   │   ├── simulation.py
│   │   │   └── master.py
│   │   ├── orchestration/
│   │   │   ├── context.py           # ContextBundle builder, data hash
│   │   │   ├── contradictions.py    # deterministic cross-report checks
│   │   │   └── orchestrator.py
│   │   └── simulation/
│   │       ├── strength_model.py
│   │       ├── engine.py            # seeded Monte Carlo
│   │       └── scenarios.py         # availability/formation/venue modifiers
│   ├── data/samples/                # bundled sample datasets + README (origin, license)
│   ├── scripts/                     # seed_db.py, ingest.py (CLI)
│   └── tests/
│       ├── conftest.py
│       ├── unit/                    # features, simulation, validation, agents (mock LLM)
│       ├── integration/             # repositories + API against Postgres
│       └── fixtures/                # recorded provider responses
│
└── frontend/
    ├── package.json                 # pnpm
    ├── Dockerfile
    ├── vite.config.ts
    ├── nginx.conf                   # production container: static files + /api proxy
    ├── tsconfig.json
    ├── index.html
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx                  # router + layout shell
    │   ├── api/                     # generated types + client + query hooks
    │   ├── components/
    │   │   ├── layout/              # Sidebar, Topbar, PageHeader
    │   │   ├── ui/                  # Card, StatTile, Badge, Skeleton, ErrorState, EmptyState
    │   │   ├── charts/              # Recharts wrappers (form line, xG bars, radar)
    │   │   ├── pitch/               # SVG Pitch, FormationView, ShotMap
    │   │   └── domain/              # AgentStatusBadge, SourceAttribution, SimulationBanner
    │   ├── pages/
    │   │   ├── Overview.tsx
    │   │   ├── MatchCenter.tsx
    │   │   ├── TeamAnalytics.tsx
    │   │   ├── PlayerAnalytics.tsx
    │   │   ├── AIAgents.tsx
    │   │   ├── SimulationLab.tsx
    │   │   ├── Reports.tsx
    │   │   └── Settings.tsx
    │   ├── lib/                     # formatters, constants
    │   └── styles/index.css         # Tailwind v4 + dark navy design tokens (@theme)
    └── tests/                       # Vitest unit + Playwright smoke
```
