# Dataset inclusi

| Cartella | Contenuto | Origine e licenza | Reale? |
|---|---|---|---|
| `openfootball/2024-25`, `openfootball/2025-26` | Calendari e risultati di Serie A (`it.1`), Premier League (`en.1`), La Liga (`es.1`) | [openfootball/football.json](https://github.com/openfootball/football.json) — pubblico dominio (CC0). Snapshot scaricato il 2026-11-05. | **Sì**, solo risultati: nessuna statistica avanzata (xG, tiri, possesso…) |
| `demo/DEMO_2026-27.json` | "Lega Dimostrativa": 10 squadre, 200 giocatori, 90 partite con xG, statistiche, formazioni e indisponibilità | Generato da `scripts/generate_demo_dataset.py` (seed fisso, output deterministico) | **No — SINTETICO.** Squadre, giocatori e numeri sono inventati |

Regole:

- Le statistiche che una fonte non fornisce restano vuote (`NULL`) e vengono mostrate come *non disponibili*.
- Nessun dato di quote o scommesse è incluso o importato.
- Le partite passate senza risultato nella fonte (10 nel 2024/25 di Serie A e La Liga) vengono importate senza punteggio e segnalate come avviso in `ingestion_issues`.

Aggiornare lo snapshot openfootball:

```bash
uv run football-ai ingest openfootball SA 2025/26 --remote   # scarica da GitHub (cache + rate limit)
```
