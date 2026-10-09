# ADR 001: AI remains outside the trusted execution boundary

## Status

Accepted.

## Context

An autonomous QA system benefits from model-assisted planning but a model response is not an authorization decision. Provider output can be malformed, manipulated by prompt injection, inconsistent, or simply wrong. Giving it direct access to browser, shell, filesystem, database, network, or secret capabilities would make prompt content part of the security perimeter.

## Decision

Treat every agent/provider response as untrusted data. It must be parsed into typed domain values and then pass deterministic validation and `ScenarioPolicy` before an executor can act.

Executable behavior is represented by a finite action enum. A new capability requires all of the following:

1. an explicit domain representation;
2. policy consideration and tests;
3. a trusted executor implementation;
4. evidence and observability expectations.

## Consequences

- A provider cannot add shell, filesystem, SQL, secret, or arbitrary network authority through a prompt.
- Policy violations are inspectable `PolicyDecision` values rather than hidden prompt failures.
- Provider integrations remain infrastructure adapters and can be replaced by deterministic fakes in tests.
- More parsing and validation work is required before feature development, deliberately trading speed for auditable control.

## Rejected alternative

Prompt-only restrictions were rejected because a prompt is guidance to an untrusted component, not a deterministic enforcement mechanism.
