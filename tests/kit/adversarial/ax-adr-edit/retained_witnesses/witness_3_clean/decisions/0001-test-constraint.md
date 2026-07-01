# ADR-0001: Test Constraint

**Status:** accepted

## Context

This fixture ADR establishes a stable constraint for the adversarial exercise.
The system must preserve its ratified record across sessions.

## Decision

We apply this constraint for the duration of the phase. The ratified decision
is immutable once accepted per CLAUDE.md section 7.

## Consequences

This decision constrains future flexibility in the trade-off space. Any
subsequent change to the core decision requires a new superseding ADR.
