# Agentic QA Lab

**A platform for constraining, observing, executing, and evaluating autonomous QA agents, not an AI Playwright demo.**

Agentic QA Lab addresses a practical engineering question:

> How can an organization constrain, observe, measure, and trust an autonomous QA agent enough to use it in CI/CD?

The project is intentionally built through five small architectural pull requests. PR #1 established the trusted engine; PR #2 adds deterministic, evidence-producing execution behind it.

## Implemented in PR #2

- `ExecuteTestPlan` use case: the only path from a typed `TestPlan` to an executor. Policy runs first; a blocked scenario never reaches the executor.
- `ScenarioExecutor` and `EvidenceVerifier` application ports; the domain does not know Playwright exists.
- Playwright adapter with a fresh browser and context per scenario, service workers blocked, and no shared state.
- Runtime egress enforcement: Chromium host resolution is restricted to the allowlist, requests are routed through a guard, redirect hops and third-party subresources are blocked and fail the scenario. Every WebSocket is blocked.
- Elapsed-time budget enforced at runtime, including failure-evidence capture.
- Deterministic oracles for HTTP status, visibility, and text containment, with a step index on each verdict.
- Screenshot, Playwright trace, and console/page-error evidence, each tied to a SHA-256 digest by a path-confined evidence store. Tampered or missing evidence downgrades a pass to an error.
- `ScenarioResult` invariants: a pass requires a deterministic verdict and evidence, and a failed deterministic verdict can never be overridden.
- Versioned, machine-readable `run-result.json`.

## Implemented in PR #1

- Immutable domain contracts for requirements, risk, scenarios, plans, budgets, evidence, oracle verdicts, and policy decisions.
- Deterministic keyword risk classification behind a typed `RiskAnalyzer` application port.
- A risk-assessment use case with no provider, browser, filesystem, or network dependency.
- A fail-closed scenario policy with risk threshold, action allowlist, HTTP(S) navigation validation, host allowlist, and action budget checks.
- Executable architecture checks that keep `domain/` independent of outer layers and vendor SDKs.
- Ruff, strict mypy, pytest, and an 85% coverage gate in CI.

## Trust boundary

AI is outside the trusted execution boundary. A future planning provider may propose a `TestPlan`; it never receives the authority to execute it.

```text
Untrusted plan producer (PR #3)
              |
              v
        Typed TestPlan
              |
============== TRUST BOUNDARY ==============
              |
              v
Domain invariants + ScenarioPolicy (PR #1)
              |
       +------+------+
       |             |
     BLOCK          ALLOW
       |             |
       v             v
Auditable decision   Deterministic executor (PR #2)
```

The executable action vocabulary is deliberately small: `navigate`, `click`, `fill`, `assert_visible`, and `assert_text`. New capabilities require an explicit domain action, policy rule, executor implementation, and test.

## Current security guarantees

- Only typed actions are representable; shell, SQL, filesystem, secret, and arbitrary HTTP operations are not actions.
- Navigation must be an absolute HTTP(S) URL without embedded credentials and must match the configured host allowlist.
- Policy rejects actions outside its allowlist, scenarios above its risk threshold, and plans exceeding the action budget.
- Deterministic and semantic verdicts are distinct. A semantic verdict must carry confidence and provenance; it cannot be represented as a replacement for a deterministic verdict.

Provider planning, worker coordination and telemetry, and benchmark scoring are deliberately deferred to their respective PRs. See [docs/implementation-plan.md](docs/implementation-plan.md).

## Architecture

```text
src/agentic_qa/
├── domain/          # immutable contracts, risk rules, policy, deterministic oracles
├── application/     # use cases and ports
└── infrastructure/  # Playwright executor, evidence store, run-result writer
```

Dependencies point inward: `infrastructure -> application -> domain`, with interfaces acting only as a future composition root. The domain imports neither provider SDKs nor browser, filesystem, HTTP, database, or CI implementations.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,browser]"
python -m playwright install chromium
ruff check .
ruff format --check .
mypy src
pytest
```

`pytest` includes the repository coverage threshold. Browser tests are marked `browser` and are skipped when Playwright is not installed; the coverage gate then fails for the executor, so CI installs both.

## Five-PR roadmap

| Phase | PR | Outcome |
|---|---|---|
| Trusted Engine | #1 `feat: establish trusted agentic QA architecture` | contracts, risks, deterministic policy, CI |
| Trusted Engine | #2 `feat: implement evidence-driven execution` | isolated browser execution, deterministic oracles, evidence |
| Agentic Intelligence | #3 `feat: introduce guarded multi-agent planning` | typed provider-neutral planning and validation |
| Agentic Intelligence | #4 `feat: add autonomous coordination and observability` | bounded workers, tracing, replay metadata |
| Quality Intelligence | #5 `feat: benchmark autonomous QA reliability` | seeded defects, scorecard, CI quality gate |

## Portfolio relationship

- **Atlas Test Framework**: reusable UI/API automation framework architecture.
- **TestOps Lab**: result ingestion, history, quality policy, and release gates.
- **Agentic QA Lab**: trusted autonomous QA, safety controls, observability, and evaluation.

Future integration with TestOps Lab occurs through a stable, machine-readable result contract rather than a repository-level dependency.
