from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_qa.domain.models import (
    Action,
    ExecutionBudget,
    ExecutionConstraints,
    OracleKind,
    Outcome,
    RiskLevel,
    ScenarioResult,
)
from agentic_qa.domain.models import TestScenario as Scenario
from agentic_qa.domain.models import TestStep as Step

pytest.importorskip("playwright.sync_api")

from agentic_qa.infrastructure.evidence.store import FilesystemEvidenceStore  # noqa: E402
from agentic_qa.infrastructure.execution.playwright_executor import (  # noqa: E402
    PlaywrightScenarioExecutor,
)
from tests.integration.fixture_site import fixture_site  # noqa: E402

pytestmark = pytest.mark.browser

RUN_ID = "run-1"


@pytest.fixture(scope="module")
def site() -> str:
    with fixture_site() as base_url:
        yield base_url


@pytest.fixture
def store(tmp_path: Path) -> FilesystemEvidenceStore:
    return FilesystemEvidenceStore(tmp_path / "artifacts")


@pytest.fixture
def executor(store: FilesystemEvidenceStore) -> PlaywrightScenarioExecutor:
    return PlaywrightScenarioExecutor(store, step_timeout_ms=1000)


def _constraints(max_duration_seconds: int = 30) -> ExecutionConstraints:
    return ExecutionConstraints(
        frozenset({"127.0.0.1"}),
        ExecutionBudget(max_steps=20, max_duration_seconds=max_duration_seconds),
    )


def _scenario(scenario_id: str, *steps: Step) -> Scenario:
    return Scenario(scenario_id, "scenario under test", RiskLevel.LOW, steps)


def _run(
    executor: PlaywrightScenarioExecutor,
    scenario: Scenario,
    constraints: ExecutionConstraints | None = None,
) -> ScenarioResult:
    return executor.execute(scenario, run_id=RUN_ID, constraints=constraints or _constraints())


def test_user_journey_passes_with_verifiable_evidence(
    executor: PlaywrightScenarioExecutor, store: FilesystemEvidenceStore, site: str
) -> None:
    scenario = _scenario(
        "journey",
        Step(Action.NAVIGATE, site + "/"),
        Step(Action.FILL, "#name", "Sarah"),
        Step(Action.CLICK, "#go"),
        Step(Action.ASSERT_TEXT, "#greeting", "Hello, Sarah"),
        Step(Action.ASSERT_VISIBLE, "#title"),
    )

    result = _run(executor, scenario)

    assert result.outcome is Outcome.PASSED, result.failure_reason
    assert [v.step_index for v in result.verdicts] == [0, 3, 4]
    assert all(v.oracle is OracleKind.DETERMINISTIC and v.passed for v in result.verdicts)
    assert {e.kind for e in result.evidence} == {"screenshot", "playwright_trace", "console"}
    assert store.problems(result) == ()
    assert result.duration_ms > 0


def test_failed_text_assertion_records_verdict_and_failure_evidence(
    executor: PlaywrightScenarioExecutor, store: FilesystemEvidenceStore, site: str
) -> None:
    scenario = _scenario(
        "wrong-text",
        Step(Action.NAVIGATE, site + "/"),
        Step(Action.ASSERT_TEXT, "#title", "Goodbye"),
    )

    result = _run(executor, scenario)

    assert result.outcome is Outcome.FAILED
    failed = [v for v in result.verdicts if not v.passed]
    assert failed and failed[0].step_index == 1
    assert failed[0].actual == "Welcome"
    assert any(e.kind == "screenshot" for e in result.evidence)
    assert store.problems(result) == ()


def test_hidden_element_fails_visibility_oracle(
    executor: PlaywrightScenarioExecutor, site: str
) -> None:
    scenario = _scenario(
        "hidden",
        Step(Action.NAVIGATE, site + "/"),
        Step(Action.ASSERT_VISIBLE, "#hidden"),
    )

    result = _run(executor, scenario)

    assert result.outcome is Outcome.FAILED
    assert result.verdicts[-1].actual == "not visible"


def test_missing_element_fails_without_hanging(
    executor: PlaywrightScenarioExecutor, site: str
) -> None:
    scenario = _scenario(
        "no-element",
        Step(Action.NAVIGATE, site + "/"),
        Step(Action.CLICK, "#does-not-exist"),
    )

    result = _run(executor, scenario)

    assert result.outcome is Outcome.FAILED
    assert result.failure_reason is not None and "step 1" in result.failure_reason


def test_http_error_status_fails_deterministic_oracle(
    executor: PlaywrightScenarioExecutor, site: str
) -> None:
    scenario = _scenario(
        "not-found",
        Step(Action.NAVIGATE, site + "/missing"),
        Step(Action.ASSERT_VISIBLE, "#title"),
    )

    result = _run(executor, scenario)

    assert result.outcome is Outcome.FAILED
    assert result.verdicts[0].actual == "404"


def test_redirect_to_unlisted_host_is_blocked_at_runtime(
    executor: PlaywrightScenarioExecutor, store: FilesystemEvidenceStore, site: str
) -> None:
    scenario = _scenario(
        "redirect",
        Step(Action.NAVIGATE, site + "/redirect-out"),
        Step(Action.ASSERT_VISIBLE, "#title"),
    )

    result = _run(executor, scenario)

    assert result.outcome is Outcome.FAILED
    assert result.failure_reason is not None and "localhost" in result.failure_reason
    console = next(e for e in result.evidence if e.kind == "console")
    payload = json.loads((store.root / console.location).read_text())
    assert any("localhost" in url for url in payload["blocked_requests"])


def test_third_party_subresource_is_blocked_and_fails_the_scenario(
    executor: PlaywrightScenarioExecutor, site: str
) -> None:
    scenario = _scenario(
        "third-party",
        Step(Action.NAVIGATE, site + "/third-party"),
        Step(Action.ASSERT_VISIBLE, "#title"),
    )

    result = _run(executor, scenario)

    assert result.outcome is Outcome.FAILED
    assert result.failure_reason is not None and "egress blocked" in result.failure_reason


def test_websocket_to_unlisted_host_is_blocked(
    executor: PlaywrightScenarioExecutor, site: str
) -> None:
    scenario = _scenario(
        "websocket",
        Step(Action.NAVIGATE, site + "/websocket"),
        Step(Action.ASSERT_VISIBLE, "#closed"),
    )

    result = _run(executor, scenario)

    assert result.outcome is Outcome.FAILED
    assert result.failure_reason is not None and "egress blocked" in result.failure_reason


def test_websocket_to_allowed_host_is_also_blocked(
    executor: PlaywrightScenarioExecutor, site: str
) -> None:
    scenario = _scenario(
        "websocket-same-host",
        Step(Action.NAVIGATE, site + "/websocket-same-host"),
        Step(Action.ASSERT_VISIBLE, "#title"),
    )

    result = _run(executor, scenario)

    assert result.outcome is Outcome.FAILED
    assert result.failure_reason is not None and "egress blocked" in result.failure_reason


def test_duration_budget_is_enforced_at_runtime(store: FilesystemEvidenceStore, site: str) -> None:
    executor = PlaywrightScenarioExecutor(store, step_timeout_ms=10_000)
    scenario = _scenario(
        "slow",
        Step(Action.NAVIGATE, site + "/slow"),
        Step(Action.ASSERT_VISIBLE, "#title"),
    )

    result = _run(executor, scenario, _constraints(max_duration_seconds=1))

    assert result.outcome is Outcome.FAILED
    assert result.failure_reason == "duration budget exceeded"
    assert result.duration_ms < 2500
    assert {"playwright_trace", "console"} <= {e.kind for e in result.evidence}
    assert store.problems(result) == ()


def test_page_console_errors_are_captured_as_evidence(
    executor: PlaywrightScenarioExecutor, store: FilesystemEvidenceStore, site: str
) -> None:
    scenario = _scenario(
        "console",
        Step(Action.NAVIGATE, site + "/console-error"),
        Step(Action.ASSERT_VISIBLE, "#title"),
    )

    result = _run(executor, scenario)

    console = next(e for e in result.evidence if e.kind == "console")
    payload = json.loads((store.root / console.location).read_text())
    assert any(entry["text"] == "boom" for entry in payload["console"])
    assert any("page-crash" in error for error in payload["page_errors"])


def test_scenarios_do_not_share_browser_state(
    executor: PlaywrightScenarioExecutor, site: str
) -> None:
    visit = Step(Action.NAVIGATE, site + "/")
    first = _scenario("first", visit, Step(Action.ASSERT_TEXT, "#visited", "no"))
    second = _scenario("second", visit, Step(Action.ASSERT_TEXT, "#visited", "no"))

    results = [_run(executor, first), _run(executor, second)]

    assert [r.outcome for r in results] == [Outcome.PASSED, Outcome.PASSED]


def test_evidence_tampering_is_detected(
    executor: PlaywrightScenarioExecutor, store: FilesystemEvidenceStore, site: str
) -> None:
    scenario = _scenario("tamper", Step(Action.NAVIGATE, site + "/"))
    result = _run(executor, scenario)
    screenshot = next(e for e in result.evidence if e.kind == "screenshot")

    (store.root / screenshot.location).write_bytes(b"forged")

    assert any("does not match its digest" in p for p in store.problems(result))
