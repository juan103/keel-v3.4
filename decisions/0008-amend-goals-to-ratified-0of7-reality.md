# ADR-0008: Amend GOALS.md to the ratified 0-executably-closed reality

**Status:** accepted
**Date:** 2026-07-03

## Context

An external (Fable-5) review found that `goals/GOALS.md` — the project's claim contract — still
asserted the *pre-build* goal: "v3.4 closes the refusal-critical gaps … every refusal-critical
hazard has a wired, biting, execution-time falsifier (d≥1) … live-exercised at closure" (Claim),
"every refusal-critical hazard row carries `status=green`" (Success criteria), and "gate
ratification is blocked until all refusal-critical rows are `green` or `accepted-risk`"
(Commitment 4). **None of that is what happened.** The build ratified a scope pivot (ADR-0003 "B
now, C next, A never"; ADR-0005 A/B/C `conditional`; ADR-0007 the F7 downgrade), landing at an
honest **0 refusal-critical hazards executably closed** with `conditional`/`pending` dispositions —
but `GOALS.md` itself was never amended. So the front-door claim contract contradicted the
honesty-ledger and the matrix. That is precisely the drift the kit's §0 ritual exists to surface,
and it was mechanically uncaught (`check_falsifier_consistency` only scans the `## Falsifier`
section against `rejected_prose` tokens, not the Claim/Success/Commitments prose). The commitment
lock, ironically, was *freezing* the now-inaccurate Commitments section.

## Options considered

1. Amend the Claim / Success criteria / Commitment 4 to state the ratified reality, and authorize
   the resulting `goals_sections.Commitments` lock divergence via a `keel-lock-override` block here.
2. Leave `GOALS.md` as-is (dishonest — the claim contract keeps contradicting the outcome).
3. Supersede the whole `GOALS.md` with a new file (heavier; loses the section-level lineage).

## Decision

**Option 1.** Amend `GOALS.md` §Claim, §Success criteria, and Commitment 4 in place, each marked
"AMENDED by ADR-0008", to state the ratified outcome: v3.4 *models* every refusal-critical gap and
wires an in-boundary mitigating check for each, but reaches the execution-time d≥1 barrier for none;
the honest floor is 0 executably closed; `conditional`/`pending` are ratified non-green
dispositions; ratification requires the honesty invariant (wired mechanism + falsifiable exit +
headline held), not "all green". The underlying scope pivot (ADR-0003/0005/0007) is unchanged — this
ADR only makes the claim contract match it. The `Commitments` section is on the commitment-lock
locked surface; the divergence is non-refusal-critical (`goals_sections.*`, not
`refusal_critical_rows.*`), so it is authorized by the lock-override block below rather than by a
re-snapshot, preserving the original Phase-3 baseline as the audit anchor.

```keel-lock-override
lock_override = true
authorized_keys = ["goals_sections.Commitments"]
```

## Consequences

- The claim contract now matches `goals/honesty-ledger.md` and `goals/hazard-coverage.md`; the
  §0 drift the review found is closed.
- The lock-override is scoped to exactly one key (`goals_sections.Commitments`); every other locked
  element (the Falsifier section, all refusal-critical matrix rows, the checks, `preflight.py`, the
  registries) remains under the original baseline, and any refusal-critical-row divergence stays
  GP-5-blocked (no override can exempt it).
- This does not green any row, change any disposition, or alter the 0-executably-closed headline.
- Follow-up (v3.5, not this ADR): `check_falsifier_consistency` (or a new check) should scan the
  Claim/Success/Commitments prose for outcome-contradiction, so this class of drift is caught
  mechanically rather than by external review.
