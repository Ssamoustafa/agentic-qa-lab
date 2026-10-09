from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Action(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_TEXT = "assert_text"


class OracleKind(StrEnum):
    DETERMINISTIC = "deterministic"
    SEMANTIC = "semantic"


@dataclass(frozen=True, slots=True)
class Requirement:
    requirement_id: str
    text: str

    def __post_init__(self) -> None:
        if not self.requirement_id.strip():
            raise ValueError("requirement_id must not be blank")
        if not self.text.strip():
            raise ValueError("requirement text must not be blank")


@dataclass(frozen=True, slots=True)
class Risk:
    area: str
    level: RiskLevel
    rationale: str

    def __post_init__(self) -> None:
        if not self.area.strip() or not self.rationale.strip():
            raise ValueError("risk area and rationale must not be blank")


@dataclass(frozen=True, slots=True)
class TestStep:
    action: Action
    target: str
    value: str | None = None

    def __post_init__(self) -> None:
        if not self.target.strip():
            raise ValueError("step target must not be blank")
        action_requires_value = self.action in {Action.FILL, Action.ASSERT_TEXT}
        if action_requires_value and self.value is None:
            raise ValueError(f"{self.action.value} requires a value")
        if not action_requires_value and self.value is not None:
            raise ValueError(f"{self.action.value} does not accept a value")

    @property
    def host(self) -> str | None:
        if self.action is not Action.NAVIGATE:
            return None
        return urlparse(self.target).hostname


@dataclass(frozen=True, slots=True)
class TestScenario:
    scenario_id: str
    title: str
    risk: RiskLevel
    steps: tuple[TestStep, ...]
    acceptance_criteria: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario_id.strip() or not self.title.strip():
            raise ValueError("scenario id and title must not be blank")
        if not self.steps:
            raise ValueError("scenario must contain at least one step")
        if any(not criterion.strip() for criterion in self.acceptance_criteria):
            raise ValueError("acceptance criteria must not contain blank values")


@dataclass(frozen=True, slots=True)
class TestPlan:
    requirement_id: str
    risks: tuple[Risk, ...]
    scenarios: tuple[TestScenario, ...]

    def __post_init__(self) -> None:
        if not self.requirement_id.strip():
            raise ValueError("test plan requirement_id must not be blank")
        if not self.risks:
            raise ValueError("test plan must contain risks")
        if not self.scenarios:
            raise ValueError("test plan must contain scenarios")
        scenario_ids = tuple(scenario.scenario_id for scenario in self.scenarios)
        if len(set(scenario_ids)) != len(scenario_ids):
            raise ValueError("test plan scenario ids must be unique")


@dataclass(frozen=True, slots=True)
class ExecutionBudget:
    max_steps: int = 30
    max_duration_seconds: int = 120

    def __post_init__(self) -> None:
        if self.max_steps <= 0 or self.max_duration_seconds <= 0:
            raise ValueError("execution budgets must be positive")


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    kind: str
    location: str
    sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.kind.strip() or not self.location.strip():
            raise ValueError("evidence kind and location must not be blank")
        if self.sha256 is not None and (
            len(self.sha256) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in self.sha256)
        ):
            raise ValueError("sha256 must be a 64-character hexadecimal digest")


@dataclass(frozen=True, slots=True)
class OracleVerdict:
    oracle: OracleKind
    passed: bool
    expected: str
    actual: str
    confidence: float = 1.0
    provenance: tuple[EvidenceReference, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.oracle is OracleKind.DETERMINISTIC and self.confidence != 1.0:
            raise ValueError("deterministic oracle confidence must be 1.0")
        if self.oracle is OracleKind.SEMANTIC and not self.provenance:
            raise ValueError("semantic oracle verdicts require provenance")


@dataclass(frozen=True, slots=True)
class PolicyViolation:
    rule: str
    reason: str

    def __post_init__(self) -> None:
        if not self.rule.strip() or not self.reason.strip():
            raise ValueError("policy violation rule and reason must not be blank")


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    violations: tuple[PolicyViolation, ...] = ()

    def __post_init__(self) -> None:
        if self.allowed and self.violations:
            raise ValueError("allowed policy decisions cannot include violations")
        if not self.allowed and not self.violations:
            raise ValueError("blocked policy decisions require violations")
