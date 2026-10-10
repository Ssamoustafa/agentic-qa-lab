# Threat Model

## Security position

Prompt text is not a security control. Typed contracts and deterministic policy decide whether a proposed scenario may run, and the executor enforces the same limits again at runtime because a policy check alone cannot see redirects or subresources.

| Threat | Deterministic control | Status / follow-up |
|---|---|---|
| Prompt injection proposes unsafe work | agent text has no authority; only typed actions reach policy | PR #3 validates provider output before it becomes a `TestPlan` |
| Arbitrary browser navigation | policy requires absolute HTTP(S), credential-free, allowlisted URLs; Chromium host resolution is restricted to the allowlist; a context route aborts and records anything else, including redirect hops and third-party subresources; any recorded block fails the scenario | enforced in PR #2 |
| Arbitrary shell, SQL, filesystem, secrets, or HTTP | no such executable action exists in the domain vocabulary | new capability requires domain, policy, executor, and tests |
| Action-loop resource exhaustion | action budget before execution; elapsed-time budget enforced in step timeouts and failure-evidence capture | enforced in PR #2; PR #4 adds bounded workers |
| Scenario above accepted risk | `maximum_risk_level` blocks it with an auditable violation | PR #3 adds approval routing |
| Fabricated or overridden verdict | `ScenarioResult` requires a deterministic verdict and evidence for a pass and rejects a pass beside a failed deterministic verdict | enforced in PR #2 |
| Missing or forged evidence | every reference carries a SHA-256 digest; `ExecuteTestPlan` verifies each result and downgrades a pass to `error` when evidence is missing, outside the root, or altered | enforced in PR #2 |
| Path traversal through identifiers | run and scenario ids must match a strict pattern; the store resolves every path and rejects anything outside its root | enforced in PR #2 |
| Executor failure hiding as a pass | executor exceptions and results for another scenario become `Outcome.ERROR` | enforced in PR #2 |
| State leaking between scenarios | a new browser and context per scenario, service workers blocked, downloads disabled | enforced in PR #2; PR #4 adds concurrent workers |
| Untraceable decisions | `PolicyDecision` preserves all violations; run results record outcome per scenario | PR #4 adds run, scenario, and worker correlation events |

## Security invariants

1. `PolicyDecision` cannot claim both allow and a violation, and a block must record at least one violation.
2. `TestPlan` requires a nonblank requirement identifier, risk context, scenarios, and unique scenario identifiers.
3. A passed `ScenarioResult` needs a deterministic verdict and evidence, and a failed deterministic verdict can never be overridden.
4. A blocked scenario never reaches an executor.
5. `domain/` and `application/` cannot import outer layers or named provider/browser SDKs.

## Residual risk

- **WebSockets are blocked outright.** Sync Playwright cannot safely connect an allowed socket from inside a route handler, so none are permitted. A scenario that needs one fails visibly rather than silently succeeding.
- **Any blocked egress fails the scenario.** A site that legitimately loads a third-party asset needs that host added to the allowlist.
- **Duration is enforced between and within steps, not by a hard kill.** A scenario may overrun by the screenshot grace period (0.5s) plus browser teardown.
- **A timeout mid-navigation may leave no screenshot.** Trace and console evidence are still captured and verified.
- **Digests prove integrity after capture, not authenticity.** Someone able to rewrite both the artifact and the manifest is outside this PR's threat model; signing is a candidate follow-up.
- **No model provider, autonomous loop, or concurrency exists yet.** Their controls arrive in PRs #3 and #4.
