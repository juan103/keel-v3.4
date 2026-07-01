# KEEL Project Kit v3.2 — Release Notes

v3.2 is an additive patch over v3.1. No v3.1 contract is removed and no
existing check changes behavior. Three additions: a systematic bug
protocol, a preferred-paradigm declaration, and a `resources/` reference
set consolidating the kit lineage.

The v4-scope items deferred by v3.1 (frame-validity binding shape,
pilot-phase binding shape, `runtime_role`/`agent_authority` annotation,
`vacuous_review_session` granularity) remain deferred — see
`resources/merged-kit-friction.md` Part 3 for the full open-pressure list.

## Changes

### 1. Bug protocol (`BUGS.md`, `CLAUDE.md` §11, preflight `check_bug_log_exists`)

**Files:** `BUGS.md` (new), `CLAUDE.md` (new §11, §7 memory list, §10 third
log category), `preflight.py` (new check).

Project bugs get a first-class documented lifecycle:

1. Document in `BUGS.md` as `BUG-NNN` the moment observed.
2. Reproduce with a failing `test_BUG_NNN_<descriptor>` test (test-first
   applied to bugs).
3. Diagnose — root cause recorded; status `diagnosed`.
4. Fix — smallest change that makes the reproduction pass.
5. The reproduction test stays in the suite forever (removal needs an ADR).
6. Close as `fixed` (commit referenced) or `wontfix` (reason; ADR if
   load-bearing).

`check_bug_log_exists` asserts the file exists, validates every `Status:`
against the four lifecycle states, and prints a `[WARN]` listing open bugs
at every preflight run so they stay visible.

**Motivation:** the kit had no home for project bugs. `kit-friction.md` is
explicitly for kit bugs; `goals/load-bearing-assumptions.md` is for
methodological risks (CLAUDE.md §10 enforces that split). Project bugs were
fixed ad hoc, leaving no record and no regression test. The protocol closes
that gap with the kit's existing grammar: written artifact + executable
verification + lifecycle states (mirroring the assumptions ledger).

### 2. Preferred paradigm (`goals/PARADIGM.md`, `CLAUDE.md` §12, preflight `check_paradigm_declared`)

**Files:** `goals/PARADIGM.md` (new), `CLAUDE.md` (new §12, §7 memory
list), `preflight.py` (new check).

The project declares its programming paradigm (e.g., object-oriented;
functional core / imperative shell; procedural; or an explicitly
partitioned mix) and the concrete conventions that follow, once, at project
setup. New code follows the declaration; deviations need a stated reason;
deviations that constrain future code are forks (§4) and need an ADR.
Changing the declaration itself goes through an ADR, not silent drift.

`check_paradigm_declared` fails while the `## Paradigm` section is still
the shipped placeholder — same forcing-function pattern as
`check_falsifier_declared`.

**Motivation:** paradigm choice is a fork by the §4 criteria (multiple
reasonable options, constrains future code beyond one function) but was
never prompted, so each session re-decided it implicitly and codebases
drifted into mixed styles. Declaring it once makes the choice visible,
ratified, and checkable.

### 3. `resources/` reference set

**Files:** `resources/keel-elements-catalog.md`,
`resources/merged-kit-friction.md`, `resources/methods-dictionary.md`
(all new).

- **Elements catalog** — every element in v2 / v3 / v3.1 /
  v3.1_op_proposal2 / v3.2 with a version matrix, what each does, and
  tier guidance (research-grade takes everything; hobby-grade takes the
  spine, per the op_proposal2 worked example).
- **Merged friction archive** — all real friction entries across the
  lineage in one place: the 16 canonical entries (beliefwire + v3-build,
  2026-05-02), the 9 trio entries (2026-05-03..2026-05-10, reconstructed
  from `CHANGELOG-v3.1.md` citations since the trio repo is external), and
  the carried-forward open-pressure list. Each entry carries a disposition
  (FIXED-vN / DEFERRED-v4 / CANDIDATE / PROJECT). This is an archive —
  live friction still goes in the project's own `kit-friction.md`.
- **Methods dictionary** — every function in every kit Python module
  (`preflight.py`, `check_coverage.py`, `state.py`, `binding.py`,
  `assumptions.py`, `reachability.py`, `tests/conftest.py`) with the
  version it appeared in and what it does, plus removed/superseded items.

**Motivation:** by v3.1 the lineage spans five kit folders; knowing what
elements exist, why they exist, and what the kit can already check
required diffing folders. New projects start from one catalog instead.

## Upgrade path

For a v3.1 project upgrading to v3.2 in place:

1. Copy `BUGS.md` and `goals/PARADIGM.md` into the project; fill in
   PARADIGM.md (for an existing codebase, declare the paradigm the code
   already follows — or the one it should converge to, via an ADR).
2. Replace `preflight.py` with the v3.2 version (adds the two checks; all
   v3.1 checks unchanged).
3. Replace `CLAUDE.md` with the v3.2 version (new §11/§12, version stamp).
4. Optionally copy `resources/` for reference.
5. Run `python preflight.py` to confirm a clean upgrade.

No data migration. No phase rollback. No ADR re-ratification.
