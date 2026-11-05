# ADR 0001 — Decisioni iniziali di prodotto e stack

Data: 2026-11-05 · Stato: **Accettato**

## Decisioni del product owner

| # | Domanda | Decisione |
|---|---|---|
| 1 | Fornitore AI predefinito | **Anthropic** (modello configurabile via variabile d'ambiente); provider `mock` per sviluppo e CI |
| 2 | Campionati iniziali | **Serie A, Premier League, La Liga** |
| 3 | Destinazione di esecuzione | **Locale** (sviluppo diretto o Docker Compose) |
| 4 | Autenticazione | **Utente singolo** — nessun sistema di account; API esposta solo su localhost per impostazione predefinita |
| 5 | Lingua | **Interfaccia in italiano** (testi UI e report AI in italiano; codice, identificatori e commenti tecnici in inglese) |
| 6 | Rete | Autorizzare gli host dei fornitori di dati calcistici quando si arriva alla Fase 7 |

## Decisioni tecniche

* Python gestito con **uv**, frontend con **pnpm**.
* Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, psycopg 3, structlog.
* Frontend: Vite, React 18, TypeScript strict, Tailwind CSS, React Router, TanStack Query, Recharts.
* Pacchetto Python: `football_ai`.

## Conseguenze

* I prompt degli agenti chiedono output in italiano; i controlli anti-scommesse includono termini italiani (quota, scommessa, puntata, pronostico sicuro…).
* Nessuna pagina di login; in Fase 7 si valuterà al massimo un token locale opzionale per la pagina Impostazioni.
* Il backend ascolta su `127.0.0.1` per impostazione predefinita.
