from agentic_qa.domain.models import (
    Action,
    ExecutionBudget,
    RiskLevel,
)
from agentic_qa.domain.models import TestScenario as Scenario
from agentic_qa.domain.models import TestStep as Step
from agentic_qa.domain.policy import ScenarioPolicy


def test_policy_blocks_unapproved_host() -> None:
    policy = ScenarioPolicy(
        frozenset({"safe.example"}),
        frozenset(Action),
        ExecutionBudget(max_steps=5),
    )
    scenario = Scenario(
        "s1",
        "Unsafe navigation",
        RiskLevel.HIGH,
        (Step(Action.NAVIGATE, "https://evil.example"),),
    )

    decision = policy.evaluate(scenario)

    assert not decision.allowed
    assert decision.violations[0].rule == "host_allowlist"


def test_policy_enforces_action_budget() -> None:
    policy = ScenarioPolicy(
        frozenset({"safe.example"}),
        frozenset(Action),
        ExecutionBudget(max_steps=1),
    )
    scenario = Scenario(
        "s1",
        "Too many actions",
        RiskLevel.MEDIUM,
        (
            Step(Action.NAVIGATE, "https://safe.example"),
            Step(Action.ASSERT_VISIBLE, "body"),
        ),
    )

    assert not policy.evaluate(scenario).allowed


def test_policy_blocks_disallowed_action() -> None:
    policy = ScenarioPolicy(
        frozenset({"safe.example"}),
        frozenset({Action.NAVIGATE}),
        ExecutionBudget(max_steps=5),
    )
    scenario = Scenario(
        "s1",
        "Restricted action",
        RiskLevel.MEDIUM,
        (Step(Action.CLICK, "button[type=submit]"),),
    )

    decision = policy.evaluate(scenario)

    assert not decision.allowed
    assert decision.violations[0].rule == "action_allowlist"


def test_policy_blocks_risk_above_its_threshold() -> None:
    policy = ScenarioPolicy(
        frozenset({"safe.example"}),
        frozenset(Action),
        ExecutionBudget(max_steps=5),
        maximum_risk_level=RiskLevel.HIGH,
    )

    scenario = Scenario(
        "s1",
        "Critical workflow",
        RiskLevel.CRITICAL,
        (Step(Action.NAVIGATE, "https://safe.example"),),
    )

    decision = policy.evaluate(scenario)

    assert not decision.allowed
    assert decision.violations[0].rule == "risk_policy"


def test_policy_allows_a_conforming_scenario() -> None:
    policy = ScenarioPolicy(
        frozenset({"safe.example"}),
        frozenset(Action),
        ExecutionBudget(max_steps=5),
    )
    scenario = Scenario(
        "s1",
        "Allowed navigation",
        RiskLevel.LOW,
        (Step(Action.NAVIGATE, "https://safe.example"),),
    )

    assert policy.evaluate(scenario).allowed


def test_policy_blocks_navigation_without_an_allowed_http_host() -> None:
    policy = ScenarioPolicy(
        frozenset({"safe.example"}),
        frozenset(Action),
        ExecutionBudget(max_steps=5),
    )
    scenario = Scenario(
        "s1",
        "Malformed navigation",
        RiskLevel.HIGH,
        (Step(Action.NAVIGATE, "javascript:alert('untrusted')"),),
    )

    decision = policy.evaluate(scenario)

    assert not decision.allowed
    assert decision.violations[0].rule == "navigation_target"
