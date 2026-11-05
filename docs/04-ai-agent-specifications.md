# 04 — AI Agent Specifications

## Common contract

Every agent subclasses `BaseAgent` and follows the same lifecycle:

```
build_context(bundle: ContextBundle) -> AgentContext   # deterministic, no LLM
run(ctx) -> AgentReport                                # ≤ 1 LLM call (+1 repair retry)
```

**Shared `AgentReport` schema (Pydantic, JSON-validated):**

```json
{
  "agent": "statistics",
  "headline": "string (≤ 160 chars)",
  "findings": [
    {"claim": "string", "evidence_keys": ["home.xg_last5_avg"], "strength": "low|medium|high"}
  ],
  "missing_information": ["Lineups not yet confirmed", "..."],
  "confidence": "low|medium|high",
  "limitations": ["string"],
  "sources": ["local_sample", "statsbomb_open"]
}
```

Shared rules (enforced in prompts **and** post-validation):

* Use only facts present in the supplied context; every finding cites `evidence_keys` that must exist in the context. Findings with unknown keys are rejected.
* State missing data explicitly; never estimate unavailable statistics.
* No betting language: no odds, tips, stakes, "value", "sure thing", recommendations to wager. A lexical filter flags such terms and fails validation.
* Neutral, analytical tone; English output (localisation later).
* If the context is too thin (e.g. < N matches), return `confidence: low` with a short report — or skip the LLM call entirely and emit a deterministic "insufficient data" report.

Configuration per agent (env/`app_settings`): `enabled`, `model`, `max_output_tokens`, `timeout_s`, `prompt_version`.

---

## Agent 1 — Match Analyst

| | |
|---|---|
| **Purpose** | Contextualise the fixture: recent form, home/away performance, head-to-head, competition context. |
| **Deterministic inputs** | Last N (default 5/10) results per team with W/D/L, goals for/against; home-only and away-only splits; points per game; H2H last N meetings; league position & points gap (if standings available); days of rest since last match; competition stage. |
| **Output focus** | Form trajectory, venue effect, H2H patterns (with sample-size caveat), schedule/fatigue context. |
| **Missing-data behaviour** | H2H < 3 meetings → flagged as low-sample. No standings → omitted, listed as missing. |

## Agent 2 — Statistics AI

| | |
|---|---|
| **Purpose** | Interpret performance metrics beyond results. |
| **Deterministic inputs** | Rolling averages and trends of xG, xGA, goals vs xG (finishing over/under-performance), shots, shots on target, possession, corners, cards; league percentiles; top player aggregates (goals, xG, xA, minutes, per-90 values with minimum-minutes threshold). |
| **Output focus** | Underlying performance vs results, attacking/defensive profile, key statistical contributors, data-quality notes. |
| **Missing-data behaviour** | Provider without xG → xG-based findings removed, "xG unavailable for this competition" listed. Per-90 metrics suppressed below 270 minutes. |

## Agent 3 — Team Intelligence

| | |
|---|---|
| **Purpose** | Summarise availability and tactical set-up from **verified, attributed** sources only. |
| **Deterministic inputs** | `player_availability` (injuries, suspensions with `reported_at` and source), confirmed or last-known lineups and formations, formation usage frequency, impact of absent players (their share of team minutes/xG/xA). |
| **Output focus** | Who is unavailable and why it matters statistically, likely tactical shape (explicitly labelled *expected* vs *confirmed*), staleness of the information. |
| **Missing-data behaviour** | No team-news source → report states "No verified team news available" and does **not** speculate. Each item shows timestamp + source. No rumour scraping. |

## Agent 4 — Simulation AI

| | |
|---|---|
| **Purpose** | Explain results of the deterministic `SimulationEngine` for baseline and scenario runs. |
| **Deterministic inputs** | Simulation run results (seed, iterations, model version, training window), scenario deltas vs baseline (e.g. key striker unavailable), assumptions and limitations lists. The LLM never generates simulated numbers. |
| **Output focus** | What the model suggests under stated assumptions, sensitivity of outcomes to scenarios, why simulations differ from reality. |
| **Mandatory** | Every report starts with the label *SIMULATION — hypothetical, not an actual or guaranteed result*; validation fails otherwise. |

## Agent 5 — Master Analyst

| | |
|---|---|
| **Purpose** | Integrate the four reports into a final structured report. |
| **Inputs** | The four `AgentReport`s (or their failure/skip status) + deterministic contradiction checks from `orchestration/contradictions.py`, e.g.: results-form "strong" vs xG trend "declining"; Team Intelligence "key striker out" vs Simulation baseline not including that scenario; differing sample windows. |
| **Output schema** | `summary`, `key_findings[]` (with originating agent), `agreements[]`, `contradictions[]` (description, agents involved, likely reason, resolution or "unresolved"), `missing_information[]` (deduplicated), `overall_confidence`, `sources[]`, `disclaimer`. |
| **Rules** | Cannot introduce new facts — only synthesise. Downgrades confidence when agents failed or disagree. Always includes the educational/no-betting disclaimer. |

---

## Orchestration & cost controls

| Control | Default (configurable) |
|---|---|
| LLM calls per analysis | max 5 (+ max 1 repair retry each, counted in budget) |
| Max output tokens per agent | 800 (master: 1500) |
| Daily call cap | 100 |
| Daily token cap | 500k |
| Cache | Reuse when `data_hash` + `prompt_version` + `model` unchanged |
| Skip rule | No LLM call when deterministic context is insufficient |
| Concurrency | Agents 1–4 in parallel, master after; per-agent timeout 60 s |
| Offline | `AI_PROVIDER=mock` runs entire pipeline with deterministic outputs |

Budget exhaustion → run completes with `partial` status and a clear UI message; no silent truncation.
