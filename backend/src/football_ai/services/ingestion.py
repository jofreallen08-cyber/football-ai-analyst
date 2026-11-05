"""Ingestion: fetch → validate → normalise → upsert, with a full audit trail.

* Every row records ``source_id``, ``fetched_at`` and ``source_updated_at``.
* Provider IDs are mapped to internal IDs through ``external_refs``.
* Invalid records are stored in ``ingestion_issues`` — never dropped silently.
* Re-running an ingestion is idempotent (rows are updated, not duplicated).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from football_ai.core.logging import get_logger
from football_ai.models import (
    AvailabilityStatus,
    AvailabilityType,
    Competition,
    CompetitionType,
    DataSource,
    ExternalRef,
    IngestionIssue,
    IngestionRun,
    IngestionStatus,
    IssueSeverity,
    Lineup,
    LineupEntry,
    LineupRole,
    Match,
    MatchStatus,
    MatchTeamStats,
    Player,
    PlayerAvailability,
    PlayerMatchStats,
    Season,
    SquadMembership,
    Team,
)
from football_ai.providers.base import (
    DataProvider,
    PMatch,
    PTeamStats,
    RecordIssue,
    SeasonBundle,
)

log = get_logger(__name__)

TEAM_STAT_FIELDS = tuple(PTeamStats.model_fields)
PLAYER_STAT_FIELDS = (
    "minutes started position goals assists shots shots_on_target xg xa key_passes passes "
    "pass_accuracy_pct tackles interceptions yellow_cards red_cards"
).split()


@dataclass
class IngestionResult:
    run_id: int
    status: IngestionStatus
    records_upserted: int
    records_rejected: int
    warnings: int
    error: str | None = None


def ensure_data_source(session: Session, provider: DataProvider) -> DataSource:
    """Create or refresh the ``data_sources`` row describing ``provider``."""
    src = session.scalar(select(DataSource).where(DataSource.key == provider.key))
    if src is None:
        src = DataSource(key=provider.key)
        session.add(src)
    src.name = provider.name
    src.license_name = provider.license.name
    src.license_url = provider.license.url
    src.attribution_text = provider.license.attribution
    src.commercial_use_allowed = provider.license.commercial_use_allowed
    src.is_synthetic = provider.is_synthetic
    session.flush()
    return src


class IngestionService:
    def __init__(self, session: Session, clock: Callable[[], datetime] | None = None) -> None:
        self.session = session
        self._clock = clock or (lambda: datetime.now(UTC))

    async def ingest(
        self, provider: DataProvider, competition_code: str, season_label: str
    ) -> IngestionResult:
        source = ensure_data_source(self.session, provider)
        run = IngestionRun(
            source_id=source.id,
            scope={"competition": competition_code, "season": season_label},
            started_at=self._clock(),
            status=IngestionStatus.RUNNING,
        )
        self.session.add(run)
        self.session.commit()
        run_id, source_id = run.id, source.id

        try:
            bundle = await provider.fetch_season(competition_code, season_label)
            writer = _BundleWriter(self.session, source_id, self._clock())
            writer.write(bundle)
        except Exception as exc:
            self.session.rollback()
            run = self.session.get_one(IngestionRun, run_id)
            run.status = IngestionStatus.FAILED
            run.error = f"{type(exc).__name__}: {exc}"[:2000]
            run.finished_at = self._clock()
            self.session.commit()
            log.warning("ingestion_failed", provider=provider.key, error=run.error)
            return IngestionResult(run_id, IngestionStatus.FAILED, 0, 0, 0, run.error)

        issues = bundle.issues + writer.issues
        errors = sum(1 for i in issues if i.severity == "error")
        warnings = len(issues) - errors
        for issue in issues:
            self.session.add(
                IngestionIssue(
                    ingestion_run_id=run_id,
                    entity_type=issue.entity_type,
                    external_id=issue.external_id,
                    severity=IssueSeverity(issue.severity),
                    message=issue.message[:2000],
                    payload=_jsonable(issue.payload),
                )
            )
        run = self.session.get_one(IngestionRun, run_id)
        run.status = IngestionStatus.PARTIAL if errors else IngestionStatus.SUCCESS
        run.records_upserted = writer.upserted
        run.records_rejected = errors
        run.finished_at = self._clock()
        self.session.commit()
        log.info(
            "ingestion_done",
            provider=provider.key,
            competition=competition_code,
            season=season_label,
            upserted=writer.upserted,
            rejected=errors,
            warnings=warnings,
        )
        return IngestionResult(run_id, run.status, writer.upserted, errors, warnings)


def _jsonable(payload: dict[str, object] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in payload.items()}


class _BundleWriter:
    """Writes one validated :class:`SeasonBundle` inside the caller's transaction."""

    def __init__(self, session: Session, source_id: int, fetched_at: datetime) -> None:
        self.s = session
        self.source_id = source_id
        self.fetched_at = fetched_at
        self.source_updated_at: datetime | None = None
        self.upserted = 0
        self.issues: list[RecordIssue] = []
        self.refs: dict[tuple[str, str], int] = {
            (r.entity_type, r.external_id): r.internal_id
            for r in session.scalars(select(ExternalRef).where(ExternalRef.source_id == source_id))
        }

    # -- helpers ------------------------------------------------------------------
    def _prov(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "fetched_at": self.fetched_at,
            "source_updated_at": self.source_updated_at,
        }

    def _apply(self, obj: Any, values: dict[str, Any]) -> None:
        for k, v in {**values, **self._prov()}.items():
            setattr(obj, k, v)
        self.upserted += 1

    def _link(self, entity_type: str, external_id: str, internal_id: int) -> None:
        if (entity_type, external_id) not in self.refs:
            self.s.add(
                ExternalRef(
                    source_id=self.source_id,
                    entity_type=entity_type,
                    external_id=external_id,
                    internal_id=internal_id,
                )
            )
            self.refs[(entity_type, external_id)] = internal_id

    def _upsert(
        self,
        model: type[Any],
        entity_type: str,
        external_id: str,
        values: dict[str, Any],
        find_existing: Callable[[], Any] | None = None,
    ) -> int:
        iid = self.refs.get((entity_type, external_id))
        obj = self.s.get(model, iid) if iid is not None else None
        if obj is None and find_existing is not None:
            obj = find_existing()
        if obj is None:
            obj = model()
            self.s.add(obj)
        self._apply(obj, values)
        self.s.flush()
        self._link(entity_type, external_id, obj.id)
        return int(obj.id)

    def _ref(self, entity_type: str, external_id: str) -> int | None:
        return self.refs.get((entity_type, external_id))

    # -- main ---------------------------------------------------------------------
    def write(self, b: SeasonBundle) -> None:
        self.source_updated_at = b.source_updated_at
        c = b.competition
        comp_id = self._upsert(
            Competition,
            "competition",
            c.external_id,
            {
                "name": c.name,
                "code": c.code,
                "country": c.country,
                "type": CompetitionType(c.type),
                "tier": c.tier,
            },
            lambda: self.s.scalar(select(Competition).where(Competition.code == c.code)),
        )
        se = b.season
        season_id = self._upsert(
            Season,
            "season",
            se.external_id,
            {
                "competition_id": comp_id,
                "label": se.label,
                "start_date": se.start_date,
                "end_date": se.end_date,
                "is_current": se.is_current,
            },
            lambda: self.s.scalar(
                select(Season).where(Season.competition_id == comp_id, Season.label == se.label)
            ),
        )
        for t in b.teams:
            self._upsert(
                Team,
                "team",
                t.external_id,
                {
                    "name": t.name,
                    "short_name": t.short_name,
                    "country": t.country,
                    "founded": t.founded,
                },
            )
        for p in b.players:
            self._upsert(
                Player,
                "player",
                p.external_id,
                p.model_dump(exclude={"external_id"}),
            )
        self._write_squads(b, season_id)
        for m in b.matches:
            self._write_match(m, season_id)
        self._write_availability(b)

    def _write_squads(self, b: SeasonBundle, season_id: int) -> None:
        existing = {
            (sm.player_id, sm.team_id): sm
            for sm in self.s.scalars(
                select(SquadMembership).where(SquadMembership.season_id == season_id)
            )
        }
        for sq in b.squads:
            pid = self._ref("player", sq.player_external_id)
            tid = self._ref("team", sq.team_external_id)
            if pid is None or tid is None:
                self.issues.append(
                    RecordIssue("squad", sq.player_external_id, "giocatore o squadra sconosciuti")
                )
                continue
            obj = existing.get((pid, tid))
            if obj is None:
                obj = SquadMembership(player_id=pid, team_id=tid, season_id=season_id)
                self.s.add(obj)
            self._apply(obj, {"shirt_number": sq.shirt_number})

    def _write_match(self, m: PMatch, season_id: int) -> None:
        home = self._ref("team", m.home_team_external_id)
        away = self._ref("team", m.away_team_external_id)
        if home is None or away is None:
            self.issues.append(RecordIssue("match", m.external_id, "squadra sconosciuta"))
            return
        match_id = self._upsert(
            Match,
            "match",
            m.external_id,
            {
                "season_id": season_id,
                "matchday": m.matchday,
                "stage": m.stage,
                "kickoff_at": m.kickoff_at,
                "home_team_id": home,
                "away_team_id": away,
                "status": MatchStatus(m.status),
                "home_score": m.home_score,
                "away_score": m.away_score,
                "home_score_ht": m.home_score_ht,
                "away_score_ht": m.away_score_ht,
                "neutral_venue": m.neutral_venue,
                "attendance": m.attendance,
                "referee": m.referee,
            },
            lambda: self.s.scalar(
                select(Match).where(
                    Match.season_id == season_id,
                    Match.home_team_id == home,
                    Match.away_team_id == away,
                    Match.kickoff_at == m.kickoff_at,
                )
            ),
        )
        for team_id, is_home, stats, opp in (
            (home, True, m.home_stats, m.away_stats),
            (away, False, m.away_stats, m.home_stats),
        ):
            if stats is None:
                continue
            row = self.s.scalar(
                select(MatchTeamStats).where(
                    MatchTeamStats.match_id == match_id, MatchTeamStats.team_id == team_id
                )
            )
            if row is None:
                row = MatchTeamStats(match_id=match_id, team_id=team_id)
                self.s.add(row)
            values = {f: getattr(stats, f) for f in TEAM_STAT_FIELDS}
            values["is_home"] = is_home
            values["xga"] = opp.xg if opp is not None else None
            self._apply(row, values)

        if m.player_stats:
            existing = {
                r.player_id: r
                for r in self.s.scalars(
                    select(PlayerMatchStats).where(PlayerMatchStats.match_id == match_id)
                )
            }
            for ps in m.player_stats:
                pid = self._ref("player", ps.player_external_id)
                tid = self._ref("team", ps.team_external_id)
                if pid is None or tid is None or tid not in (home, away):
                    self.issues.append(
                        RecordIssue(
                            "player_match_stats",
                            f"{m.external_id}/{ps.player_external_id}",
                            "giocatore o squadra non validi per la partita",
                        )
                    )
                    continue
                prow = existing.get(pid)
                if prow is None:
                    prow = PlayerMatchStats(match_id=match_id, player_id=pid)
                    self.s.add(prow)
                    existing[pid] = prow
                vals = {f: getattr(ps, f) for f in PLAYER_STAT_FIELDS}
                vals["team_id"] = tid
                self._apply(prow, vals)

        for lu in m.lineups:
            tid = self._ref("team", lu.team_external_id)
            if tid not in (home, away) or tid is None:
                self.issues.append(RecordIssue("lineup", m.external_id, "squadra non valida"))
                continue
            row_l = self.s.scalar(
                select(Lineup).where(Lineup.match_id == match_id, Lineup.team_id == tid)
            )
            if row_l is None:
                row_l = Lineup(match_id=match_id, team_id=tid)
                self.s.add(row_l)
            self._apply(
                row_l,
                {
                    "formation": lu.formation,
                    "confirmed": lu.confirmed,
                    "announced_at": lu.announced_at,
                },
            )
            self.s.flush()
            self.s.execute(delete(LineupEntry).where(LineupEntry.lineup_id == row_l.id))
            for e in lu.entries:
                pid = self._ref("player", e.player_external_id)
                if pid is None:
                    self.issues.append(
                        RecordIssue("lineup_entry", e.player_external_id, "giocatore sconosciuto")
                    )
                    continue
                self.s.add(
                    LineupEntry(
                        lineup_id=row_l.id,
                        player_id=pid,
                        role=LineupRole(e.role),
                        position=e.position,
                        grid_x=e.grid_x,
                        grid_y=e.grid_y,
                        shirt_number=e.shirt_number,
                    )
                )
        self.s.flush()

    def _write_availability(self, b: SeasonBundle) -> None:
        for a in b.availability:
            pid = self._ref("player", a.player_external_id)
            tid = self._ref("team", a.team_external_id)
            if pid is None or tid is None:
                self.issues.append(
                    RecordIssue("availability", a.external_id, "giocatore o squadra sconosciuti")
                )
                continue
            self._upsert(
                PlayerAvailability,
                "availability",
                a.external_id,
                {
                    "player_id": pid,
                    "team_id": tid,
                    "type": AvailabilityType(a.type),
                    "description": a.description,
                    "reported_at": a.reported_at,
                    "expected_return": a.expected_return,
                    "source_url": a.source_url,
                    "status": AvailabilityStatus(a.status),
                },
            )
