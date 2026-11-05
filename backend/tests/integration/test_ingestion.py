"""Ingestion against PostgreSQL: idempotency, provenance, issues and failure handling."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from football_ai.models import (
    DataSource,
    IngestionIssue,
    IngestionRun,
    IngestionStatus,
    Match,
    MatchTeamStats,
    PlayerAvailability,
)
from football_ai.providers.base import (
    AvailableSeason,
    Capability,
    PCompetition,
    PMatch,
    ProviderError,
    ProviderLicense,
    PSeason,
    PTeam,
    RecordIssue,
    SeasonBundle,
)
from football_ai.services.ingestion import IngestionService

pytestmark = pytest.mark.db
KO = datetime(2026, 3, 1, 15, tzinfo=UTC)


class FakeProvider:
    key = "fake"
    name = "Fake"
    license = ProviderLicense("Test", None, "Test", False)
    capabilities = frozenset({Capability.RESULTS})
    is_synthetic = True

    def __init__(self, bundle: SeasonBundle | None = None, error: Exception | None = None):
        self.bundle = bundle
        self.error = error

    async def list_available(self) -> list[AvailableSeason]:
        return []

    async def fetch_season(self, competition_code: str, season_label: str) -> SeasonBundle:
        if self.error:
            raise self.error
        assert self.bundle
        return self.bundle


def _bundle(**kw) -> SeasonBundle:
    teams = [PTeam(external_id="a", name="Alfa"), PTeam(external_id="b", name="Beta")]
    match = PMatch(
        external_id="m1",
        kickoff_at=KO,
        home_team_external_id="a",
        away_team_external_id="b",
        status="finished",
        home_score=2,
        away_score=0,
    )
    return SeasonBundle(
        competition=PCompetition(external_id="c", name="Coppa Test", code="FAKE"),
        season=PSeason(external_id="s", label="2025/26"),
        teams=teams,
        matches=[match],
        **kw,
    )


async def test_ingestion_is_idempotent_and_tracks_provenance(db_session) -> None:
    svc = IngestionService(db_session)
    r1 = await svc.ingest(FakeProvider(_bundle()), "FAKE", "2025/26")
    r2 = await svc.ingest(FakeProvider(_bundle()), "FAKE", "2025/26")
    assert r1.status == r2.status == IngestionStatus.SUCCESS
    src = db_session.scalar(select(DataSource).where(DataSource.key == "fake"))
    matches = db_session.scalars(select(Match).where(Match.source_id == src.id)).all()
    assert len(matches) == 1
    assert matches[0].fetched_at is not None
    assert src.is_synthetic is True


async def test_issues_are_persisted_and_mark_run_partial(db_session) -> None:
    b = _bundle(issues=[RecordIssue("match", "x", "record rotto", {"k": 1})])
    res = await IngestionService(db_session).ingest(FakeProvider(b), "FAKE", "2025/26")
    assert res.status == IngestionStatus.PARTIAL and res.records_rejected == 1
    issue = db_session.scalar(
        select(IngestionIssue).where(IngestionIssue.ingestion_run_id == res.run_id)
    )
    assert issue.message == "record rotto" and issue.payload == {"k": 1}


async def test_warnings_do_not_make_run_partial(db_session) -> None:
    b = _bundle(issues=[RecordIssue("match", "x", "avviso", severity="warning")])
    res = await IngestionService(db_session).ingest(FakeProvider(b), "FAKE", "2025/26")
    assert res.status == IngestionStatus.SUCCESS and res.warnings == 1


async def test_unknown_team_reference_recorded(db_session) -> None:
    b = _bundle()
    b.matches.append(
        PMatch(
            external_id="m2",
            kickoff_at=KO,
            home_team_external_id="a",
            away_team_external_id="zzz",
            status="scheduled",
        )
    )
    res = await IngestionService(db_session).ingest(FakeProvider(b), "FAKE", "2025/26")
    assert res.status == IngestionStatus.PARTIAL


async def test_provider_failure_records_failed_run(db_session) -> None:
    res = await IngestionService(db_session).ingest(
        FakeProvider(error=ProviderError("rete non disponibile")), "FAKE", "2025/26"
    )
    assert res.status == IngestionStatus.FAILED
    run = db_session.get(IngestionRun, res.run_id)
    assert "rete non disponibile" in run.error and run.finished_at is not None


def test_seeded_demo_has_full_data(seeded_engine) -> None:
    from sqlalchemy.orm import Session

    with Session(seeded_engine) as s:
        assert s.scalar(select(func.count(MatchTeamStats.id))) == 2 * 55
        assert s.scalar(select(func.count(PlayerAvailability.id))) == 7
        real_stats = s.scalar(
            select(func.count(MatchTeamStats.id))
            .join(DataSource, DataSource.id == MatchTeamStats.source_id)
            .where(DataSource.key == "openfootball")
        )
        assert real_stats == 0  # results-only source: no statistics invented


async def test_reingest_removes_player_stats_no_longer_in_source(db_session) -> None:
    from football_ai.models import PlayerMatchStats
    from football_ai.providers.base import PPlayer, PPlayerStats

    def bundle(player_ids: list[str]) -> SeasonBundle:
        b = _bundle(players=[PPlayer(external_id=p, full_name=p.upper()) for p in ("p1", "p2")])
        m = b.matches[0]
        b.matches[0] = m.model_copy(
            update={
                "player_stats": [
                    PPlayerStats(player_external_id=p, team_external_id="a", minutes=90)
                    for p in player_ids
                ]
            }
        )
        return b

    svc = IngestionService(db_session)
    await svc.ingest(FakeProvider(bundle(["p1", "p2"])), "FAKE", "2025/26")
    await svc.ingest(FakeProvider(bundle(["p1"])), "FAKE", "2025/26")
    src = db_session.scalar(select(DataSource).where(DataSource.key == "fake"))
    rows = db_session.scalars(
        select(PlayerMatchStats).where(PlayerMatchStats.source_id == src.id)
    ).all()
    assert len(rows) == 1
