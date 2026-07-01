# ADR-0001: Testing strategy for non-deterministic outputs

**Status:** accepted
**Date:** [fill in when starting project]

## Context

Many requirements in this project may produce non-deterministic outputs: statistical metrics on graphs, simulation results with random initialization, predictions with stochastic models, signals with noise. Strict example-based tests do not work for these — there is no single "expected output" to compare against.

Without an explicit policy, the agent will either skip writing tests for these (because no example fits), or write tests that assert whatever the code currently produces (which passes any implementation, broken or correct).

## Options considered

1. Skip tests for non-deterministic code — accept that some requirements have no executable verification.
2. Use approximate equality with fixed seeds — set the random seed, run once, save output, assert future runs match within tolerance.
3. Use property-based testing (Hypothesis) — assert invariants that must hold for any valid input, generate hundreds of test cases trying to break them.
4. Combine seeded snapshots for regression detection AND property-based tests for invariant checks.

## Decision

**Use option 4: combined approach.**

For every non-deterministic requirement, write at least one of each:

- **A property-based test (Hypothesis)** that asserts the invariant the requirement actually claims. Example: "for any graph with these properties, the partition's blanket nodes are conditionally independent of the rest." This catches edge cases.
- **A seeded snapshot test** that runs with a fixed seed, compares against a saved JSON snapshot, fails if the result drifts beyond tolerance. This catches silent regressions when code changes.

Example-based tests remain the default for deterministic requirements.

## Consequences

- Project depends on `hypothesis` library (added to requirements).
- First time using Hypothesis on a project takes ~1 hour to learn the patterns.
- Snapshot files live in `tests/snapshots/` and are version-controlled.
- When intentionally changing an algorithm, the snapshot must be explicitly regenerated and the change recorded in a new ADR.
- Snapshots prevent silent regressions but can also create false positives when the change is intentional. The remediation step (ADR + regenerate) is the cost of preventing silent drift.
- For requirements that are *purely* exploratory ("see what the metric looks like on the data"), no test is required, but the requirement must be marked `EXPLORATORY` in REQUIREMENTS.md and produce only an artifact (a plot, a results JSON), never code that other phases depend on.
