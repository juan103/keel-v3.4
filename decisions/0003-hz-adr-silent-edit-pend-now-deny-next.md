# ADR-0003: hz-adr-silent-edit -- pend now (conformance-honest), deny-and-prove next

**Status:** accepted
**Date:** 2026-06-28

## Context

Phase-1c spec Commitment 6 / decision C1 promised to green hz-adr-silent-edit at
conformance-level d=1 on the PreToolUse prevention hook (scripts/hooks/protect_adrs.py),
proven via a 4b prevention_proving_test asserting the accepted-ADR file is byte-unchanged
after an attempted edit. On wiring the proving test, we found the hook emits
permissionDecision "ask" (it defers to a human); it does NOT autonomously deny/stop the
write. So a 4b "block proof" would rest on a test-constructed block-gate the production
hook does not implement. The question (green now, or pend) was put to a trio v0.3
adversarial panel (run loop_v0_2_20260627... see docs/superpowers/specs/
keel-v3.4-hz-adr-silent-edit-trio/), terminal disposition unanimous-no-blocking.

## Options considered

1. Option A -- green at conformance level on a test-modeled block-gate, with bounding labels.
2. Option B -- keep the row pending; extract should_block now; ship F-0; charter the honest close next.
3. Option C -- change the hook ask->deny + add an agent-unreachable override, then green.

## Decision

Adopt the panel verdict: **B now, C next, A never.** Reject A as pretending: its proving
test's byte-unchanged pass-condition holds because the test's own `if` refused, not the
shipped hook (proof-production divergence); and I1's prevention-bite is satisfied
circularly by a test-owned gate (neutering should_block also neuters the test's own
branch). Keep hz-adr-silent-edit `pending`. Extract should_block(tool_input, project_dir)
-> bool now (behavior-preserving: main() still emits "ask"); this makes the contract
expressible and is the prerequisite for any honest green. Add the engine's C-5
production-gate rule (Plan 1c-B-i) that makes A mechanically inadmissible. Record the
verbatim F-3 exit condition in the honesty ledger. Charter Phase 1c-C for the honest
close (ask->deny + agent-unreachable override, proven by F-1 with seven controls and F-2).

## Consequences

- Gate-1 headline is honest: 0 of 7 refusal-critical hazards executably closed; 2
  non-critical rows greened. The d>=1 floor is reported as honestly unmet for this hazard.
- The engine permanently rejects a test-local prevention gate for an execution_time green
  on this row (C-5); a future green must drive production code through its real entrypoint.
- Phase 1c-C is now load-bearing: hz-adr-silent-edit greens only when F-1 (production
  deny-gate, byte-unchanged, C-5 (a)-(c), F-1.7 decision-driven-apply) and F-2 (override
  authority model enumerating and closing each agent-reachable channel) both pass.
- This refines the spec's Commitment 6 prose; it does not relitigate the d>=1 floor or
  the detect-don't-pretend discipline, which it upholds.
