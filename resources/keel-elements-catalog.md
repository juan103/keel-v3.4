# KEEL Elements Catalog

Every element that exists in any KEEL kit version so far (v2, v3, v3.1,
v3.1_op_proposal2, v3.2, v3.3). Use this when starting a new project to
decide which elements the project needs. Elements marked **core** are the
spine every KEEL project carries; the rest are tiered — research-grade
projects take everything, hobby-grade projects take the spine only (see
the v3.1_op_proposal2 subversion for the worked example of stripping).

Legend: v2 / v3 / v3.1 / op2 (= v3.1_op_proposal2) / v3.2 columns show the
version where the element exists. "—" means absent in that version.
**v3.3 inherits every v3.2 element unchanged unless noted; v3.3-only
additions are in the "New in v3.3" section near the end.**

---

## 1. Discipline documents (prose contracts)

| Element | File | v2 | v3 | v3.1 | op2 | v3.2 | What it does |
|---|---|---|---|---|---|---|---|
| **Operating rules** (core) | `CLAUDE.md` | x | x | x | x (lean) | x | Non-negotiable session rules: compliance check, orientation order, phase model, work cycle, fork protocol, falsifier rule, memory rules, style. |
| **Compliance check §0** (core) | `CLAUDE.md` §0 | x (1-line) | x (3-line) | x (3-line) | x (4-line, playtest) | x (3-line) | Agent must quote the falsifier (and binding metadata + executable-check location since v3) verbatim in its first message. Proves the file was read. **v3.3: the block is emitted by `preflight.py --compliance` from disk; hand assembly is the documented fallback only.** |
| **Precheck prompt** | `PRECHECK_PROMPT.md` | x | x | x | — | x | Interrogation prompt run in a fresh session BEFORE implementation; its output fills `goals/GOALS.md`. |
| **Adversarial review prompt** | `ADVERSARIAL_REVIEW_PROMPT.md` | — | x | x | — | x | Multi-AI methodological review of the pre-registration draft before stamping. Separate gate from the precheck. |
| **Pre-stamp review record** | `pre-stamp-review.md` | — | x | x | — | x | Records the dispositions of adversarial-review findings. |
| **Kit README** (core) | `README.md` | x | x | x | x | x | What the kit is, first-use steps, every-session steps, phase workflow. |
| **Release notes / changelog** | `CHANGELOG-v*.md` | — | — | x | x | x | What changed vs the parent version, with the friction entry that motivated each change. |

## 2. Claim & goal artifacts (`goals/`)

| Element | File | v2 | v3 | v3.1 | op2 | v3.2 | What it does |
|---|---|---|---|---|---|---|---|
| **Claim contract** (core) | `goals/GOALS.md` | x | x | x | x | x | What we're testing, what would falsify it, what counts as success. Sections: Claim, Success criteria, Falsifier, Commitments, Non-commitments, Phases, Risks. |
| **Lineage section** | `GOALS.md ## Lineage` | — | x | x | — | x | Records the precheck input documents so content does not live only in an earlier proposal. (Friction 2026-05-02: v14↔GOALS.md delta.) |
| **Falsifier / kill condition** (core) | `GOALS.md ## Falsifier` | x | x | x | x (`## Kill condition`, playtest outcome) | x | The declared condition that kills the project. op2 grounds it in playtests instead of statistics. |
| **Phase requirements** (core) | `goals/phase_N/REQUIREMENTS.md` | x | x | x | x (`phases/phase_N/SCOPE.md`, freeform + `## Done when`) | x | Numbered requirements `R-N.X`, each bound to a test. |
| **Ratification marker** (core) | `goals/phase_N/RATIFIED` (empty file) | x | x | x | x (`phases/phase_N/RATIFIED`) | x | Phase N+1 cannot start until N is ratified by the human. |
| **Load-bearing assumptions ledger** | `goals/load-bearing-assumptions.md` | — | x | x | — (replaced by `GOALS.md ## Open questions`) | x | Methodological assumptions with lifecycle states (`unverified`/`verified`/`falsified`/`accepted-risk`/`retired`) and gate deadlines. Gate refuses to ratify with overdue `unverified` entries. |
| **Reachability declarations** | `goals/reachability.md` | — | x | x | — (prose `goals/dependencies.md` note) | x | Typed probes for external dependencies, run at Gate 0 BEFORE any pre-registration is stamped. (Friction: beliefwire closed on an undetected geo-block.) **v3.3: live-blocking at gates (`--strict`); cached/advisory in session mode.** |
| **Environment portability record** | `goals/environment.md` | — | x | x | — | x | Pre-stamp tooling checks and project-side workarounds (e.g. the OTS-on-Windows wrapper). |
| **Playtest log** | `goals/playtest-log.md` | — | — | — | x | — (take from op2 if building a game) | One entry per playtest with a `verdict:` field (`alive`/`weakening`/`killed`). The evidence channel for playtest-grounded kill conditions. |
| **Closure write-up** | `goals/CLOSURE.md` | — | (pattern from beliefwire/v3-build) | (same) | — | x (named in catalog) | When the kill condition fires, the closure write-up is the deliverable. |
| **Preferred paradigm declaration** | `goals/PARADIGM.md` | — | — | — | — | x | Declares the project's preferred programming paradigm (OOP, functional, procedural, mixed) and the conventions that follow from it. Checked by preflight. |

## 3. Decision artifacts (`decisions/`)

| Element | File | v2 | v3 | v3.1 | op2 | v3.2 | What it does |
|---|---|---|---|---|---|---|---|
| **ADR template** (core) | `decisions/0000-template.md` | x | x | x | x (lite) | x | Status / Context / Decision / Consequences (+ Errata since v3.1). 4-digit numbering. |
| **Starter ADR: non-determinism testing policy** | `decisions/0001-non-deterministic-testing.md` | x | x | x | — | x | When to use example, property-based (Hypothesis), and snapshot tests. |
| **ADR immutability rule** (core) | `CLAUDE.md` §7 | x | x | x | x | x | Accepted ADRs are immutable; superseding requires a new ADR. **v3.3: mechanically guarded — `adr_guard.py` + preflight `check_adr_immutability` (blocking) + the PreToolUse hook (interactive).** |
| **ADR Errata convention** | `0000-template.md` + `CLAUDE.md` §7 | — | — | x | x | x | One optional `## Errata` appendix for typo-class corrections only. Substantive changes still need a superseding ADR. |
| **Post-stamp ADR folder** | `decisions/post-stamp/` | — | x | x | — | x | ADRs added after the commitment-stamp event live separately from the immutable pre-stamp bundle. |
| **keel-binding metadata blocks** | TOML fences inside binding ADRs | — | x | x | — | x | Machine-readable falsifier metadata (statistic/null/alpha/p_value or behavior/test) parsed by `binding.py`; catches GOALS.md-prose vs binding-ADR drift. |

## 4. Executable checks (Python + hooks)

| Element | File | v2 | v3 | v3.1 | op2 | v3.2 | What it does |
|---|---|---|---|---|---|---|---|
| **Preflight** (core) | `preflight.py` | x (5 checks) | x (9 checks) | x (9, Windows-hardened) | — | x (11 checks) | Executable project invariants run at session start and on commit. **v3.3: 12 checks + `--compliance` and `--strict` modes.** See `resources/methods-dictionary.md` for every check. |
| **Coverage check** (core) | `check_coverage.py` | x | x (`--strict`) | x (`--strict`, `--strict-named-tests`) | — | x | Every requirement has a marked test; orphan markers always fail; strict modes for ratification. **v3.3: `--strict-red-green` red-run evidence.** |
| **State inference** | `state.py` | — | x | x | — | x | Infers precheck / pre_stamp / post_stamp state and current gate from files on disk. |
| **Binding parser** | `binding.py` | — | x | x | — | x | Parses/validates `keel-binding` blocks; falsifier consistency check against `rejected_prose`. |
| **Assumption checks** | `assumptions.py` | — | x | x | — | x | Ledger parsing, gate-closure refusal, backward-deadline-edit detection via git history. |
| **Reachability probes** | `reachability.py` | — | x | x | — | x | `https_tls`, `http_status`, `dns`, bounded `script` probes; Windows env passthrough since v3.1. |
| **Pre-commit hook** (core) | `.git-hooks/pre-commit` + `install_hooks.sh` | x | x | x | — | x | Runs preflight + tests + coverage on every commit. Portable interpreter detection; accepts pytest exit 5. |
| **Test patterns reference** | `tests/PATTERNS.md` | (live examples in test file) | x | x | — | x | Example-based, property-based, snapshot patterns — documented, not shipped as active tests (active examples blocked Gate-0 commits in v2). |
| **Pytest requirement marker** (core) | `tests/conftest.py` | x | x | x | (tests exist, unbound) | x | Registers `@pytest.mark.requirement("R-N.X")`. **v3.3: also records each tracked test's first observed outcome (red-run evidence).** |

## 5. Evolution & honesty logs

| Element | File | v2 | v3 | v3.1 | op2 | v3.2 | What it does |
|---|---|---|---|---|---|---|---|
| **Kit friction log** (core) | `kit-friction.md` | x | x | x | x | x | Where the KIT's own failures are logged. The kit evolves from real friction, not imagined improvements. |
| **Kit-friction vs assumptions split** | `CLAUDE.md` §10 | — | x | x | x (friction vs open questions) | x | Kit bugs and project-internal methodological risks go to different logs with different monitoring. |
| **Bug log & protocol** | `BUGS.md` + `CLAUDE.md` §11 | — | — | — | — | x | Systematic protocol for project bugs: document → reproduce with a failing regression test → fix → test stays. Lifecycle states per entry. Distinct from kit-friction (kit bugs) and assumptions (methodological risks). |

## 6. Process rules (live in CLAUDE.md, no file of their own)

| Rule | Section | Since | Summary |
|---|---|---|---|
| **Phase/gate model** (core) | §2 | v2 | Numbered phases; each is a gate; no skipping; ratification by human. |
| **Test-first work cycle** (core) | §3 | v2 | State requirement → choose test type → test first, watch it fail → smallest code → re-run all → preflight. **v3.3: the red run is recorded mechanically.** |
| **Fork protocol** (core) | §4 | v2 | Stop and ask when ≥2 options + constrains future code + not already decided. Result becomes an ADR before the code. |
| **Falsifier rule** (core) | §5 | v2 | Every project has an early phase whose job is to kill the project. |
| **Executable > prose verification** (core) | §6 | v2 | A check the human relies on belongs in preflight or a test, not in prose. **v3.3 applied this to the kit itself (§0 emitter, ADR guard).** |
| **File-based memory** (core) | §7 | v2 | Conversation history is not memory. Anything you decide that isn't in a file did not happen. |
| **Style of work** (core) | §8 | v2 | Concise; push back; flag uncertainty; don't be encouraging by default. |
| **Default-to-artifact** (core) | §9 | v2 | When in doubt: produce an artifact, stop and ask, encode the check in code. |
| **Preferred paradigm rule** | §12 | v3.2 | New code follows the paradigm declared in `goals/PARADIGM.md`; deviations need a stated reason or an ADR. |

## 7. Companion practices (not kit files, but part of the discipline)

| Practice | Source | Notes |
|---|---|---|
| **OpenTimestamps stamping** | beliefwire project | Cryptographic commitment to the pre-registration bundle at Gate 0. Kit-adjacent; tooling portability belongs in `goals/environment.md`. |
| **Multi-AI iterative critique (trio)** | beliefwire → trio project | Independent AI reviewers iterate on the proposal until none can improve it. Guards against single-AI agreeable concession under conversational pressure. |
| **Versioning convention** | v2 status report, ADR-0002 (v3-build) | Kits are versioned; each project records which kit revision it was built under (CLAUDE.md header stamp). |
| **Subversion pattern** | v3.1_op_proposal2 | A kit may be deliberately stripped for a lower-stakes tier, keeping the spine, with each removal documented and justified in the changelog. |

## New in v3.3

| Element | File | Tier | What it does |
|---|---|---|---|
| **Mechanical §0 emitter** | `preflight.py --compliance` | core | Emits the session-start compliance block from files on disk (state, falsifier, binding metadata, executable-check location). The agent pastes it + a one-line read confirmation. |
| **ADR immutability guard** | `adr_guard.py` + preflight `check_adr_immutability` | core (any project with git) | Blocking diff of every accepted ADR against its acceptance commit; `## Errata` and Status accepted→superseded exempt. |
| **Claude Code hooks** | `claude-settings.template.json` + `scripts/hooks/protect_adrs.py` | recommended for agent-driven work | SessionStart injects the compliance block; PreToolUse asks the human before agent edits to accepted ADRs. Installed (never overwritten) by `install_hooks.sh`. |
| **Red-run evidence** | `tests/conftest.py` recorder + `tests/.first-outcome-log.json` + `check_coverage.py --strict-red-green` | core for research-grade; recommended elsewhere | First observed outcome of every requirement-marked test / BUG reproduction, recorded once, checked at ratification. |
| **Reachability probe scoping** | `preflight.py --strict` + `.reachability-cache.json` | applies wherever probes exist | Session mode: cached pass / advisory failures. Strict mode (gates, stamping): live + blocking. |

---

## Choosing elements for a new project

- **Research-grade** (claims about a referent system, external audience):
  take everything in v3.3.
- **Hobby/game-grade** (audience is friends, falsifier is "we stopped
  playing"): take the spine — CLAUDE.md (lean), GOALS.md with a kill
  condition, phases with SCOPE.md, ADR-lite, kit-friction.md, BUGS.md,
  PARADIGM.md — and ground verification in playtests. See
  `project-kit-v3.1_op_proposal2` for the worked stripping. Of the v3.3
  additions, the Claude Code hooks are worth keeping even at hobby scale
  (they cost nothing per session); the red-run log and ADR guard follow
  the executable-check tier.
- **In between**: start from the spine, add the executable checks
  (`preflight.py`, `check_coverage.py`, hook) as soon as correctness
  matters, add reachability probes the moment an external dependency
  appears, and add the assumptions ledger the moment the project leans on
  something unverified.
