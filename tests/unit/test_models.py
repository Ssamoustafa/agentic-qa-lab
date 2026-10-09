from __future__ import annotations

import pytest

from agentic_qa.domain.models import (
    Action,
    EvidenceReference,
    ExecutionBudget,
    OracleKind,
    OracleVerdict,
    PolicyDecision,
    PolicyViolation,
    Risk,
    RiskLevel,
)
from agentic_qa.domain.models import (
    TestPlan as Plan,
)
from agentic_qa.domain.models import (
    TestScenario as Scenario,
)
from agentic_qa.domain.models import (
    TestStep as Step,
)


def _scenario(scenario_id: str = "scenario-1") -> Scenario:
    return Scenario(
        scenario_id=scenario_id,
        title="Primary journey",
        risk=RiskLevel.MEDIUM,
        steps=(Step(Action.ASSERT_VISIBLE, "main"),),
    )


def _risk() -> Risk:
    return Risk("checkout", RiskLevel.HIGH, "stateful payment flow")


@pytest.mark.parametrize(
    ("action", "value"),
    [
        (Action.FILL, None),
        (Action.ASSERT_TEXT, None),
        (Action.NAVIGATE, "unexpected"),
    ],
)
def test_step_enforces_its_value_contract(action: Action, value: str | None) -> None:
    with pytest.raises(ValueError):
        Step(action, "target", value)


def test_scenario_rejects_blank_acceptance_criteria() -> None:
    with pytest.raises(ValueError, match="acceptance criteria"):
        Scenario(
            scenario_id="scenario-1",
            title="Primary journey",
            risk=RiskLevel.LOW,
            steps=(Step(Action.ASSERT_VISIBLE, "main"),),
            acceptance_criteria=("",),
        )


def test_plan_rejects_duplicate_scenario_ids() -> None:
    with pytest.raises(ValueError, match="scenario ids"):
        Plan("requirement-1", (_risk(),), (_scenario(), _scenario()))


@pytest.mark.parametrize(
    ("max_steps", "max_duration_seconds"),
    [(0, 30), (5, 0)],
)
def test_execution_budget_must_be_positive(max_steps: int, max_duration_seconds: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        ExecutionBudget(max_steps=max_steps, max_duration_seconds=max_duration_seconds)


def test_evidence_reference_validates_required_fields_and_hash() -> None:
    with pytest.raises(ValueError, match="kind and location"):
        EvidenceReference("", "memory://result")
    with pytest.raises(ValueError, match="64-character"):
        EvidenceReference("trace", "memory://result", "not-a-sha")

    evidence = EvidenceReference("trace", "memory://result", "a" * 64)

    assert evidence.sha256 == "a" * 64


def test_semantic_oracle_requires_provenance() -> None:
    with pytest.raises(ValueError, match="require provenance"):
        OracleVerdict(OracleKind.SEMANTIC, True, "clear", "clear", confidence=0.8)
    with pytest.raises(ValueError, match="must be 1.0"):
        OracleVerdict(OracleKind.DETERMINISTIC, True, "1", "1", confidence=0.9)

    verdict = OracleVerdict(
        OracleKind.SEMANTIC,
        True,
        "clear",
        "clear",
        confidence=0.8,
        provenance=(EvidenceReference("oracle-response", "memory://semantic-response"),),
    )

    assert verdict.provenance[0].kind == "oracle-response"


def test_policy_decision_requires_consistent_state() -> None:
    violation = PolicyViolation("action_allowlist", "click is not allowed")
    with pytest.raises(ValueError, match="cannot include"):
        PolicyDecision(True, (violation,))
    with pytest.raises(ValueError, match="require violations"):
        PolicyDecision(False)

    assert PolicyDecision(False, (violation,)).violations == (violation,)
