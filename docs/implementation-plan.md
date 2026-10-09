# Three Phases / Five PRs

The repository advances through five focused architectural pull requests. A capability appears only in its assigned PR so its trust boundary, policy, tests, and documentation can be reviewed together.

## Phase 1: Trusted Engine

### PR #1: `feat: establish trusted agentic QA architecture`

Establish immutable domain contracts, deterministic risk classification, risk assessment port/use case, host and action policy, action budgets, oracle/evidence concepts, executable architecture boundary, ADRs, and CI quality gates.

This PR does not execute a browser, call a model, write evidence, coordinate workers, or calculate agent reliability. It establishes the constraints those later capabilities must satisfy.

### PR #2: `feat: implement evidence-driven execution`

Add a Playwright executor behind an application port, isolated browser contexts, navigation/click/fill/assertion support, deterministic verdicts, screenshots, traces, manifests, duration enforcement, and cleanup guarantees.

## Phase 2: Agentic Intelligence

### PR #3: `feat: introduce guarded multi-agent test planning`

Add provider-neutral `PlanningAgent` contracts, structured parsing and validation, risk-weighted planning, malformed-output rejection, prompt-injection policy tests, provider telemetry contracts, and a deterministic planner for CI.

### PR #4: `feat: add autonomous coordination and observability`

Add bounded parallel scenario workers, isolated worker state, run/scenario/worker identifiers, structured trace events, latency metrics, failure classification, time/resource enforcement, replay metadata, and an OpenTelemetry-compatible abstraction.

## Phase 3: Quality Intelligence

### PR #5: `feat: benchmark autonomous QA reliability`

Add a deterministic seeded-defect fixture, independently calculated recall, precision, false-positive rate, scenario validity, acceptance-criteria coverage, execution success, evidence completeness, reproducibility, latency, and optional provider cost metrics. Produce a machine-readable `AgentScorecard` with configurable CI thresholds for TestOps Lab ingestion.
