# ADVERSARIAL-BASELINE.md — Phase 1c.0 probe results

Recorded pre-hardening (Phase 1b engine, before any 1c-A task).

| Pattern | Pre-hardening result | Target after 1c-A hardening | Resolving task |
|---|---|---|---|
| ADV-1: post-hoc-relabeled-as-execution_time | **FAIL-OPEN** (no `_assert_prevents`) | Rejected at step 4b | 1c-A.6 |
| ADV-2: vacuous-but-collectible | **ALREADY REJECTED** (`_assert_neuter_probe`) | Stays rejected; sentinel/corollary added | 1c-A.5 |
| ADV-3: distance-overclaim (`silent_path_defense_distance=2`) | **FAIL-OPEN** (no `_assert_distance`) | Rejected at step 5 | 1c-A.8 |
| ADV-4: cache-survives-strict | **DEFERRED** (skip — requires `--strict` cache semantics) | 1c-B anchor | 1c-B |

GP-6 isolation confirmed: all fixtures use the current 17-col schema (`_EXPECTED_COLS`).
ADV-3 fixture sets `silent_path_defense_distance=2` (existing col 13, not a new field).
ADV-1 pattern needs `prevention_proving_test` (new col, added in 1c-A.1) — baseline uses
only `layer="execution_time"` (existing field); the absence of `_assert_prevents` is the
targeted fail-open, not schema skew.

Permanent strict-reject assertions (post-hardening) live in:
  `tests/kit/test_green_rows.py::test_adv_posthoc_relabeled_execution_time_rejected` (1c-A.10)
  `tests/kit/test_green_rows.py::test_adv_distance_overclaim_rejected` (1c-A.10)

## ADV-5 — vacuous-prevention (added 1c-B-i, trio-driven)

Pattern: an `execution_time` row ships a `prevention_proving_test` that passes
regardless of the check (e.g. `assert True` naming the resource). Closed by the
I1 prevention-bite: the neuter-probe runs the prevention test under neuter and
rejects the row if it still passes. Permanent guard:
`test_adv5_vacuous_prevention_permanently_rejected`.
