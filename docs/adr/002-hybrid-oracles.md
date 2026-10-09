# ADR 002: Separate deterministic and semantic oracles

## Status

Accepted.

## Context

Some QA assertions are exact: URL, status code, numeric value, visibility, text, and schema compliance. Other judgments, such as clarity of an error message, are probabilistic and may use a model. Treating both as a generic boolean would allow a high-confidence subjective judgment to hide a deterministic failure.

## Decision

Represent deterministic and semantic results with distinct `OracleKind` values in `OracleVerdict`.

- Deterministic verdicts have confidence `1.0`.
- Semantic verdicts must provide a bounded confidence value and evidence provenance.
- Future verdict aggregation must preserve a failed deterministic result; semantic output may add context but cannot silently replace it.

## Consequences

The first PR defines and validates the contract without introducing a provider or browser assertion library. PR #2 implements deterministic browser assertions and evidence capture. A semantic-oracle port will be added only when an application use case consumes it, keeping speculative abstractions out of the trusted core.

## Trade-off

This model produces more than one signal for a scenario rather than a convenient single score. That extra structure is necessary to keep exact and probabilistic claims explainable.
