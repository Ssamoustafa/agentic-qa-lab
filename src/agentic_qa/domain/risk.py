from __future__ import annotations

from agentic_qa.domain.models import Requirement, Risk, RiskLevel

_KEYWORDS: tuple[tuple[tuple[str, ...], RiskLevel, str], ...] = (
    (("payment", "card", "checkout"), RiskLevel.CRITICAL, "financial transaction surface"),
    (("auth", "login", "password", "token"), RiskLevel.CRITICAL, "authentication surface"),
    (("privacy", "personal", "user data"), RiskLevel.CRITICAL, "sensitive data surface"),
    (("order", "account", "profile"), RiskLevel.HIGH, "stateful customer workflow"),
)


class KeywordRiskAnalyzer:
    """Deterministic baseline used to benchmark richer risk analyzers."""

    def analyze(self, requirement: Requirement) -> tuple[Risk, ...]:
        text = requirement.text.lower()
        risks: list[Risk] = []
        for keywords, level, rationale in _KEYWORDS:
            if any(keyword in text for keyword in keywords):
                risks.append(Risk("/".join(keywords), level, rationale))
        if not risks:
            risks.append(Risk("general", RiskLevel.MEDIUM, "unclassified functional change"))
        return tuple(risks)
