from __future__ import annotations

from agentic_qa.application.use_cases import ExecuteTestPlan
from agentic_qa.domain.models import (
    Action,
    EvidenceReference,
    ExecutionBudget,
    ExecutionConstraints,
    OracleKind,
    OracleVerdict,
    Outcome,
    Risk,
    RiskLevel,
    ScenarioResult,
)
from agentic_qa.domain.models import TestPlan as Plan
from agentic_qa.domain.models import TestScenario as Scenario
from agentic_qa.domain.models import TestStep as Step
from agentic_qa.domain.policy import ScenarioPolicy

_EVIDENCE = (EvidenceReference("screenshot", "run-1/s/final.png", "c" * 64),)


def _policy() -> ScenarioPolicy:
    return ScenarioPolicy(
        frozenset({"safe.example"}), frozenset(Action), ExecutionBudget(max_steps=5)
    )


def _scenario(scenario_id: str, url: str = "https://safe.example") -> Scenario:
    return Scenario(scenario_id, "t", RiskLevel.LOW, (Step(Action.NAVIGATE, url),))


def _plan(*scenarios: Scenario) -> Plan:
    return Plan("REQ-1", (Risk("area", RiskLevel.LOW, "why"),), scenarios)


class _Executor:
    def __init__(self, behavior: str = "pass") -> None:
        self.behavior = behavior
        self.calls: list[tuple[str, ExecutionConstraints]] = []

    def execute(
        self, scenario: Scenario, *, run_id: str, constraints: ExecutionConstraints
    ) -> ScenarioResult:
        self.calls.append((scenario.scenario_id, constraints))
        if self.behavior == "raise":
            raise RuntimeError("browser crashed")
        scenario_id = "other" if self.behavior == "wrong-id" else scenario.scenario_id
        verdict = OracleVerdict(OracleKind.DETERMINISTIC, True, "ok", "ok", step_index=0)
        return ScenarioResult(scenario_id, Outcome.PASSED, 1, _EVIDENCE, (verdict,))


class _Verifier:
    def __init__(self, problems: tuple[str, ...] = ()) -> None:
        self._problems = problems

    def problems(self, result: ScenarioResult) -> tuple[str, ...]:
        return self._problems


def _run(executor: _Executor, verifier: _Verifier, *scenarios: Scenario) -> list[ScenarioResult]:
    return list(
        ExecuteTestPlan(_policy(), executor, verifier)
        .execute(_plan(*scenarios), run_id="r1")
        .results
    )


def test_policy_blocked_scenario_never_reaches_the_executor() -> None:
    executor = _Executor()

    results = _run(executor, _Verifier(), _scenario("bad", "https://evil.example"))

    assert results[0].outcome is Outcome.BLOCKED
    assert "host_allowlist" in (results[0].failure_reason or "")
    assert executor.calls == []


def test_allowed_scenario_runs_with_the_policy_constraints() -> None:
    executor = _Executor()

    results = _run(executor, _Verifier(), _scenario("good"))

    assert results[0].outcome is Outcome.PASSED
    assert executor.calls[0][1] == _policy().constraints


def test_blocked_scenarios_do_not_stop_the_rest_of_the_plan() -> None:
    executor = _Executor()

    results = _run(executor, _Verifier(), _scenario("bad", "https://evil.example"), _scenario("ok"))

    assert [r.outcome for r in results] == [Outcome.BLOCKED, Outcome.PASSED]


def test_executor_exception_becomes_an_error_result() -> None:
    results = _run(_Executor("raise"), _Verifier(), _scenario("good"))

    assert results[0].outcome is Outcome.ERROR
    assert "RuntimeError" in (results[0].failure_reason or "")


def test_result_for_another_scenario_is_rejected() -> None:
    results = _run(_Executor("wrong-id"), _Verifier(), _scenario("good"))

    assert results[0].outcome is Outcome.ERROR
    assert "another scenario" in (results[0].failure_reason or "")


def test_unverifiable_evidence_downgrades_a_pass_to_an_error() -> None:
    results = _run(_Executor(), _Verifier(("screenshot is missing",)), _scenario("good"))

    assert results[0].outcome is Outcome.ERROR
    assert "evidence verification failed" in (results[0].failure_reason or "")


def test_run_result_carries_plan_identity_and_duration() -> None:
    run = ExecuteTestPlan(_policy(), _Executor(), _Verifier()).execute(
        _plan(_scenario("good")), run_id="r1"
    )

    assert (run.run_id, run.requirement_id) == ("r1", "REQ-1")
    assert run.duration_ms >= 0
