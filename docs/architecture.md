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
Typed TestPlan (future untrusted producer)
        |
==== TRUST BOUNDARY ====
        |
        v
Domain invariants + ScenarioPolicy
        |
        +---- BLOCK --> PolicyDecision with violations
        |
        +---- ALLOW --> Deterministic executor (PR #2)
```

## Dependency rule

Dependencies point inward:

```text
interfaces/composition -> infrastructure -> application -> domain
```

`domain/` has no dependency on browser, provider, filesystem, HTTP, database, or CI SDKs. A test parses every domain module and fails if it imports an outer layer or a named vendor SDK.

## Implemented layers

### Domain

The domain owns immutable requirements, risks, test steps, scenarios, plans, execution budgets, policy decisions, evidence references, and oracle verdicts. It also owns deterministic keyword risk classification and `ScenarioPolicy`.

The policy fails closed for the following conditions:

- scenario risk exceeds `maximum_risk_level`;
- action is outside the allowlist;
- navigation is not an absolute HTTP(S) URL, contains credentials, or targets a host outside the allowlist;
- scenario steps exceed the action budget.

`max_duration_seconds` is part of the immutable execution contract. Enforcing elapsed time requires an executor and is therefore introduced with the deterministic execution adapter in PR #2.

### Application

The application contains the `RiskAnalyzer` protocol and `AssessRequirementRisk` use case. The use case accepts a `Requirement` and returns an immutable `RiskAssessment`; it has no knowledge of agents, browser automation, or persistence.

## Oracle model

The first PR establishes the contract, not an oracle provider. `OracleVerdict` distinguishes deterministic and semantic results:

- deterministic verdicts have confidence `1.0`;
- semantic verdicts must include confidence and evidence provenance;
- the types are separate, so semantic output cannot silently overwrite a deterministic failure.

PR #2 will add deterministic browser assertions and evidence. A semantic-oracle adapter belongs behind an application port introduced only when it has a concrete consumer.

## Planned extension points

| PR | Capability | Boundary |
|---|---|---|
| #2 | Browser execution, evidence manifests, deterministic oracle | Infrastructure implementation of an application executor port |
| #3 | Guarded provider-neutral planning | Infrastructure implementation of a planning port; parser and policy validation before execution |
| #4 | Bounded workers and telemetry | Application coordination with infrastructure trace sink |
| #5 | Seeded-defect benchmark and quality gate | Stable machine-readable result contract |

This sequence avoids prematurely treating an AI provider or a browser library as a domain concept.
