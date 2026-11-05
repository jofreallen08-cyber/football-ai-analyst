"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from football_ai.models.base import Base
from football_ai.models.football import (
    Competition,
    CompetitionType,
    Match,
    MatchStatus,
    MatchTeamStats,
    Player,
    PlayerMatchStats,
    Season,
    Team,
    TeamAlias,
)
from football_ai.models.provenance import (
    DataSource,
    ExternalRef,
    IngestionIssue,
    IngestionRun,
    IngestionStatus,
    IssueSeverity,
)

__all__ = [
    "Base",
    "Competition",
    "CompetitionType",
    "DataSource",
    "ExternalRef",
    "IngestionIssue",
    "IngestionRun",
    "IngestionStatus",
    "IssueSeverity",
    "Match",
    "MatchStatus",
    "MatchTeamStats",
    "Player",
    "PlayerMatchStats",
    "Season",
    "Team",
    "TeamAlias",
]
