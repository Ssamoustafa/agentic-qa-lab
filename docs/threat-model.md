# Threat Model

## Security position

Prompt text is not a security control. The trusted engine uses typed contracts and deterministic policy to decide whether a proposed scenario is eligible for future execution.

| Threat | PR #1 deterministic control | Follow-up boundary |
|---|---|---|
| Prompt injection proposes unsafe work | agent text has no authority; only typed actions can reach policy | PR #3 validates provider output before it becomes a `TestPlan` |
| Arbitrary browser navigation | `navigate` must be absolute HTTP(S), credential-free, and host allowlisted | PR #2 revalidates actual navigation and redirects in the browser adapter |
| Arbitrary shell, SQL, filesystem, secrets, or HTTP | no such executable action exists in the domain vocabulary | new capability requires domain, policy, executor, and tests |
| Action-loop resource exhaustion | positive action budget is enforced before execution | PR #2 enforces elapsed-time budget; PR #4 adds bounded workers and resource accounting |
| Scenario above accepted risk | `maximum_risk_level` blocks it with an auditable violation | PR #3 adds approval routing when policy allows human review |
| Fabricated deterministic result | no agent can emit an execution result in this phase; deterministic and semantic verdict types are separate | PR #2 owns deterministic assertions and evidence capture |
| Missing or fabricated evidence | evidence references validate kind, location, and optional SHA-256 shape | PR #2 requires real artifact production and manifest verification |
| Parallel state interference | no parallel execution exists in this phase | PR #4 isolates worker and browser state |
| Untraceable decisions | `PolicyDecision` preserves all violations | PR #4 adds run, scenario, and worker correlation events |

## Security invariants

1. `PolicyDecision` cannot claim both allow and a violation, and a block must record at least one violation.
2. `TestPlan` requires a nonblank requirement identifier, risk context, scenarios, and unique scenario identifiers.
3. Semantic oracle verdicts require confidence and provenance. They are not a substitute for deterministic verdicts.
4. Domain code cannot import infrastructure, interfaces, or named provider/browser SDKs.

## Residual risk

This PR intentionally contains no browser, model provider, filesystem writer, network client, or autonomous loop. That limits its attack surface, but it also means browser redirect handling, timeout enforcement, evidence materialization, and observability must be implemented before any autonomous execution is enabled.
