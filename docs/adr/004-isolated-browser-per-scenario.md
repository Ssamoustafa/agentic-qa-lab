# ADR 004: One fresh browser per scenario

## Status

Accepted.

## Context

Cookies, local storage, cache, and service workers can make one scenario's result depend on another. That makes failures irreproducible and lets state from one scenario influence another's verdict.

## Decision

`PlaywrightScenarioExecutor` launches a new browser and context for every scenario and closes both in `finally` blocks, with service workers blocked and downloads disabled.

## Consequences

- Scenarios are independent, and a test proves local storage does not leak between them.
- Cleanup is guaranteed even when a step fails or tracing stops with an error.
- Each scenario pays browser launch cost, roughly a second.

## Trade-off

Speed is deliberately traded for isolation. PR #4 introduces bounded workers; each worker will still own its browser state rather than share a context.
