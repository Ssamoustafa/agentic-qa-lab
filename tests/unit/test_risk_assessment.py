from __future__ import annotations

import pytest

from agentic_qa.application.use_cases import AssessRequirementRisk
from agentic_qa.domain.models import Requirement, Risk, RiskLevel


class StaticRiskAnalyzer:
    def __init__(self, risks: tuple[Risk, ...]) -> None:
        self._risks = risks

    def analyze(self, requirement: Requirement) -> tuple[Risk, ...]:
        if not requirement.requirement_id:
            raise AssertionError("requirements passed to the analyzer must be identified")
        return self._risks


def test_assessment_preserves_the_requirement_and_risks() -> None:
    requirement = Requirement("REQ-001", "Protect customer payments")
    risks = (Risk("payments", RiskLevel.CRITICAL, "financial transaction surface"),)

    assessment = AssessRequirementRisk(StaticRiskAnalyzer(risks)).execute(requirement)

    assert assessment.requirement is requirement
    assert assessment.risks == risks


def test_assessment_rejects_an_empty_analyzer_result() -> None:
    requirement = Requirement("REQ-001", "Protect customer payments")

    with pytest.raises(ValueError, match="at least one risk"):
        AssessRequirementRisk(StaticRiskAnalyzer(())).execute(requirement)
