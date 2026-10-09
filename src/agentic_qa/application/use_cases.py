from __future__ import annotations

from dataclasses import dataclass

from agentic_qa.application.ports import RiskAnalyzer
from agentic_qa.domain.models import Requirement, Risk


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
