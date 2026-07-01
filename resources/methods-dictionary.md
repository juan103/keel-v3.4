# KEEL Methods Dictionary

Every function shipped in any KEEL kit version's Python modules, with the
version where it first appeared and what it does. Use this to know what the
kit can already check before writing a new check, and to see what changed
between versions.

Conventions: leading-underscore functions are internal helpers. "v3" means
introduced in v3 and present in v3.1/v3.2/v3.3 unchanged unless noted. v3.3
inherits all of v3.2; v3.3-only additions and behavior changes are in the
last sections.

---

## preflight.py — executable project invariants

Run at session start and on every commit (via the pre-commit hook). Each
check raises `AssertionError` on failure; `main()` runs them all and exits
non-zero if any fail. Checks accumulate across phases and are never removed
without a superseding ADR. v3.3 adds two modes: `--compliance` (print the
CLAUDE.md §0 block from disk and exit) and `--strict` (ratification mode —
reachability probes run live and block).

| Method | Since | What it does |
|---|---|---|
| `check_project_structure()` | v2 | Asserts the scaffolding exists: `CLAUDE.md`, `goals/GOALS.md`, `decisions/`, `tests/`, `kit-friction.md`. |
| `check_decisions_have_template()` | v2 | Asserts `decisions/0000-template.md` exists so new ADRs have a template. |
| `check_non_determinism_policy_exists()` | v2 | Asserts `decisions/0001-non-deterministic-testing.md` exists (every project needs a testing policy for non-deterministic output). |
| `check_active_phase_exists()` | v2 | Asserts at least one `goals/phase_*/` folder exists and the latest has a `REQUIREMENTS.md`. |
| `check_falsifier_declared()` | v2 | Asserts `GOALS.md` has a `## Falsifier` section and the placeholder text has been replaced (forces the precheck to actually happen). |
| `check_falsifier_consistency()` | v3 | Delegates to `binding.check_falsifier_consistency`: structural validation of `keel-binding` blocks + scan of GOALS.md falsifier prose against `rejected_prose`. Skips silently in precheck state. |
| `check_pre_stamp_review_exists()` | v3 | Delegates to `assumptions.check_pre_stamp_review_exists`. State-aware: skip in precheck, warn in pre_stamp, fail in post_stamp. |
| `check_load_bearing_assumptions_closed_at_gate()` | v3 | Delegates to `assumptions`: refuses ratification when any assumption due at or before the current gate is still `unverified`; prints advisory warnings for backward deadline edits. |
| `check_reachability_probes_pass()` | v3 (**rewritten v3.3**) | Delegates to `reachability`. v3.3 scoping: in session mode a cached pass (<24h, `.reachability-cache.json`) is accepted and live failures degrade to `[WARN]`; under `--strict` probes run live and failures FAIL (the v3..v3.2 behavior). Structural reachability.md errors fail in both modes. Skips silently if no file / no probes. |
| `check_bug_log_exists()` | v3.2 (**hardened v3.3**) | Asserts `BUGS.md` exists and every entry's `Status:` uses a valid lifecycle state. Warns (does not fail) on open bugs. v3.3: entry-based parse — an entry with NO Status line now fails (previously passed silently). |
| `check_paradigm_declared()` | v3.2 | Asserts `goals/PARADIGM.md` exists and the `## Paradigm` placeholder has been replaced with an actual declaration. |
| `check_adr_immutability()` | **v3.3** | Delegates to `adr_guard.detect_adr_mutations`: every accepted ADR is compared against its acceptance commit; changes outside `## Errata` / the Status line FAIL. Silent skip outside a git repo. |
| `_read_reachability_cache()` / `_write_reachability_cache(ok)` | **v3.3** | Session-mode probe cache (`.reachability-cache.json`, gitignored). |
| `emit_compliance_block()` | **v3.3** | Prints the CLAUDE.md §0 block from files on disk: inferred state, falsifier first paragraph (placeholder flagged), every keel-binding block's metadata, executable-check location. |
| `_first_paragraph(section)` | **v3.3** | First non-empty blank-line-delimited paragraph of a section body. |
| `_find_falsifier_test()` | **v3.3** | Locates the executable falsifier check: behavioral binding block `test` field, else `def test_*falsifier*` scan of tests/, else None. |
| `_format_binding_block(adr, block)` | **v3.3** | One-line rendering of a keel-binding block for the compliance output. |
| `main(argv=None)` | v2 (**flags v3.3**) | Runs all checks, prints `[OK]`/`[FAIL]` per check, exits 1 if any failed. v3.3: argparse with `--compliance` and `--strict`. |

Module-level (v3.1): reconfigures `sys.stdout`/`sys.stderr` to utf-8 with
`errors="replace"` on import, so advisory messages survive Windows cp1252
consoles. Module-level (v3.3): `STRICT` flag set by `main()`.

## check_coverage.py — requirement-to-test coverage

| Method | Since | What it does |
|---|---|---|
| `find_requirements()` | v2 | Scans `goals/phase_*/REQUIREMENTS.md` for `R-N.X` requirement IDs. |
| `find_test_markers()` | v2 | Scans `tests/` for `@pytest.mark.requirement("R-N.X")` markers. |
| `find_named_test_references()` | v3.1 | Scans REQUIREMENTS.md prose for `test_R_N_X_<descriptor>` names (sub-clause tests promised in prose). |
| `find_named_test_definitions()` | v3.1 | Scans `tests/` for `def test_R_N_X_<descriptor>(...)` definitions. |
| `find_tracked_test_functions()` | **v3.3** | Static scan for every test subject to the red-run evidence check: functions carrying a requirement marker, plus `test_BUG_NNN_*` reproductions. Returns `(file, name)` pairs. |
| `load_first_outcomes()` | **v3.3** | Loads `tests/.first-outcome-log.json` (missing/corrupt → `{}`). |
| `check_red_green(tracked, log)` | **v3.3** | Failure messages for tracked tests with no recorded run or whose first recorded outcome was a pass (no red run ever observed). Parametrized variants share the function; any red counts. |
| `main()` | v2 | Default mode: orphan markers FAIL (typos), untested requirements WARN (normal mid-phase). `--strict` (v3): untested requirements also FAIL. `--strict-named-tests` (v3.1): named-in-prose but undefined tests FAIL. `--strict-red-green` (v3.3): tracked tests without red-run evidence FAIL. All three strict flags run at ratification. |

## state.py — filesystem state inference (v3)

Infers where the project is in its lifecycle from files on disk, so other
checks can be state-aware.

| Method | Since | What it does |
|---|---|---|
| `_has_keel_binding(repo_root)` | v3 | True if any markdown under `decisions/` contains a fenced `keel-binding` block. |
| `_is_in_tests_path(rel_parts)` | v3 | True if a path is inside `tests/` (any depth) or a `test_*` file — excluded from stamp-artifact detection. |
| `_has_stamp_artifacts(repo_root)` | v3 | post_stamp signal: `bundle/` contains a non-scaffolding file (per ADR-0011). |
| `_commitment_artifact_path(repo_root)` | v3 | Reads `GOALS.md ## Commitment-artifact` and returns the resolved path, or None. |
| `_has_commitment_artifact(repo_root)` | v3 | Override signal: GOALS.md names a commitment artifact AND it exists. |
| `detect_dimension_1(repo_root)` | v3 | Returns `'precheck'` \| `'pre_stamp'` \| `'post_stamp'`. |
| `detect_phase_state(repo_root)` | v3 | Returns `(current_gate, active_phase)` inferred from `RATIFIED` markers and phase folders. |
| `detect(repo_root)` | v3 | Full state dict: `dimension_1`, `current_gate`, `active_phase`. |

## binding.py — keel-binding parser & falsifier consistency (v3)

| Method | Since | What it does |
|---|---|---|
| `extract_keel_binding_blocks(path)` | v3 | Finds every fenced `keel-binding` TOML block in a file and returns parsed dicts. |
| `validate_block(block)` | v3 | Layer 1 structural validation (required fields per binding type: statistic/null/alpha/p_value for `statistical_inference`, behavior/test for `behavioral`). Returns error list. |
| `get_active_values(block)` | v3 | Returns the canonical tokens the block names as active. |
| `find_binding_adrs(repo_root)` | v3 | Finds `decisions/**/*.md` files containing at least one keel-binding fence. |
| `_extract_section(text, section_name)` | v3 | Returns the body of a `## <section>` block, or None. |
| `check_falsifier_consistency(repo_root)` | v3 | Layer 1 + Layer 2: validates all blocks, then scans the GOALS.md `## Falsifier` prose for any surface form the binding ADR lists in `rejected_prose`. The mechanical guard against the "§0 anchored on stale narrative" failure. |

## assumptions.py — load-bearing assumptions & review gates (v3)

| Method | Since | What it does |
|---|---|---|
| `_import_state()` | v3 | Lazy import of `state.py` for state-aware checks. |
| `check_pre_stamp_review_exists(repo_root)` | v3 | Returns `('ok'\|'warn'\|'fail', message)` depending on Dimension 1: the adversarial pre-stamp review must exist before stamping. |
| `parse_assumptions_md(path)` | v3 | Parses `goals/load-bearing-assumptions.md` into assumption dicts (id, state, deadline). |
| `_parse_deadline_gate(value)` | v3 | Extracts the gate number from a `Resolution required before:` value. |
| `check_load_bearing_assumptions_closed_at_gate(repo_root, ...)` | v3 | Error list: assumptions due at or before the current gate still `unverified` block ratification (ADR-0009). |
| `_git(args, cwd)` | v3 (utf-8 hardened v3.1) | Runs a git command; returns None when git/repo unavailable. |
| `detect_backward_deadline_edits(repo_root)` | v3 (ASCII strings v3.1) | Scans git history for `Resolution required before:` edits that move a deadline backward — advisory warning (forbidden by CLAUDE.md §10). |

## adr_guard.py — ADR immutability guard (v3.3)

| Method | Since | What it does |
|---|---|---|
| `_git(args, cwd)` | v3.3 | Runs a git command; None on failure (same pattern as `assumptions._git`). |
| `_is_git_repo(repo_root)` | v3.3 | `.git` presence or `git rev-parse --git-dir`. |
| `_normalize(text)` | v3.3 | Unifies line endings, strips trailing whitespace — CRLF working trees vs LF blobs must not produce false mutation reports. |
| `_strip_mutable(text)` | v3.3 | Removes the legitimately-mutable parts before comparison: the `## Errata` section and the `**Status:**` line. |
| `_acceptance_commit(repo_root, rel)` | v3.3 | First commit in which the file's Status line said accepted/superseded; None if never committed accepted. |
| `detect_adr_mutations(repo_root)` | v3.3 | Error list: accepted ADRs whose content changed since their acceptance commit outside the mutable parts. Empty == OK; silent skip outside git. Consumed by preflight `check_adr_immutability` (blocking). |

## reachability.py — typed external-dependency probes (v3)

| Method | Since | What it does |
|---|---|---|
| `validate_probe(probe)` | v3 | Validates a probe block (required fields per type). Returns error list. |
| `parse_reachability(repo_root)` | v3 | Parses `goals/reachability.md` into probe dicts. |
| `_parse_status_threshold(condition, default=500)` | v3 | Extracts the HTTP status threshold from a probe condition. |
| `_parse_cert_substring(condition)` | v3 | Extracts the expected certificate subject/SAN substring. |
| `_build_auth_headers(probe)` | v3 | Builds auth headers from the probe's `Auth env:` variable names (values from env only — nothing invented). |
| `_http_fetch(url, headers, timeout)` | v3 | HEAD request, falls back to GET on 405/501; returns status. |
| `_https_fetch_with_cert(url, headers, timeout)` | v3 | HTTPS fetch that also returns the peer certificate for subject/SAN matching. |
| `_dns_resolve(host)` | v3 | Resolves a hostname to address strings; raises on failure. |
| `_result(passed, details, error)` | v3 | Builds the standard probe-result dict. |
| `probe_http_status(probe)` | v3 | Plain HTTP status-threshold probe. |
| `probe_https_tls(probe)` | v3 | Status threshold + certificate subject/SAN substring probe (catches ISP sinkholes serving wrong certs — the beliefwire geo-block class). |
| `probe_dns(probe)` | v3 | Hostname resolution + optional CIDR block-list probe. |
| `probe_script(repo_root, probe)` | v3 (Windows env passthrough + `Env passthrough:` field v3.1) | Bounded Python escape hatch: requires `Script probe: true`, a reason, a tracked path under `scripts/probes/`, Python-only execution, stripped environment. |
| `run_probe(repo_root, probe)` | v3 | Dispatches a probe dict to the right `probe_*` function by `Type`. |
| `check_reachability_probes_pass(repo_root)` | v3 | Runs every declared probe; returns error messages. Empty/missing file passes silently. (v3.3 note: preflight now decides cache/warn/block policy around this call; this function itself is unchanged.) |

## scripts/hooks/protect_adrs.py — Claude Code PreToolUse hook (v3.3)

| Method | Since | What it does |
|---|---|---|
| `main()` | v3.3 | Reads the pending Edit/Write tool call as JSON from stdin; if the target is an existing accepted ADR under `decisions/`, emits permission decision "ask" with the §7 rationale so the human ratifies the edit. New/proposed ADRs, the template, and everything else pass through. Always exits 0 — a hook crash must never block unrelated edits. |

## tests/conftest.py

| Method | Since | What it does |
|---|---|---|
| `pytest_configure(config)` | v2 | Registers the `requirement(id)` marker so `@pytest.mark.requirement("R-N.X")` doesn't warn. |
| `_load_log()` / `_git_head()` | **v3.3** | Lazy log load; short HEAD hash for evidence context. |
| `pytest_collection_modifyitems(config, items)` | **v3.3** | Collects the nodeids subject to first-outcome recording (requirement-marked + `test_BUG_*`). |
| `pytest_runtest_logreport(report)` | **v3.3** | Records each tracked test's FIRST call-phase outcome (`failed`/`passed`) once; skips and setup errors are not recorded. |
| `pytest_sessionfinish(session, exitstatus)` | **v3.3** | Writes `tests/.first-outcome-log.json` (sorted, committed) if anything new was recorded. |

## Removed / superseded along the way

| Item | Was in | Fate |
|---|---|---|
| Active example tests `test_R_1_1_example_pattern()`, `test_R_1_3_snapshot_pattern()` | v2 `tests/test_phase_1.py` | Removed in v3 — active placeholder tests blocked Gate-0 commits (friction 2026-05-02). Patterns moved to `tests/PATTERNS.md`. |
| Entire Python toolchain | v3.1_op_proposal2 | Deliberately not shipped at hobby scale; playtest log replaces executable falsification. |
| Hand-assembled §0 compliance block | v2..v3.2 `CLAUDE.md` §0 | Superseded in v3.3 by `preflight.py --compliance` (kept as the documented fallback when Python is unavailable). |

## New in v3.2

| Method | File | What it does |
|---|---|---|
| `check_bug_log_exists()` | `preflight.py` | `BUGS.md` must exist; every `Status:` value must be one of `open` / `diagnosed` / `fixed` / `wontfix`; open bugs print a `[WARN]` listing so they stay visible at every session start. |
| `check_paradigm_declared()` | `preflight.py` | `goals/PARADIGM.md` must exist and its `## Paradigm` section must not be the placeholder — forces the paradigm fork (OOP vs functional vs procedural vs mixed) to be decided once, at project start. |

## New in v3.3

| Method | File | What it does |
|---|---|---|
| `emit_compliance_block()` (+ `_first_paragraph`, `_find_falsifier_test`, `_format_binding_block`) | `preflight.py` | Mechanical CLAUDE.md §0 block from files on disk (`--compliance`). |
| `check_adr_immutability()` | `preflight.py` | Blocking ADR-mutation check; delegates to `adr_guard`. |
| `_read_reachability_cache()` / `_write_reachability_cache()` | `preflight.py` | Session-mode probe cache; `--strict` bypasses it. |
| `detect_adr_mutations()` (+ helpers) | `adr_guard.py` | Accepted-ADR diff against the acceptance commit, Errata/Status exempt. |
| `find_tracked_test_functions()`, `load_first_outcomes()`, `check_red_green()` | `check_coverage.py` | The `--strict-red-green` red-run evidence check. |
| first-outcome recorder hooks | `tests/conftest.py` | Records each tracked test's first observed outcome to `tests/.first-outcome-log.json`. |
| `main()` | `scripts/hooks/protect_adrs.py` | PreToolUse "ask" guard for accepted ADRs. |
