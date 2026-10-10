from __future__ import annotations

import pytest

from agentic_qa.domain.models import (
    EvidenceReference,
    OracleKind,
    OracleVerdict,
    Outcome,
    RunResult,
    ScenarioResult,
    is_safe_identifier,
)

_EVIDENCE = (EvidenceReference("screenshot", "r/s/final.png", "d" * 64),)
_PASS = OracleVerdict(OracleKind.DETERMINISTIC, True, "ok", "ok")
_FAIL = OracleVerdict(OracleKind.DETERMINISTIC, False, "ok", "bad")
_SEMANTIC_PASS = OracleVerdict(
    OracleKind.SEMANTIC,
    True,
    "clear",
    "clear",
    confidence=0.9,
    provenance=(EvidenceReference("oracle-response", "memory://x"),),
)


@pytest.mark.parametrize("value", ["run-1", "A.b_c-9", "x" * 64])
def test_safe_identifiers_are_accepted(value: str) -> None:
    assert is_safe_identifier(value)


@pytest.mark.parametrize("value", ["", "..", "a/b", "a\\b", "-x", ".x", "a b", "x" * 65, "a\n"])
def test_unsafe_identifiers_are_rejected(value: str) -> None:
    assert not is_safe_identifier(value)


def test_passed_result_requires_a_deterministic_verdict_and_evidence() -> None:
    assert ScenarioResult("s", Outcome.PASSED, 1, _EVIDENCE, (_PASS,)).outcome is Outcome.PASSED
    with pytest.raises(ValueError, match="deterministic verdict"):
        ScenarioResult("s", Outcome.PASSED, 1, _EVIDENCE, ())
    with pytest.raises(ValueError, match="deterministic verdict"):
        ScenarioResult("s", Outcome.PASSED, 1, _EVIDENCE, (_SEMANTIC_PASS,))
    with pytest.raises(ValueError, match="require evidence"):
        ScenarioResult("s", Outcome.PASSED, 1, (), (_PASS,))


def test_semantic_verdict_cannot_override_a_failed_deterministic_verdict() -> None:
    with pytest.raises(ValueError, match="cannot be overridden"):
        ScenarioResult("s", Outcome.PASSED, 1, _EVIDENCE, (_FAIL, _SEMANTIC_PASS))


def test_passed_result_cannot_carry_a_failure_reason() -> None:
    with pytest.raises(ValueError, match="cannot carry"):
        ScenarioResult("s", Outcome.PASSED, 1, _EVIDENCE, (_PASS,), "oops")


@pytest.mark.parametrize("outcome", [Outcome.FAILED, Outcome.BLOCKED, Outcome.ERROR])
def test_non_passing_results_require_a_reason(outcome: Outcome) -> None:
    with pytest.raises(ValueError, match="require a failure reason"):
        ScenarioResult("s", outcome, 1, _EVIDENCE)


def test_failed_results_require_evidence() -> None:
    with pytest.raises(ValueError, match="failed results require evidence"):
        ScenarioResult("s", Outcome.FAILED, 1, (), failure_reason="bad")


def test_result_validates_identifier_and_duration() -> None:
    with pytest.raises(ValueError, match="identifier"):
        ScenarioResult("../s", Outcome.BLOCKED, 0, failure_reason="x")
    with pytest.raises(ValueError, match="non-negative"):
        ScenarioResult("s", Outcome.BLOCKED, -1, failure_reason="x")


def test_verdict_rejects_a_negative_step_index() -> None:
    with pytest.raises(ValueError, match="step_index"):
        OracleVerdict(OracleKind.DETERMINISTIC, True, "a", "b", step_index=-1)


def test_run_result_validates_its_contract() -> None:
    blocked = ScenarioResult("s", Outcome.BLOCKED, 0, failure_reason="x")
    with pytest.raises(ValueError, match="run id"):
        RunResult("../r", "REQ", (blocked,), 1)
    with pytest.raises(ValueError, match="requirement_id"):
        RunResult("r", " ", (blocked,), 1)
    with pytest.raises(ValueError, match="scenario results"):
        RunResult("r", "REQ", (), 1)
    with pytest.raises(ValueError, match="unique"):
        RunResult("r", "REQ", (blocked, blocked), 1)
    with pytest.raises(ValueError, match="non-negative"):
        RunResult("r", "REQ", (blocked,), -1)
