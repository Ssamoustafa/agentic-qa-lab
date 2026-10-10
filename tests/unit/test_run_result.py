from __future__ import annotations

import json
from pathlib import Path

from agentic_qa.domain.models import (
    EvidenceReference,
    OracleKind,
    OracleVerdict,
    Outcome,
    RunResult,
    ScenarioResult,
)
from agentic_qa.infrastructure.evidence.run_result import (
    SCHEMA_VERSION,
    JsonRunResultWriter,
    serialize_run_result,
)
from agentic_qa.infrastructure.evidence.store import FilesystemEvidenceStore

_EVIDENCE = (EvidenceReference("screenshot", "run-1/a/final.png", "b" * 64),)
_PASS = OracleVerdict(OracleKind.DETERMINISTIC, True, "visible", "visible", step_index=0)


def _passed(scenario_id: str) -> ScenarioResult:
    return ScenarioResult(scenario_id, Outcome.PASSED, 5, _EVIDENCE, (_PASS,))


def _failed(scenario_id: str) -> ScenarioResult:
    return ScenarioResult(scenario_id, Outcome.FAILED, 5, _EVIDENCE, failure_reason="bad")


def test_serialization_is_stable_and_summarizes_outcomes() -> None:
    run = RunResult("run-1", "REQ-1", (_passed("a"), _failed("b")), 12)

    document = serialize_run_result(run)

    assert document["schema_version"] == SCHEMA_VERSION
    assert document["outcome"] == "failed"
    assert document["summary"] == {
        "total": 2,
        "passed": 1,
        "failed": 1,
        "blocked": 0,
        "error": 0,
    }
    scenarios = document["scenarios"]
    assert isinstance(scenarios, list)
    assert scenarios[0]["verdicts"][0]["oracle"] == "deterministic"
    assert scenarios[0]["evidence"][0]["sha256"] == "b" * 64


def test_writer_persists_json_inside_the_run_directory(tmp_path: Path) -> None:
    store = FilesystemEvidenceStore(tmp_path)
    run = RunResult("run-1", "REQ-1", (_passed("a"),), 3)

    path = JsonRunResultWriter(store).write(run)

    assert path == store.root / "run-1" / "run-result.json"
    assert json.loads(path.read_text())["outcome"] == "passed"


def test_run_outcome_uses_the_most_severe_scenario_outcome() -> None:
    blocked = ScenarioResult("c", Outcome.BLOCKED, 0, failure_reason="policy")
    error = ScenarioResult("d", Outcome.ERROR, 0, failure_reason="boom")

    assert RunResult("r", "R", (_passed("a"),), 1).outcome is Outcome.PASSED
    assert RunResult("r", "R", (_passed("a"), blocked), 1).outcome is Outcome.BLOCKED
    assert RunResult("r", "R", (blocked, _failed("b")), 1).outcome is Outcome.FAILED
    assert RunResult("r", "R", (_failed("b"), error), 1).outcome is Outcome.ERROR
