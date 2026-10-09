from __future__ import annotations

from typing import Protocol

from agentic_qa.domain.models import Requirement, Risk


class RiskAnalyzer(Protocol):
    def analyze(self, requirement: Requirement) -> tuple[Risk, ...]: ...
