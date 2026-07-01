# ADR-0007: Phase-4 F7 downgrade ratified — closure at the honest 0/7 floor

**Status:** accepted
**Date:** 2026-07-01

## Context

The Phase-4 live adversarial-exercise gate (F7) was meant to be the closure evidence for the 4
refusal-critical `conditional` rows (a check-blind opus adversary could not silently escape past the
named check). It was run live (N=10 opus, ax-runtime-role + ax-frame-validity: named checks caught
every modeled escape taken, 0 uncaught). But a Phase-0 adversarial probe **verified** that F7
cannot be run check-blind with the in-session Agent-subagent mechanism — every subagent roots at the
full repo and can read its own answer key (2/10 ax-frame-validity agents demonstrably did). A trio
v0.3 panel ruled that "name the leak and continue" cannot claim "conservative under leakage." Both
mandatory closure audits then PASS on the downgraded state: the Atlas as-built re-run returns
REFUSE–disclaimer driven solely by the 2 accepted-risk residuals (no new unguarded refusal-critical
finding), and the Phase-4 trio closure panel's ground-truth matches the artifacts (headline 0/7
held, F7 credited only as instrument-validation, all residues named). See
`docs/superpowers/keel-v3.4-phase4-F7-finding.md`.

## Options considered

1. Ratify the honest downgrade — F7 = instrument-validation, not closure; headline 0/7; blind
   harness → v3.5.
2. Build real isolation now (separate clean checkout/container per trial, or remove the check
   sources during each trial) and run a valid blind F7 in v3.4.
3. Pause — do not ratify until a valid blind F7 exists.

## Decision

**Option 1.** The owner ratifies the honest downgrade. F7 is recorded as **instrument-validation**
(the named checks catch the modeled escapes when taken), **NOT** as closure of any refusal-critical
row. The headline stays **0 of 7 refusal-critical hazards executably closed**; the 4 conditional
rows remain `conditional`. This ratifies an honest "not closed," not a pass — nothing is marked
closed. "Infeasible" is scoped to the in-session tooling, not absolute (option 2 remains available;
it is deferred to v3.5, not foreclosed).

## Consequences

- **v3.4 closes at the honest 0/7 floor.** The conditional rows' gate-integrity/F7 residue stays
  OPEN; the instrument-validation credit is bounded (conditional on detector soundness — BUG-001 is
  the exception channel — and internal-consistency, not external-validity correspondence).
- **Deferred to v3.5, carried as documented open items (NOT applied now):** the properly-isolated
  blind F7 harness (trio panel v4 spec); the BUG-001 hardening of `check_frame_validity_audit` (its
  `xfail` falsifier remains as the executable record of the open gap); the harness-contract
  `oracle_leakage_scope` correction. Applying any of these is a locked-surface + vocabulary-fork
  change requiring its own ADR + `commitment_lock` re-snapshot when v3.5 does the work.
- **Owner attestation is NOT required for this ratification** — it would complete
  `hz-runtime-role-unannotated` precondition #6 but cannot green the row (gate-integrity/F7 is the
  downgraded residue; greening needs the v3.5 interlock). The `preflight --strict` WARN on the
  unattested author-fill is the expected honest state of a conditional row.
- Both auditors (structure = Atlas, prose = trio) converge on this floor; this is convergent
  internal coherence, NOT external validation (§8 names that gap; the pilot gate schedules it).
