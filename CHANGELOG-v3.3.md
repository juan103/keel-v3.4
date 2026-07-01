# KEEL Project Kit v3.3 — Release Notes

v3.3 is an additive patch over v3.2. Unlike v3.1 (trio field friction) and
v3.2 (lineage consolidation), v3.3 is driven by an **external design
review** of the kit (2026-06-10, full findings in
`resources/merged-kit-friction.md` Part 4). The review's theme: the kit's
own §6 rule ("executable verification beats prose verification") had not
been applied to the kit itself. The two most load-bearing prose rules —
the §0 compliance ritual and ADR immutability — and the work cycle's most
skippable step — watch the test fail — were enforced by agent obedience
and human vigilance. v3.3 makes them mechanical.

One pre-existing check changes behavior (reachability probes in session
mode — see change 5, with the compatibility note). Everything else is
additive: no v3.2 contract is removed.

The v4-scope items deferred by v3.1/v3.2 (frame-validity binding shape,
pilot-phase binding shape, `runtime_role`/`agent_authority` annotation,
`vacuous_review_session` granularity) remain deferred.

## Changes

### 1. Mechanical §0 compliance block (`preflight.py --compliance`, `CLAUDE.md` §0)

**Files:** `preflight.py` (new `--compliance` mode, `emit_compliance_block`,
`_first_paragraph`, `_find_falsifier_test`, `_format_binding_block`),
`CLAUDE.md` §0 (rewritten).

`python preflight.py --compliance` prints the session-start compliance
block generated from files on disk: inferred project state (`state.py`),
the GOALS.md `## Falsifier` first paragraph (with an explicit flag if it
is still the placeholder), every `keel-binding` block's metadata
(`binding.py`), and the executable falsifier check location (a behavioral
binding block's `test` field, else a `def test_*falsifier*` scan of
`tests/`, else "not yet implemented"). The agent's §0 duty is now: run the
command (or copy the SessionStart hook's injected output), paste the block
verbatim, add one line confirming CLAUDE.md was read.

**Motivation (review finding 1):** §0 violated §6. The block existed to
prove the operating rules were read, but it was produced by the agent
obeying prose — and was gameable: an agent could reproduce a plausible
block from conversation history or a compaction summary without reading
anything this session. All the data sources already existed in kit modules;
the block content is now code-emitted and cannot drift. What still proves
the file was read is knowing to run the command and the explicit
confirmation line.

### 2. ADR immutability guard (`adr_guard.py`, preflight `check_adr_immutability`)

**Files:** `adr_guard.py` (new), `preflight.py` (check #12), `CLAUDE.md` §7.

For every `decisions/**/*.md` whose Status is `accepted` (or `superseded` —
it was accepted first), the guard finds the acceptance commit (first commit
where the Status line said accepted), reconstructs that text, strips the
legitimately-mutable parts from both versions — the `## Errata` section
(v3.1 convention) and the `**Status:**` line (the accepted→superseded
transition) — normalizes line endings, and compares. Any other difference
fails preflight with the reverting `git checkout` command in the message.
Skips silently outside a git repo; an ADR never committed as accepted is
not yet protected.

**Motivation (review finding 3):** ADR immutability was the kit's most
load-bearing prose-only rule. Binding metadata, the stamp bundle, and the
fork protocol all rest on the ratified record not changing, yet nothing
detected a silent edit. The kit already had the pattern — 
`detect_backward_deadline_edits` scans git history for the assumptions
ledger — but only as an advisory. This one is blocking, because a mutated
ratified record is never legitimate.

### 3. Claude Code harness hooks (`claude-settings.template.json`, `scripts/hooks/protect_adrs.py`)

**Files:** `claude-settings.template.json` (new),
`scripts/hooks/protect_adrs.py` (new), `install_hooks.sh` (installs both).

Two hooks, installed to `.claude/settings.json` by `install_hooks.sh`
(never overwriting an existing settings.json; Windows `py`-launcher
patching included, mirroring the pre-commit hook's interpreter detection):

- **SessionStart** → `python preflight.py --compliance`. The compliance
  block is injected into the agent's context at session start — §0 no
  longer depends on the agent remembering to run anything.
- **PreToolUse** (Edit|Write) → `scripts/hooks/protect_adrs.py`. If the
  edit target is an existing accepted ADR, the hook returns permission
  decision "ask" so the human ratifies the edit before it happens. New
  ADRs, proposed ADRs, and the template pass through silently. This is the
  interactive half of change 2: the hook catches the edit before it
  happens; `check_adr_immutability` catches whatever the hook missed.

**Motivation (review finding 2):** "run preflight at session start" and
"begin with §0" were enforced only by the human noticing. The kit targeted
coding agents but used none of the agent harness's own enforcement
mechanisms; `install_hooks.sh` covered git only. The harness gives
mechanical enforcement for free.

**Note on shipping as a template:** the kit ships
`claude-settings.template.json` rather than a live `.claude/settings.json`
so that activating hooks is an explicit human act (running
`install_hooks.sh`), consistent with hooks executing commands on the
user's machine.

### 4. Red-run evidence (`tests/conftest.py` recorder, `check_coverage.py --strict-red-green`)

**Files:** `tests/conftest.py` (first-outcome recorder),
`check_coverage.py` (new flag, `find_tracked_test_functions`,
`load_first_outcomes`, `check_red_green`), `CLAUDE.md` §3/§11, `README.md`
(ratification command).

The conftest records the FIRST observed call-phase outcome of every
requirement-marked test and every `test_BUG_NNN_*` reproduction into
`tests/.first-outcome-log.json` (committed; written once per nodeid, never
overwritten; skips and setup errors not recorded — "fails for the right
reason" means a call-phase failure). At ratification,
`check_coverage.py --strict-red-green` fails any tracked test with no
recorded run or whose first outcome was a pass.

**Motivation (review finding 4):** coverage proved a marker existed, not
that the test bites. A vacuous `assert True` with the right marker passed
`--strict`, and §3 step 3 ("watch it fail") left no evidence. The recorder
closes the gap between "tests exist" and "tests were seen to fail before
the code existed" — for requirements and for §11 bug reproductions alike.

**Boundary:** the log is evidence, not state. If a red run genuinely
predates the recorder (e.g., upgrading mid-project), say so at
ratification; editing the log defeats it. The flag is opt-in at
ratification, so mid-phase work is unaffected.

### 5. Reachability probes scoped to gates (`preflight.py --strict`, session cache)

**Files:** `preflight.py` (`check_reachability_probes_pass` rewritten,
`--strict` flag, `.reachability-cache.json`), `.gitignore`, `README.md`.

- `--strict` (ratification/stamp): probes run live; failures FAIL —
  identical to v3..v3.2 behavior.
- Session mode (default): a cached pass younger than 24h is accepted
  without network I/O; otherwise probes run live, a pass refreshes the
  cache, and failures degrade to `[WARN]` with an explicit pointer to
  `--strict`. Structural errors in `reachability.md` (missing fields,
  unknown Type) still FAIL in both modes — they are file bugs, not network
  state.

**Motivation (review finding 5):** the v3 principle was "probes run at
Gate 0, before any pre-registration is stamped" — not "every commit needs
the network." Because the pre-commit hook runs preflight, a probe-bearing
project could not commit from an offline machine, and every session start
did network I/O. **This is v3.3's only behavior change to an existing
check:** session-mode probe failures no longer block. Projects that want
the old always-blocking behavior run `python preflight.py --strict`
everywhere (and may put it in the pre-commit hook).

### 6. BUGS.md parser hardening (preflight `check_bug_log_exists`)

**Files:** `preflight.py`.

The v3.2 line-scanner only validated `Status:` lines it found, so a
`BUG-NNN` entry with a missing Status line passed silently. The v3.3
entry-based parse splits on `### BUG-NNN` headers and fails any entry
without a Status line.

**Motivation (review finding, minor):** an entry outside the lifecycle is
exactly what the check exists to catch.

## Upgrade path

For a v3.2 project upgrading to v3.3 in place:

1. Replace `preflight.py`, `check_coverage.py`, `tests/conftest.py`,
   `install_hooks.sh` with the v3.3 versions; add `adr_guard.py`,
   `claude-settings.template.json`, `scripts/hooks/protect_adrs.py`.
2. Replace `CLAUDE.md` (new §0 procedure, version stamp, §3/§7/§11 notes).
3. Re-run `bash install_hooks.sh` to install the Claude Code hooks.
4. Add `.reachability-cache.json` to `.gitignore`.
5. Run the suite once (`python -m pytest tests/ -q`) to seed
   `tests/.first-outcome-log.json`, and commit it. Existing tests that
   were genuinely written test-first will record `passed` (their red runs
   predate the recorder) — declare that at the next ratification rather
   than back-filling the log; the check applies cleanly to all NEW tests.
6. Run `python preflight.py` and `python preflight.py --strict` to confirm
   a clean upgrade. `check_adr_immutability` may legitimately fire on ADRs
   that were silently edited in the past — each hit is either a revert or
   a retroactive superseding ADR. That is the check working.

No data migration. No phase rollback. No ADR re-ratification.
