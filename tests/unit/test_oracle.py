from __future__ import annotations

from agentic_qa.domain.models import OracleKind
from agentic_qa.domain.oracle import (
    evaluate_contains_text,
    evaluate_http_status,
    evaluate_visibility,
)


def test_http_status_below_400_passes() -> None:
    verdict = evaluate_http_status("https://safe.example", 200, step_index=0)

    assert verdict.passed
    assert verdict.oracle is OracleKind.DETERMINISTIC
    assert verdict.confidence == 1.0
    assert verdict.actual == "200"
    assert verdict.step_index == 0


def test_http_error_status_fails() -> None:
    assert not evaluate_http_status("https://safe.example", 404, step_index=1).passed
    assert not evaluate_http_status("https://safe.example", 500, step_index=1).passed


def test_visibility_verdict_reports_the_observation() -> None:
    assert evaluate_visibility("#a", visible=True, step_index=2).actual == "visible"
    failed = evaluate_visibility("#a", visible=False, step_index=2)

    assert not failed.passed
    assert failed.actual == "not visible"


def test_text_containment_is_exact_and_case_sensitive() -> None:
    assert evaluate_contains_text(
        "#a", expected="Hello", actual="Hello, Sarah", step_index=0
    ).passed
    assert not evaluate_contains_text(
        "#a", expected="hello", actual="Hello, Sarah", step_index=0
    ).passed


def test_long_observations_are_truncated() -> None:
    verdict = evaluate_contains_text("#a", expected="x", actual="y" * 5000, step_index=0)

    assert len(verdict.actual) < 600
    assert verdict.actual.endswith("[truncated]")
    assert not verdict.passed
