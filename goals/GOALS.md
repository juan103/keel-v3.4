# GOALS

## Lineage

- v3.3 self-audit (2026-06-17): `goals/audit-v3.3.md` — named the refusal-critical gaps this build closes.
- KEEL v3.4 design spec: `docs/superpowers/specs/2026-06-21-keel-v3.4-design.md` — the per-phase roadmap this project follows.

## Claim

KEEL v3.4 closes the refusal-critical gaps the v3.3 self-audit named: every refusal-critical hazard has at least one wired, biting, execution-time falsifier on its silent-escape path (d≥1), and each is live-exercised against an AI adversary at closure.

## Success criteria

At the Commitment-12 pilot gate: `check_hazard_coverage` returns no violations; every refusal-critical hazard row carries `status=green`; the live-exercise gate has been run against an AI adversary; and the mandatory Atlas re-run adds a fresh confidence interval over the updated hazard list. A meaningful negative result is any refusal-critical hazard that cannot be given a full/execution-time falsifier with d≥1 — that triggers a scope pivot, not a silent demotion.

## Falsifier

`check_hazard_coverage` fails if any refusal-critical hazard maps to a missing/non-importable/non-biting check, is absent/downgraded vs the pinned audit, rests only on a post_hoc/partial falsifier, or sits in an impermissible red state; at closure the live-exercise gate and the mandatory Atlas re-run add their kills. The executable location is `tests/kit/test_hazard_coverage.py`.

## Commitments

1. Every refusal-critical hazard in the v3.3 audit must have a row in `goals/hazard-coverage.md` with a wired falsifier check (ADR-0002).
2. The hazard-coverage matrix is hash-pinned against `goals/audit-v3.3.md`; any silent edit to hazard criticality fails `check_hazard_coverage`.
3. The `d≥1` floor (target_defense_distance ≥ 1) is binding for all refusal-critical hazards — zero-distance rows are impermissible outside `accepted-risk`.
4. Gate ratification is blocked until all refusal-critical rows are `green` or `accepted-risk`; `accepted-risk` rows require a named assumption in `goals/load-bearing-assumptions.md`.

## Non-commitments

- We do not commit to eliminating monoculture risk (AI-judged adversary exercises) in Phase 0; this is an `accepted-risk` assumption with deadline at the Commitment-12 pilot gate.
- We do not commit to covering non-refusal-critical hazards in the Phase-0 falsifier pass; they are tracked but not blocking.
- We do not commit to a specific adversary AI vendor for the live-exercise gate — that decision deferred to Phase 3.

## Phases

### Phase 0: Pre-registration and falsifier spine
- **Builds:** GOALS/PARADIGM/binding ADR; hazard-coverage matrix parser; `check_hazard_coverage` wired into preflight; commitment-lock snapshot.
- **Verifies:** preflight exits 0 with all baseline checks green; `check_hazard_coverage` returns no violations on the Phase-0 baseline; audit pin holds.
- **Kill condition:** `check_hazard_coverage` cannot be made to bite on a synthetic missing-hazard input — the check is vacuous.

### Phase 1: Wiring and falsifier bite (one hazard per Tier)
- **Builds:** wired checks for at least one Tier-1 and one Tier-2 refusal-critical hazard; proving-test pair (negative + positive) per wired check.
- **Verifies:** each wired check flips its row from `pending` to `green`; the proving-test negative run is on record in `.first-outcome-log.json`.
- **Kill condition:** no wired check can be written for a Tier-1 hazard without requiring human judgment — the falsifier is not mechanical.

### Phase 2: Full coverage
- **Builds:** wired checks for all remaining refusal-critical hazards not in `accepted-risk`.
- **Verifies:** `check_hazard_coverage` returns no violations on the full matrix; all refusal-critical rows are `green` or `accepted-risk`.
- **Kill condition:** more than three refusal-critical hazards end in `accepted-risk` without a verified closure plan.

### Phase 3: Live-exercise gate + Atlas re-run
- **Builds:** live-exercise harness against an AI adversary; Atlas re-run with the updated hazard list.
- **Verifies:** every `exercise_scenario` field has a passing execution-time result; Atlas confidence interval covers the claim.
- **Kill condition:** live-exercise fails on a Tier-1 hazard that was marked `green` — this is a false green; the row must be re-opened and the check strengthened.

## Risks

1. The hazard list itself may be incomplete — we are relying on the v3.3 self-audit's coverage, which is AI-generated and has not been externally validated. Managed as an `accepted-risk` assumption (§8 in load-bearing-assumptions.md).
2. Mechanical falsifiers may not catch substantive judgment failures (e.g., a check that passes on a subtly-wrong frame). Managed by the d≥1 floor and the live-exercise gate.
3. The `accepted-risk` escape valve may be overused to silence hard hazards. Managed by the three-row cap in Phase 2's kill condition and by naming each `accepted-risk` assumption explicitly.

## Named assumption (accepted-risk)

§8 (load-bearing-assumptions.md): the hazard list is derived solely from the v3.3 self-audit (AI-generated, no external human expert review, no cross-audit comparison). AI monoculture in both the hazard enumeration and the adversary exercise means both the test and the oracle may share the same blind spots. Accepted as risk; resolution required before the Commitment-12 pilot gate.
