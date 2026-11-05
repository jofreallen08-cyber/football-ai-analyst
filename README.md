# Football AI Analyst

Piattaforma professionale di analisi calcistica con cinque agenti AI specializzati:
analisi delle partite, statistiche di squadre e giocatori, confronti tattici e
simulazioni virtuali.

> **Scopo educativo.** Nessuna scommessa, quota, integrazione con bookmaker o pronostico
> a pagamento. Le simulazioni sono scenari ipotetici, mai risultati reali o garantiti.

## Stato

| Fase | Contenuto | Stato |
|---|---|---|
| 0 | Pianificazione ([docs/](docs/)) | ✅ |
| 1 | Fondamenta: API, database, interfaccia base, Docker, CI | ✅ |
| 2 | Livello dati con dataset di esempio | prossima |

Roadmap completa: [docs/05-roadmap.md](docs/05-roadmap.md).

## Stack

- **Backend:** Python 3.13, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL 16, Pandas, NumPy
- **Frontend:** React 19, TypeScript, Tailwind CSS 4, TanStack Query, Recharts
- **Strumenti:** uv, pnpm, Pytest, Vitest, Docker Compose, GitHub Actions

## Avvio rapido con Docker

```bash
cp .env.example .env
docker compose up --build
# apri http://127.0.0.1:8080
```

## Sviluppo locale (senza Docker)

Requisiti: Python 3.13 + [uv](https://docs.astral.sh/uv/), Node 22 + pnpm, PostgreSQL 16.

```bash
# 1. Database
createuser -P football          # password: football
createdb -O football football_ai
createdb -O football football_ai_test

# 2. Backend  → http://127.0.0.1:8000/docs
cp .env.example backend/.env
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn football_ai.main:app --reload

# 3. Frontend → http://127.0.0.1:5173  (in un altro terminale)
cd frontend
pnpm install
pnpm dev
```

## Test e controlli

```bash
# Backend (i test di database richiedono TEST_DATABASE_URL)
cd backend
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy

# Frontend
cd frontend
pnpm test && pnpm typecheck && pnpm lint && pnpm build
```

## Sicurezza

- Le chiavi API stanno solo in variabili d'ambiente (`.env`, mai committato); il frontend non contiene credenziali.
- Il backend ascolta su `127.0.0.1` per impostazione predefinita (uso locale, utente singolo).
- I log sono JSON strutturati e mascherano automaticamente i campi sensibili.

## Documentazione

- [Architettura](docs/01-architecture.md) · [Struttura cartelle](docs/02-folder-structure.md) · [Schema database](docs/03-database-schema.md)
- [Agenti AI](docs/04-ai-agent-specifications.md) · [Roadmap](docs/05-roadmap.md) · [Decisioni (ADR)](docs/adr/)
