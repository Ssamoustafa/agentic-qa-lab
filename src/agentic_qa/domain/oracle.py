from __future__ import annotations

from agentic_qa.domain.models import OracleKind, OracleVerdict

_MAX_ACTUAL_LENGTH = 500


def _truncate(value: str) -> str:
    if len(value) <= _MAX_ACTUAL_LENGTH:
        return value
    return value[:_MAX_ACTUAL_LENGTH] + "...[truncated]"


def evaluate_http_status(url: str, status: int, *, step_index: int) -> OracleVerdict:
    return OracleVerdict(
        OracleKind.DETERMINISTIC,
        passed=status < 400,
        expected=f"HTTP status below 400 for {url}",
        actual=str(status),
        step_index=step_index,
    )


def evaluate_visibility(target: str, *, visible: bool, step_index: int) -> OracleVerdict:
    return OracleVerdict(
        OracleKind.DETERMINISTIC,
        passed=visible,
        expected=f"{target} is visible",
        actual="visible" if visible else "not visible",
        step_index=step_index,
    )


def evaluate_contains_text(
    target: str, *, expected: str, actual: str, step_index: int
) -> OracleVerdict:
    return OracleVerdict(
        OracleKind.DETERMINISTIC,
        passed=expected in actual,
        expected=f"{target} contains {_truncate(expected)!r}",
        actual=_truncate(actual),
        step_index=step_index,
    )
