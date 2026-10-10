from __future__ import annotations

import time
from dataclasses import dataclass, replace

from agentic_qa.application.ports import EvidenceVerifier, RiskAnalyzer, ScenarioExecutor
from agentic_qa.domain.models import (
    Outcome,
    Requirement,
    Risk,
    RunResult,
    ScenarioResult,
    TestPlan,
    TestScenario,
)
from agentic_qa.domain.policy import ScenarioPolicy

_MAX_REASON_LENGTH = 300


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    requirement: Requirement
    risks: tuple[Risk, ...]

    def __post_init__(self) -> None:
        if not self.risks:
            raise ValueError("risk assessment must contain at least one risk")


class AssessRequirementRisk:
    def __init__(self, risk_analyzer: RiskAnalyzer) -> None:
        self._risk_analyzer = risk_analyzer

    def execute(self, requirement: Requirement) -> RiskAssessment:
        return RiskAssessment(requirement, self._risk_analyzer.analyze(requirement))


class ExecuteTestPlan:
    """The only path from a typed plan to an executor: policy first, then verified execution."""

    def __init__(
        self,
        policy: ScenarioPolicy,
        executor: ScenarioExecutor,
        verifier: EvidenceVerifier,
    ) -> None:
        self._policy = policy
        self._executor = executor
        self._verifier = verifier

    def execute(self, plan: TestPlan, *, run_id: str) -> RunResult:
        started = time.perf_counter()
        results = tuple(self._run_scenario(scenario, run_id) for scenario in plan.scenarios)
        duration_ms = round((time.perf_counter() - started) * 1000)
        return RunResult(run_id, plan.requirement_id, results, duration_ms)

    def _run_scenario(self, scenario: TestScenario, run_id: str) -> ScenarioResult:
        decision = self._policy.evaluate(scenario)
        if not decision.allowed:
            reason = "; ".join(f"{v.rule}: {v.reason}" for v in decision.violations)
            return ScenarioResult(scenario.scenario_id, Outcome.BLOCKED, 0, failure_reason=reason)

        started = time.perf_counter()
        try:
            result = self._executor.execute(
                scenario, run_id=run_id, constraints=self._policy.constraints
            )
        except Exception as exc:
            return self._error(scenario, started, f"executor error: {type(exc).__name__}: {exc}")

        if result.scenario_id != scenario.scenario_id:
            return self._error(scenario, started, "executor returned a result for another scenario")
        problems = self._verifier.problems(result)
        if problems:
            reason = "evidence verification failed: " + "; ".join(problems)
            return replace(
                result, outcome=Outcome.ERROR, failure_reason=reason[:_MAX_REASON_LENGTH]
            )
        return result

    @staticmethod
    def _error(scenario: TestScenario, started: float, reason: str) -> ScenarioResult:
        duration_ms = round((time.perf_counter() - started) * 1000)
        return ScenarioResult(
            scenario.scenario_id,
            Outcome.ERROR,
            duration_ms,
            failure_reason=reason[:_MAX_REASON_LENGTH],
        )
