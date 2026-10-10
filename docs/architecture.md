# Architecture

## Architectural thesis

AI is outside the trusted execution boundary. Provider output is untrusted data until it becomes a typed value and passes deterministic domain policy.

```text
Requirement
        |
        v
RiskAnalyzer port --> RiskAssessment
        |
        v
Typed TestPlan (untrusted producer arrives in PR #3)
        |
==== TRUST BOUNDARY ====
        |
        v
ExecuteTestPlan --> ScenarioPolicy
        |
        +---- BLOCK --> Outcome.BLOCKED (executor never called)
        |
        +---- ALLOW --> ScenarioExecutor port
                              |
                              v
                 PlaywrightScenarioExecutor (fresh browser per scenario)
                              |
                 deterministic oracles + screenshot, trace, console
                              |
                              v
                 EvidenceVerifier (SHA-256, path-confined store)
                              |
                              v
                 RunResult --> run-result.json
```

## Dependency rule

Dependencies point inward:

```text
interfaces/composition -> infrastructure -> application -> domain
```

`domain/` has no dependency on browser, provider, filesystem, HTTP, database, or CI SDKs. Tests parse every module in `domain/` and `application/` and fail if they import an outer layer or a named vendor SDK.

## Implemented layers

### Domain

The domain owns immutable requirements, risks, test steps, scenarios, plans, execution budgets, policy decisions, evidence references, and oracle verdicts. It also owns deterministic keyword risk classification and `ScenarioPolicy`.

The policy fails closed for the following conditions:

- scenario risk exceeds `maximum_risk_level`;
- action is outside the allowlist;
- navigation is not an absolute HTTP(S) URL, contains credentials, or targets a host outside the allowlist;
- scenario steps exceed the action budget.

`ExecutionConstraints` (allowed hosts plus budget) is derived from the policy and passed to the executor, so the same limits are enforced again at runtime rather than only before execution.

`ScenarioResult` enforces what a trustworthy result must look like: a pass needs a deterministic verdict and evidence, a failed deterministic verdict cannot be overridden, and every non-pass carries a reason.

### Application

- `RiskAnalyzer`, `ScenarioExecutor`, and `EvidenceVerifier` protocols.
- `AssessRequirementRisk` returns an immutable `RiskAssessment`.
- `ExecuteTestPlan` evaluates policy per scenario, calls the executor only for allowed scenarios, converts executor exceptions and mismatched results into `Outcome.ERROR`, and downgrades a result whose evidence fails verification.

### Infrastructure

- `PlaywrightScenarioExecutor`: a new browser and context per scenario. Isolation is preferred over speed; pooling is a PR #4 concern.
- `FilesystemEvidenceStore`: confines every path to its root, validates identifiers, and binds each reference to a SHA-256 digest.
- `JsonRunResultWriter`: writes a versioned `run-result.json`.

### Runtime egress control

Chromium is launched with `--host-resolver-rules` so every host outside the allowlist fails to resolve, including redirect hops. A context-level route additionally aborts non-allowlisted requests and records them. Any recorded block fails the scenario, because a page reaching for an unapproved host is a finding, not noise. Every WebSocket is routed but never connected, so no socket can leave the browser, and it is recorded as blocked.

Sync Playwright calls inside a route handler deadlock the dispatcher, so handlers only record and the executor reads the record between steps.

The duration budget bounds step timeouts and the final screenshot. A scenario that times out mid-navigation keeps its trace and console evidence but may have no screenshot.

## Oracle model

`OracleVerdict` distinguishes deterministic and semantic results:

- deterministic verdicts have confidence `1.0`;
- semantic verdicts must include confidence and evidence provenance;
- `ScenarioResult` rejects a pass that contradicts a failed deterministic verdict.

Deterministic oracles (HTTP status, visibility, text containment) live in `domain/oracle.py` as pure functions over observations, so they are testable without a browser. No semantic oracle exists yet; one belongs behind an application port introduced only when it has a concrete consumer.

## Planned extension points

| PR | Capability | Boundary |
|---|---|---|
| #3 | Guarded provider-neutral planning | Infrastructure implementation of a planning port; parser and policy validation before execution |
| #4 | Bounded workers and telemetry | Application coordination with infrastructure trace sink |
| #5 | Seeded-defect benchmark and quality gate | Stable machine-readable result contract |

This sequence avoids prematurely treating an AI provider or a browser library as a domain concept.
