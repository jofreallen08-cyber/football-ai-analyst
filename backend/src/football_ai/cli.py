"""Command-line interface.

Examples::

    uv run football-ai seed                       # import every bundled dataset
    uv run football-ai ingest openfootball SA 2025/26
    uv run football-ai ingest openfootball SA 2025/26 --remote   # fetch from GitHub
    uv run football-ai sources
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from football_ai.core.config import get_settings
from football_ai.core.db import get_sessionmaker
from football_ai.core.logging import configure_logging
from football_ai.models import DataSource
from football_ai.providers.base import DataProvider, RateLimitPolicy
from football_ai.providers.http import CachedHttpClient
from football_ai.providers.openfootball import OpenFootballProvider
from football_ai.providers.rate_limit import TokenBucket
from football_ai.providers.registry import build_providers
from football_ai.services.ingestion import IngestionService, ensure_data_source


def _remote_openfootball() -> OpenFootballProvider:
    settings = get_settings()
    factory = get_sessionmaker()
    bundled = OpenFootballProvider(bundled_dir=settings.data_dir / "samples" / "openfootball")

    def source_id() -> int:
        with factory() as s:
            src = ensure_data_source(s, bundled)
            s.commit()
            return src.id

    http = CachedHttpClient(
        source_key=bundled.key,
        source_id_resolver=source_id,
        session_factory=factory,
        limiter=TokenBucket(RateLimitPolicy(requests=30, per_seconds=60)),
    )
    return OpenFootballProvider(
        bundled_dir=bundled.bundled_dir,
        mode="remote",
        base_url=settings.openfootball_base_url,
        http=http,
    )


async def _ingest(provider: DataProvider, code: str, season: str) -> bool:
    with get_sessionmaker()() as session:
        result = await IngestionService(session).ingest(provider, code, season)
    print(
        f"[{result.status.value}] {provider.key} {code} {season}: "
        f"{result.records_upserted} record, {result.records_rejected} scartati, "
        f"{result.warnings} avvisi" + (f" — {result.error}" if result.error else "")
    )
    return result.error is None


async def _seed() -> bool:
    ok = True
    for provider in build_providers(get_settings()).values():
        for item in await provider.list_available():
            ok &= await _ingest(provider, item.competition_code, item.season_label)
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="football-ai", description="Football AI Analyst CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="importa tutti i dataset inclusi nel progetto")
    ing = sub.add_parser("ingest", help="importa una stagione da un fornitore")
    ing.add_argument("provider")
    ing.add_argument("competition", help="codice competizione, es. SA, PL, PD, DEMO")
    ing.add_argument("season", help="etichetta stagione, es. 2025/26")
    ing.add_argument("--remote", action="store_true", help="openfootball: scarica da GitHub")
    sub.add_parser("sources", help="elenca le fonti registrate")
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level, json=settings.log_json)

    if args.command == "seed":
        return 0 if asyncio.run(_seed()) else 1
    if args.command == "ingest":
        providers = build_providers(settings)
        provider: DataProvider | None = (
            _remote_openfootball()
            if args.remote and args.provider == "openfootball"
            else providers.get(args.provider)
        )
        if provider is None:
            print(f"fornitore sconosciuto: {args.provider} (disponibili: {', '.join(providers)})")
            return 2
        return 0 if asyncio.run(_ingest(provider, args.competition, args.season)) else 1
    with get_sessionmaker()() as s:
        for src in s.scalars(select(DataSource).order_by(DataSource.key)):
            flag = " [SINTETICO]" if src.is_synthetic else ""
            print(f"{src.key}{flag}: {src.name} — {src.license_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
