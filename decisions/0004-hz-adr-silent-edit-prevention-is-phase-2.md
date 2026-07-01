# ADR-0004: hz-adr-silent-edit execution_time prevention is Phase-2+ (the Bash channel cannot be closed client-side)

**Status:** accepted
**Date:** 2026-06-28

## Context

ADR-0003 kept hz-adr-silent-edit `pending` ("B now, C next, A never") and chartered a
Phase 1c-C that would green it via a hook `ask->deny` change plus an agent-unreachable
override, proven by F-1 (production deny-gate, byte-unchanged) and F-2 (the override and
every agent-reachable mutation channel shown non-authorizing). On designing 1c-C we hit
the binding constraint F-2 names but defers: the PreToolUse hook matches `Edit|Write`
only, so an agent can silently edit an accepted ADR through a `Bash` tool call
(`echo > decisions/0001-x.md`, `sed -i`, `python -c "open(...).write(...)"`), which the
hook never sees. No client-side prevention barrier closes that channel against an
adversary: a Bash-matcher hook cannot parse arbitrary commands (Turing-complete); a git
pre-commit hook is skipped with `git commit --no-verify`; read-only file permissions are
undone with `os.chmod` via `python -c`. Only server-side (a `pre-receive` hook the agent
does not control) or OS-level immutability closes all channels.

## Options considered

1. Record the finding, keep hz-adr-silent-edit pending, sharpen the exit condition, move to Phase 2.
2. Run a trio panel to adversarially stress-test the "no client-side closure" claim first.
3. Do the `ask->deny` refactor anyway as defense-in-depth (does not green; worsens legit-edit UX).

## Decision

Adopt option 1. The execution_time *prevention* green for hz-adr-silent-edit is genuinely
Phase-2+ (server-side / OS enforcement). This is the faithful outcome of ADR-0003's F-2
kill condition ("if the authority model cannot enumerate-and-close the agent-reachable
channels, the row stays pending; do not green a deny-gate whose bypass is unproven"), not
a reversal of it. Keep the shipped hook as `ask` (a real partial mitigation: it converts
a silent Edit/Write edit into a human-gated one); do NOT change it to `deny` (that closes
only the autonomous Edit/Write path while leaving Bash open, and removes the human's
inline approval of legitimate Errata/supersede edits). This refines ADR-0003's "C next"
timing: C (the prevention green) is Phase-2+, not the immediate next phase.

## Consequences

- The Gate-1 headline stays honest at **0 of 7 refusal-critical executably closed**; we do
  not green hz-adr-silent-edit on a prevention barrier whose Bash bypass is unproven.
- This hazard remains covered at its honest layer by the `audit_time` detector
  `check_adr_immutability` (git-history-diff), which catches every silent edit including
  Bash ones -- at the gate, after the fact, not as prevention.
- The honesty-ledger exit condition for hz-adr-silent-edit is sharpened: it greens when
  server-side (pre-receive) or OS-level enforcement closes the Bash, `git --no-verify`,
  and `chmod` channels -- resolver phase **Phase 2+** (was 1c-C).
- The C-5 production-gate engine mechanism (`green_rows._assert_production_gate`, added
  unwired in 1c-B) stays in place for whenever an honest prevention green becomes
  achievable; wiring it (with the M6 tightening) is deferred with the green.
- Next is **Phase 2 (Tier-2)**: `runtime_role` + `attest.py`, kit versioning, CI matrix.
