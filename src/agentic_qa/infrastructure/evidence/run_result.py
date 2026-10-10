from __future__ import annotations

from pathlib import Path

from agentic_qa.domain.models import OracleVerdict, Outcome, RunResult, ScenarioResult
from agentic_qa.infrastructure.evidence.store import FilesystemEvidenceStore

SCHEMA_VERSION = "1"


def _verdict(verdict: OracleVerdict) -> dict[str, object]:
    return {
        "oracle": verdict.oracle.value,
        "passed": verdict.passed,
        "expected": verdict.expected,
        "actual": verdict.actual,
        "confidence": verdict.confidence,
        "step_index": verdict.step_index,
    }


def _scenario(result: ScenarioResult) -> dict[str, object]:
    return {
        "scenario_id": result.scenario_id,
        "outcome": result.outcome.value,
        "duration_ms": result.duration_ms,
        "failure_reason": result.failure_reason,
        "evidence": [
            {"kind": ref.kind, "location": ref.location, "sha256": ref.sha256}
            for ref in result.evidence
        ],
        "verdicts": [_verdict(verdict) for verdict in result.verdicts],
    }


def serialize_run_result(result: RunResult) -> dict[str, object]:
    counts = {outcome.value: 0 for outcome in Outcome}
    for scenario in result.results:
        counts[scenario.outcome.value] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": result.run_id,
        "requirement_id": result.requirement_id,
        "outcome": result.outcome.value,
        "duration_ms": result.duration_ms,
        "summary": {"total": len(result.results), **counts},
        "scenarios": [_scenario(scenario) for scenario in result.results],
    }


class JsonRunResultWriter:
    def __init__(self, store: FilesystemEvidenceStore) -> None:
        self._store = store

    def write(self, result: RunResult) -> Path:
        directory = self._store.run_directory(result.run_id)
        return self._store.write_json(directory, "run-result.json", serialize_run_result(result))
