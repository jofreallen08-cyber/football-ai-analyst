from football_ai.ai.schemas import AgentReport, Finding
from football_ai.orchestration.contradictions import Contradiction
from football_ai.orchestration.orchestrator import _cap_confidence, _numbers, automatic_synthesis


def rep(
    agent: str, status: str = "completed", claim: str = "Fatto 12", conf: str = "high"
) -> AgentReport:
    findings = (
        [Finding(claim=claim, evidence_keys=["k"], strength="low")] if status == "completed" else []
    )
    return AgentReport(
        agent=agent,
        status=status,
        headline=f"Titolo {agent}",
        findings=findings,
        missing_information=["manca x"],
        confidence=conf,
        limitations=[],
        sources=["s"],
        provider="mock",
        model="m",
        prompt_version="v1",
    )


def test_numbers_normalises_decimal_comma() -> None:
    assert _numbers("xG 1,45 e 3 tiri, 12.5%") == {"1.45", "3", "12.5"}


def test_confidence_is_capped_by_failures_and_contradictions() -> None:
    ok = {"a": rep("a"), "b": rep("b")}
    assert _cap_confidence("high", ok, []) == "high"
    one_fail = {"a": rep("a"), "b": rep("b", "failed")}
    assert _cap_confidence("high", one_fail, []) == "medium"
    two = {"a": rep("a", "skipped"), "b": rep("b", "failed")}
    assert _cap_confidence("high", two, []) == "low"
    warn = [Contradiction("x", "d", ["a"], "warning")] * 2
    assert _cap_confidence("medium", ok, warn) == "low"
    assert _cap_confidence("low", ok, []) == "low"  # never raised


def test_automatic_synthesis_only_reuses_existing_text() -> None:
    reports = {"match_analyst": rep("match_analyst"), "statistics": rep("statistics", "skipped")}
    c = [Contradiction("c", "Descrizione 7", ["match_analyst"], "warning")]
    out = automatic_synthesis(reports, c, ["manca y", "manca y"])
    assert out.summary == "Titolo match_analyst"
    assert out.key_findings[0].finding == "Fatto 12"
    assert out.contradictions[0].description == "Descrizione 7"
    assert out.missing_information == ["manca y"] and out.overall_confidence == "low"
