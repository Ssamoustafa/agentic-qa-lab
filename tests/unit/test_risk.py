from agentic_qa.domain.models import Requirement, RiskLevel
from agentic_qa.domain.risk import KeywordRiskAnalyzer


def test_payment_requirement_is_critical() -> None:
    risks = KeywordRiskAnalyzer().analyze(
        Requirement("R1", "Allow customers to save a payment card at checkout")
    )

    assert any(risk.level is RiskLevel.CRITICAL for risk in risks)
