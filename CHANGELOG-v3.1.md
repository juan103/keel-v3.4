# KEEL Project Kit v3.1 — Release Notes

v3.1 is an additive patch over v3, driven by frictions logged in the trio
project's `kit-friction.md` between 2026-05-03 and 2026-05-10. Every change
below cites the friction entry that motivated it. No v3 contract is removed;
no new vocabulary is introduced.

The four v4-scope items logged in trio (frame-validity binding shape,
pilot-phase binding shape, runtime_role / agent_authority annotation,
vacuous_review_session granularity) are deliberately **not** in v3.1. Those
introduce new falsifier shapes or new rubric-vocabulary fields — they are
new kit machinery, not patches to existing machinery. They belong in v4
after a precheck pass and ADR work.

## Changes

### 1. Windows cp1252 stdout hardening (preflight)

**File:** `preflight.py`

`preflight.py` reconfigures `sys.stdout` and `sys.stderr` to utf-8 with
`errors="replace"` on import, before any check runs. Advisory messages
containing non-ASCII characters (the backward-edit warning, anything a future
check prints that uses Unicode) no longer crash on the default Windows
console encoding.

**Friction:** trio kit-friction.md 2026-05-03 — *"assumptions.py uses Unicode
arrow that crashes on Windows cp1252 stdout"*. A true-positive backward-edit
warning containing `→` (U+2192) crashed preflight with `UnicodeEncodeError`
before the warning could be surfaced.

### 2. Windows cp1252 subprocess hardening

**Files:** `assumptions.py`, `reachability.py`

Every kit-shipped `subprocess.run` call that passes `text=True` now also
passes `encoding="utf-8", errors="replace"`. Specifically:

- `assumptions._git` (used by `detect_backward_deadline_edits` to read
  `git log -p` output). Without this, any commit message or diff body
  containing a non-ASCII character raises `UnicodeDecodeError` on Windows
  and the backward-edit scan dies.
- `reachability.probe_script` (the bounded Python escape-hatch). Without
  this, a probe script that prints any non-ASCII byte to stdout crashes
  decoding on Windows.

**Friction:** trio kit-friction.md 2026-05-04 — *"Python subprocess on
Windows defaults to cp1252 stdin, fails on §/≥ in prompts"*. Trio's first
real-CLI battery crashed mid-trial with `UnicodeEncodeError: 'charmap'
codec can't encode character '≥'`. The same shape applies to any
kit-shipped subprocess.

### 3. Defense-in-depth ASCII advisory strings

**Files:** `assumptions.py`, `preflight.py`, `reachability.py`

Backward-edit warning strings, missing-file assertions, and probe-failure
details that previously used Unicode arrows or em-dashes now use ASCII
(`->`, `--`). Combined with the stdout reconfigure above, this gives
belt-and-suspenders coverage: if reconfigure ever fails (detached stream,
embedded interpreter) or if the string is consumed by a downstream cp1252-
bound tool (CI log scraper, grep pipeline), the message still survives.

Touched advisory strings:
- `assumptions.detect_backward_deadline_edits`: `→` → `->`.
- `preflight.check_decisions_have_template`: em-dash → `--`.
- `preflight.check_non_determinism_policy_exists`: em-dash → `--`.
- `preflight.check_active_phase_exists`: em-dash → `--`.
- `reachability.probe_script` rule-4 detail: em-dash → `--`.

**Friction:** same as (1) and (2); also generalized from kit-friction.md
2026-05-03 — *"every kit message string that uses non-ASCII characters is
a Windows-stdout time bomb"*.

### 4. Windows env passthrough for `probe_script`

**File:** `reachability.py` (`probe_script`)

On `sys.platform == "win32"`, `probe_script` now passes through these
environment variables in addition to the existing `PATH` + `PYTHONIOENCODING`:

- `USERPROFILE`, `APPDATA`, `LOCALAPPDATA` — user-profile roots Node.js
  needs to resolve npm module installs.
- `TEMP`, `TMP` — Windows temp roots.
- `COMSPEC` — path to `cmd.exe`; subprocess needs this to launch `.CMD`
  shims.
- `PATHEXT` — extensions Windows treats as executable.
- `SystemRoot` — required by Node.js to bootstrap.

These variables do not typically carry project secrets; secrets belong in
**Auth env** per the existing convention. The strict-strip behavior remains
in effect for everything else: nothing is invented, no shell is invoked.

**Friction:** trio kit-friction.md 2026-05-03 — *"reachability.py
probe_script env stripped too aggressively for Windows .CMD shims"*. Trio's
reachability probes against npm-installed CLIs (`claude.CMD`, `codex.CMD`,
`gemini.CMD`) crashed with `NotADirectoryError` or Node.js `STATUS_BREAKPOINT`
because the sparse `{PATH, PYTHONIOENCODING}` env left the shims unable to
resolve cmd.exe or bootstrap Node.

### 5. Per-probe `Env passthrough:` field

**File:** `reachability.py` (`probe_script`); documented in
`goals/reachability.md`.

A probe block may now declare an explicit comma-separated list of
additional environment-variable names to pass through:

```
**Env passthrough:** MY_TOOL_HOME, MY_TOOL_CONFIG
```

Values are read from the parent `os.environ` only. Nothing is invented.
This is the explicit-opt-in companion to the Windows defaults in (4): a
probe author who knows the CLI they're targeting needs `MY_TOOL_HOME` can
say so in the probe block rather than having the kit ship an open-ended
allowlist. Secrets should still go in **Auth env**.

**Friction:** trio kit-friction.md 2026-05-03 (same entry) — the friction
explicitly proposed both the OS-floor and the per-probe allowlist as
alternatives; v3.1 ships both, because they cover non-overlapping cases.

### 6. `check_coverage.py --strict-named-tests`

**File:** `check_coverage.py`

New flag scans `goals/phase_*/REQUIREMENTS.md` prose for `test_R_N_X_<descriptor>`
references and FAILs if any named test is not defined in `tests/test_phase_N.py`.
This complements the existing `--strict` flag, which counts marker presence
per requirement: a requirement with multiple named sub-clause tests passes
`--strict` if any one marker exists, so sub-clause-name drift slips through.

Recommended at ratification:

```
python check_coverage.py --strict --strict-named-tests
```

Implementation: regex `\btest_R_(\d+)_(\d+)_([a-z][a-z0-9_]*)\b` against
the REQUIREMENTS.md prose, regex `^\s*def\s+(test_R_\d+_\d+_[a-z][a-z0-9_]*)\s*\(`
against the test files. Missing defs are listed individually in the failure
message.

**Friction:** trio kit-friction.md 2026-05-05 — *"check_coverage.py --strict
counts requirement markers, not sub-clause-named tests"*. Phase 2 ratified
with `test_R_2_9_prompt_injection_aborts` named in REQUIREMENTS.md prose but
never written. The missing test was load-bearing on Phase 3 entry; it
surfaced only at the Phase 3 ramp survey and had to be retrofitted as the
first Phase 3 work item (R-3.0).

### 7. ADR Errata convention

**Files:** `decisions/0000-template.md`, `CLAUDE.md` §7

Accepted ADRs remain immutable, with one carve-out: an optional `## Errata`
appendix may be added below `## Consequences` for typo-class corrections:

- Spelling/grammar.
- Stale phrasing left over from a draft Option that was rejected before
  the ADR was accepted (e.g., a Consequences line that still names Option
  2 after the ADR was revised to Option 3 pre-acceptance).
- Broken cross-references.

Errata that change what the ADR commits the project to are NOT errata.
Those are scope changes and require a new, superseding ADR. Format is one
dated line per entry. The section is absent (header deleted) until the
first erratum is actually needed.

**Friction:** trio kit-friction.md 2026-05-03 — *"ADR-0004 Consequences
section has wording inconsistency from Option 2 → Option 3 revision"*. The
operative contract (Decision section + the actual provider code) was
correct; the Consequences section retained stale Option-2 phrasing.
Reading the ADR end-to-end was mildly confusing, but the kit's
ADR-immutability rule offered no legitimate home for the typo fix. The
Errata convention gives one — without weakening immutability for
substantive content.

## Deferred to v4 (not in v3.1)

The following frictions are logged in trio's kit-friction.md but are
explicit v4 evolution-pressure items. They introduce new vocabulary
(falsifier shapes, rubric annotations) rather than patching existing
machinery, so they are deferred to v4 after a precheck pass:

- **Frame-validity falsifier shape** (kit-friction 2026-05-10): a new
  `type = "frame_validity"` keel-binding block for construct-validity
  audits. The FlyBodyGate finding showed v3's `behavioral` and
  `statistical_inference` shapes cannot express a falsifier that catches
  parameter-vs-referent-system unvalidation. Trio's
  `goals/phase_3/CLOSURE.md` + ADR-0015 form a worked example of what v4
  should be able to detect mechanically.
- **Pilot-phase falsifier shape** (kit-friction 2026-05-10): a new
  `type = "pilot_phase"` keel-binding block for population-statistic
  falsifiers over a continuously-growing population with an ambient
  threshold-gate. Trio's ADR-0014 + `pilot.py` form a working prototype.
- **`runtime_role` / `agent_authority` annotation** (kit-friction
  2026-05-04): machine-readable annotation on rubric fields and ADR
  artifacts indicating which fields are the human's call vs. which the
  orchestrator fills. Designed to be robust against auto-mode agent
  runtimes that bias toward task completion and treat author-only fields
  as checklist items.
- **`vacuous_review_session` granularity** (kit-friction 2026-05-03):
  response-level vocabulary for the §3.8 structured-feedback contract,
  beyond the existing per-item granularity. Sits at the intersection of
  kit-friction and project-internal methodology; needs a precheck pass
  before becoming kit-shipped vocabulary.

## Upgrade path

For a v3 project upgrading to v3.1 in place:

1. Replace `preflight.py`, `assumptions.py`, `reachability.py`,
   `check_coverage.py` with the v3.1 versions.
2. Replace `decisions/0000-template.md` to pick up the Errata section
   explainer (existing accepted ADRs are untouched).
3. Replace `CLAUDE.md` to pick up the v3.1 version stamp and the §7
   Errata reference.
4. Optionally update `goals/reachability.md` to mention the `Env
   passthrough:` field.
5. Run `python preflight.py` and `python check_coverage.py --strict
   --strict-named-tests` to confirm clean upgrade.

No data migration. No phase rollback. No ADR re-ratification.
