from __future__ import annotations

from typing import Protocol

from agentic_qa.domain.models import (
    ExecutionConstraints,
    Requirement,
    Risk,
    ScenarioResult,
    TestScenario,
)


class RiskAnalyzer(Protocol):
    def analyze(self, requirement: Requirement) -> tuple[Risk, ...]: ...


class ScenarioExecutor(Protocol):
    """Executes one already-approved scenario inside the given runtime constraints."""

    def execute(
        self, scenario: TestScenario, *, run_id: str, constraints: ExecutionConstraints
    ) -> ScenarioResult: ...


class EvidenceVerifier(Protocol):
    def problems(self, result: ScenarioResult) -> tuple[str, ...]:
        """Describe every evidence reference that is missing or does not match its digest."""
        ...
