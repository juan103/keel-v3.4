# Bug Log

Project bugs, documented and addressed systematically. New in KEEL v3.2.

This log is for **bugs in the project's own code** — behavior that
contradicts a requirement, a ratified phase, or an obvious correctness
expectation. It is NOT for:

- **Kit bugs** (the kit's rules/checks/hooks misbehaving) → `kit-friction.md`.
- **Methodological risks** (unverified assumptions the project leans on)
  → `goals/load-bearing-assumptions.md`.

## The protocol

Every bug goes through this cycle, in order, no exceptions:

1. **Document it.** Add an entry below the moment the bug is observed, even
   if you fix it five minutes later. A bug that isn't written down didn't
   happen — and will happen again.
2. **Reproduce it with a failing test.** Write a pytest function named
   `test_BUG_NNN_<short_descriptor>` that fails because of the bug. Watch it
   fail for the right reason. This is the bug-shaped twin of the kit's
   test-first rule (CLAUDE.md §3): no fix is written before its
   reproduction exists. (v3.3: the reproduction's first outcome is recorded
   in `tests/.first-outcome-log.json`; `check_coverage.py --strict-red-green`
   fails a reproduction that was never seen red.)
3. **Diagnose.** Record the root cause in the entry — not just where it
   broke, but why. Set status to `diagnosed`.
4. **Fix.** Smallest change that makes the reproduction test pass. Run all
   earlier tests to check for regressions.
5. **Keep the test.** The reproduction test stays in the suite permanently
   as a regression guard. Removing it requires an ADR.
6. **Close the entry.** Set status to `fixed` with the commit reference.
   If the bug is consciously not going to be fixed, set `wontfix` with the
   reason — that is a decision, so if it constrains future code, it also
   needs an ADR.

If a bug reveals that a ratified requirement was wrong (the test enforced
the wrong behavior), that is a fork (CLAUDE.md §4): stop, ask, ADR.

Preflight (`check_bug_log_exists`) verifies this file exists, that every
entry's `Status:` is one of the four lifecycle states (v3.3: an entry with
no Status line fails too), and warns at session start while any bug is
still `open`.

## Lifecycle states

- `open` — observed and documented, not yet understood.
- `diagnosed` — root cause identified, reproduction test exists and fails.
- `fixed` — reproduction test passes; commit referenced.
- `wontfix` — consciously not fixing; reason recorded (ADR if load-bearing).

## Format

```
### BUG-NNN — short title

- **Status:** open | diagnosed | fixed | wontfix
- **Date observed:** YYYY-MM-DD
- **Observed:** What happened, vs what was expected. Requirement violated (R-N.X) if applicable.
- **Reproduction test:** tests/test_phase_N.py::test_BUG_NNN_<descriptor> (or "not yet written")
- **Root cause:** (fill at diagnosis)
- **Fix:** (commit hash / description, fill at close)
```

Number bugs sequentially from BUG-001. Never reuse a number, never delete
an entry — a `wontfix` or even a mistaken entry is part of the record.

## Entries

### BUG-001 — check_frame_validity_audit accepts a non-adjudicated placeholder verdict

- **Status:** diagnosed (fix flagged for owner ratification — refusal-critical check + locked-surface + vocabulary fork)
- **Date observed:** 2026-06-30
- **Observed:** The production frame-validity check (`preflight.check_frame_validity_audit`) tests
  `author_verdict` for non-emptiness, not for being a valid adjudication. A placeholder
  `author_verdict="PENDING"` with non-empty `dispositions=["PENDING"]` produces zero problems —
  a substantively-unverified frame passes the gate. Surfaced by the Phase-4 live exercise
  (ax-frame-validity); see `docs/superpowers/keel-v3.4-phase4-F7-finding.md` §3b. (The closest live
  output, trial 3, used `dispositions=[]`, which IS caught by Check 3 — so this exact placeholder
  is a constructed demonstration, not a live escape.)
- **Reproduction test:** `tests/test_BUG_001_placeholder_verdict.py::test_BUG_001_placeholder_verdict_is_flagged`
  (xfail(strict) — documents the gap executably; turns xpass when the fix lands) plus a passing
  control confirming the empty-verdict case is already caught.
- **Root cause:** the check validates field presence + non-emptiness, never that the verdict token
  expresses a completed adjudication. A finite predicate against an open-ended verdict space
  (trio panel commitment-4 wound).
- **Fix:** NOT applied silently. Hardening `check_frame_validity_audit` to reject non-adjudicated
  placeholder verdicts is a refusal-critical check change + a `commitment_lock` locked-surface edit
  (preflight_sha / registered check set) + a verdict-vocabulary fork (positive-whitelist vs
  placeholder-blocklist). Teed up; awaits owner-ratified ADR + lock re-snapshot.
