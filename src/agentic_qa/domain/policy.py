from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from agentic_qa.domain.models import (
    Action,
    ExecutionBudget,
    ExecutionConstraints,
    PolicyDecision,
    PolicyViolation,
    RiskLevel,
    TestScenario,
)

_ALLOWED_NAVIGATION_SCHEMES = frozenset({"http", "https"})
_RISK_RANKS = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


@dataclass(frozen=True, slots=True)
class ScenarioPolicy:
    allowed_hosts: frozenset[str]
    allowed_actions: frozenset[Action]
    budget: ExecutionBudget
    maximum_risk_level: RiskLevel = RiskLevel.CRITICAL

    @property
    def constraints(self) -> ExecutionConstraints:
        return ExecutionConstraints(self.allowed_hosts, self.budget)

    def evaluate(self, scenario: TestScenario) -> PolicyDecision:
        violations: list[PolicyViolation] = []

        if _RISK_RANKS[scenario.risk] > _RISK_RANKS[self.maximum_risk_level]:
            violations.append(
                PolicyViolation(
                    "risk_policy",
                    f"{scenario.risk.value} risk exceeds {self.maximum_risk_level.value} threshold",
                )
            )

        if len(scenario.steps) > self.budget.max_steps:
            violations.append(
                PolicyViolation(
                    "action_budget",
                    f"{len(scenario.steps)} steps exceeds budget {self.budget.max_steps}",
                )
            )

        for step in scenario.steps:
            if step.action not in self.allowed_actions:
                violations.append(
                    PolicyViolation("action_allowlist", f"{step.action.value} is not allowed")
                )
            if step.action is Action.NAVIGATE:
                parsed = urlparse(step.target)
                host = parsed.hostname
                if (
                    parsed.scheme not in _ALLOWED_NAVIGATION_SCHEMES
                    or host is None
                    or parsed.username is not None
                    or parsed.password is not None
                ):
                    violations.append(
                        PolicyViolation(
                            "navigation_target",
                            "navigation must use an absolute HTTP(S) URL without credentials",
                        )
                    )
                elif host not in self.allowed_hosts:
                    violations.append(
                        PolicyViolation("host_allowlist", f"host {host!r} is not allowed")
                    )

        return PolicyDecision(allowed=not violations, violations=tuple(violations))
