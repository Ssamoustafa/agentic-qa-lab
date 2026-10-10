# ADR 003: Enforce egress at runtime, not only in policy

## Status

Accepted.

## Context

`ScenarioPolicy` validates the hosts a scenario names, but a page can redirect, load subresources, or open sockets to hosts nobody named. A policy-only check would approve a scenario that then reaches an attacker-controlled host.

## Decision

The executor receives `ExecutionConstraints` derived from the policy and enforces them independently:

1. Chromium is started with `--host-resolver-rules` so non-allowlisted hosts fail to resolve, including redirect hops.
2. A context route aborts any non-allowlisted request and records it.
3. Every WebSocket is intercepted and never connected.
4. Any recorded block fails the scenario with an `egress blocked` reason.

## Consequences

- Redirects and third-party subresources cannot silently reach unapproved hosts.
- A blocked request is reported as a finding rather than ignored.
- Sites that depend on third-party assets or WebSockets fail until explicitly allowlisted or supported.

## Rejected alternatives

- **Policy check only:** cannot observe redirects or subresources.
- **Route interception only:** relies on one layer; resolver rules give an independent second control.
- **Connecting allowed WebSockets:** sync Playwright deadlocks when calling into the dispatcher from a route handler, and the allowed path could not be exercised by a test. Blocking all sockets is the fail-closed choice until an async executor exists.
