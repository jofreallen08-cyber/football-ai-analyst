import json
from pathlib import Path

import pytest

from football_ai.providers.base import ProviderError
from football_ai.providers.local_sample import LocalSampleProvider

DEMO = Path(__file__).resolve().parents[2] / "data" / "samples" / "demo"


async def test_demo_dataset_is_valid_and_flagged_synthetic() -> None:
    p = LocalSampleProvider(DEMO)
    assert p.is_synthetic
    [season] = await p.list_available()
    b = await p.fetch_season(season.competition_code, season.season_label)
    assert b.issues == []
    assert len(b.teams) == 10 and len(b.matches) == 90
    finished = [m for m in b.matches if m.status == "finished"]
    assert finished and all(m.home_stats and m.home_stats.xg is not None for m in finished)
    assert all(m.home_stats.offsides is None for m in finished)  # not provided → None
    assert any(a.status == "active" for a in b.availability)


async def test_dataset_without_synthetic_flag_rejected(tmp_path: Path) -> None:
    data = json.loads(next(DEMO.glob("*.json")).read_text())
    data["synthetic"] = False
    (tmp_path / "x.json").write_text(json.dumps(data))
    with pytest.raises(ProviderError, match="synthetic"):
        await LocalSampleProvider(tmp_path).fetch_season("DEMO", "2026/27")


async def test_invalid_rows_reported(tmp_path: Path) -> None:
    data = json.loads(next(DEMO.glob("*.json")).read_text())
    data["matches"][0]["home_stats"]["possession_pct"] = 140
    (tmp_path / "x.json").write_text(json.dumps(data))
    b = await LocalSampleProvider(tmp_path).fetch_season("DEMO", "2026/27")
    assert len(b.matches) == 89
    assert "possession_pct" in b.issues[0].message


def test_generator_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    import importlib.util

    script = Path(__file__).resolve().parents[2] / "scripts" / "generate_demo_dataset.py"
    spec = importlib.util.spec_from_file_location("gen", script)
    assert spec and spec.loader
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    out = tmp_path / "demo.json"
    monkeypatch.setattr(gen, "OUT", out)
    gen.main()
    assert out.read_bytes() == next(DEMO.glob("*.json")).read_bytes()
