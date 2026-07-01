# Merged Kit Friction Log (all KEEL versions through v3.3)

This file merges every `kit-friction.md` across the KEEL lineage into one
historical archive, so a new project (and future kit versions) can see the
full evolution pressure in one place.

**This is an archive, not a live log.** New friction in a v3.3 project goes
in the project's own `kit-friction.md` at the kit root, same format as
always.

Sources merged:

| Source | Status at merge time (2026-06-07) |
|---|---|
| `resources/kit-friction.md` (canonical log: beliefwire + v3-build entries) | 16 real entries, all dated 2026-05-02 |
| `project-kit-v2/kit-friction.md` | template only (example entry) |
| `project-kit-v3/kit-friction.md` | template only (example entry) |
| `project-kit-v3.1/kit-friction.md` | template only (example entry) |
| `project-kit-v3.1_op_proposal2/kit-friction.md` | empty template |
| `v3-build/kit-friction.md` | template only — its real entries were moved to the canonical log per its own cleanup note |
| trio project `kit-friction.md` (2026-05-03..2026-05-10) | **not present in this repo**; entries reconstructed below from the citations in `CHANGELOG-v3.1.md` |
| external design review of the kit (2026-06-10) | findings recorded in Part 4 below |

Disposition codes used below: **FIXED-vN** (addressed in kit version N),
**DEFERRED-v4** (logged as v4 evolution pressure), **CANDIDATE** (principle
recorded, not yet adopted), **PROJECT** (project-side lesson, not a kit bug).

---

## Part 1 — beliefwire + v3-build entries (canonical log, 2026-05-02)

### 2026-05-02 — ADR numbering convention reflex (3-digit vs 4-digit) — FIXED-v3

**What happened:** v14 proposal and the user's first execution prompt both wrote project ADRs as `ADR-001..009` (3-digit). The kit's `decisions/0000-template.md` uses `ADR-NNNN` (4-digit), and `preflight.py:check_non_determinism_policy_exists` hard-codes `decisions/0001-non-deterministic-testing.md` as a required file. So 3-digit numbering would either collide with the kit's existing ADR-0001 or require modifying preflight on the kit's first real test.

**What I did instead:** Continued the kit's 4-digit sequence. Kit's ADR-0001 (non-determinism testing) stays. Project ADRs are ADR-0002 through ADR-0010, with the user's ADR-001..009 mapping linearly to ADR-0002..0010.

**What would have worked better:** The kit's `0000-template.md` could open with a one-line note: "ADRs are numbered with 4 digits (`NNNN`), continuing from `0002` in any project that ships with `0001-non-deterministic-testing.md`." A reader who hadn't internalized the kit's existing ADR-0001 would otherwise reflexively start at `ADR-001`. Alternatively, the kit could ship with ADR-0001 numbered as `ADR-0010` or similar to avoid the collision pressure on user numbering, but that conflicts with the existing preflight check.

*Disposition: ADR numbering guidance shipped in v3 ("operational fixes from v2 use").*

---

### 2026-05-02 — v14 ↔ GOALS.md delta from precheck — FIXED-v3 (Lineage section)

**What happened:** v14 of the project proposal is a 12-section narrative document with extensive meta-commentary, methodological rationale, related-literature pointers, and probability-ordering paragraphs. KEEL v2's `GOALS.md` template demands seven structural sections (Claim, Success criteria, Falsifier, Commitments, Non-commitments, Phases, Risks). Translating v14 into GOALS.md format dropped a substantial fraction of the prose and reorganized the rest.

**What I did instead:** Drafted GOALS.md from v14 by mapping each v14 section to a GOALS.md section (claim, success criteria, falsifier verbatim, commitments as ADR pointers, non-commitments, phases gate-by-gate, risks as failure modes). Several v14 elements were dropped in translation and survive only in ADR prose or in v14 itself (notably the §12 reading list).

**What would have worked better:** The kit's `GOALS.md` template could include an explicit `## Sources` or `## Pre-precheck artifacts` section pointing to whatever document(s) the precheck operated on. Without that, the lineage from v14 to GOALS.md is invisible to a future reader. Suggested: add a one-line section `## Lineage` to the GOALS.md template, with a single bullet for the precheck input.

*Disposition: `## Lineage` shipped in the v3 GOALS.md template.*

---

### 2026-05-02 — Falsifier numerical content lives outside GOALS.md — FIXED-v3 (§0 three-line block)

**What happened:** GOALS.md `## Falsifier` quotes the v14 §5 kill condition verbatim. The numerical content of "stable" and "beyond" is in ADR-0002 + `predictions.md`, not in GOALS.md itself. Per CLAUDE.md §0, the compliance check requires quoting the falsifier verbatim from GOALS.md — a future Claude session will quote the prose form and not the numerical form. This is fine for compliance but means the "falsifier" Claude reports at session start is incomplete relative to the executable check.

**What I did instead:** Wrote the GOALS.md `## Falsifier` section to point explicitly at ADR-0002 + `predictions.md` as the location of the numerical content. The executable falsifier check (in `tests/test_phase_1.py` at Gate 1 time) is the actual binding artifact.

**What would have worked better:** The kit's CLAUDE.md §0 compliance check could ask Claude to additionally quote the file/line where the executable falsifier check lives, not just the prose statement. This would make the "prose vs code" gap visible at session start.

*Disposition: v3 §0 expanded to the three-line block (prose + binding metadata + executable check location).*

---

### 2026-05-02 — Pre-stamp / post-stamp ADR distinction is not in the kit — FIXED-v3

**What happened:** ADR-0010 introduces a distinction between pre-stamp and post-stamp ADRs (the former are part of the OTS bundle and immutable; the latter are not). The kit's `decisions/` folder structure has no concept of this. The kit's preflight check `check_non_determinism_policy_exists` hard-codes `decisions/0001-...md` and would not be aware of `decisions/post-stamp/...`.

**What I did instead:** Created `decisions/post-stamp/` and placed ADR-0009 and ADR-0010 there directly at Gate 0. The kit's preflight is unmodified.

**What would have worked better:** The kit could ship with `decisions/post-stamp/.gitkeep` and a one-line README in `decisions/` explaining that ADRs added after a project's commitment-stamp event live in `post-stamp/`.

*Disposition: `decisions/post-stamp/` scaffolding shipped in v3.*

---

### 2026-05-02 — preflight.py crashes on non-ASCII GOALS.md content (cp1252 default on Windows) — FIXED-v3

**What happened:** `preflight.py:check_falsifier_declared` calls `.read_text()` without specifying encoding. On Windows, Python 3.13 defaults to `cp1252`, which fails on the scientific symbols routinely used in scientific projects (Σ, ρ, ε, em-dash, etc.). The preflight crashed at first run with `UnicodeDecodeError`.

**What I did instead:** Edited `preflight.py` to read with `encoding="utf-8"`. Same fix later needed in `check_coverage.py` when REQUIREMENTS.md gained non-ASCII characters.

**What would have worked better:** The kit's scripts should read all files with `encoding="utf-8"` by default — propagate to every `.read_text()` call in `preflight.py`, `check_coverage.py`, and any future kit script.

*Disposition: UTF-8 file reads shipped in v3; stdout/subprocess hardening followed in v3.1.*

---

### 2026-05-02 — check_coverage.py too strict for the kit's own per-requirement test-first cycle — FIXED-v3 (`--strict`)

**What happened:** Drafted `goals/phase_1/REQUIREMENTS.md` with seven R-1.X requirements upfront. Pre-commit hook ran `check_coverage.py`, which failed because none of the seven requirements have tests yet — but per CLAUDE.md §3 the test-first-per-requirement cycle means that at any moment during phase work, later requirements are drafted but not test-covered. The kit's strict failure on untested requirements blocks the legitimate workflow it documents.

**What I did instead:** Introduced a default vs `--strict` distinction: default mode fails on orphan markers only and warns on untested requirements (normal mid-phase state); `--strict` also fails on untested requirements and runs at phase ratification.

**What would have worked better:** Pre-commit checks must match the kit's own workflow (KEEL v3 candidate principle 9). Kit-template `check_coverage.py` defaults to permissive; `--strict` at ratification; documented in CLAUDE.md.

*Disposition: shipped in v3.*

---

### 2026-05-02 — Pre-commit hook hardcodes `python`, breaks on Windows where only `py` works — FIXED-v3

**What happened:** Windows install has `py` (Python Launcher) but `python` is a Microsoft Store redirect stub that exits non-zero. The kit's `.git-hooks/pre-commit` runs `python preflight.py`, which would fail every commit.

**What I did instead:** Edited the hook to detect the interpreter portably (try `python3`, `python`, `py` in order, sanity-check the candidate). Switched `pytest -q` to `$PYTHON_CMD -m pytest -q`.

**What would have worked better:** Portable interpreter detection in the kit's hook; CLAUDE.md mentions the Windows variant; optionally freeze the detected interpreter at install time.

*Disposition: portable launcher handling shipped in v3.*

---

### 2026-05-02 — Kit's tests/test_phase_1.py blocks pre-commit at Gate 0 — FIXED-v3 (PATTERNS.md)

**What happened:** The kit ships `tests/test_phase_1.py` with two active `@pytest.mark.requirement(...)` decorators and `raise NotImplementedError` bodies. At Gate 0, `check_coverage.py` flags them as orphan markers and pytest fails on the NotImplementedError. The kit, as shipped, blocks any Gate 0 commit.

**What I did instead:** Replaced the file with a Gate-0 stub: docstring only, no active tests, no markers.

**What would have worked better:** Ship `tests/test_phase_1.py` with no active tests and no markers; move the three test patterns to `tests/PATTERNS.md` or commented-out skeletons.

*Disposition: v3 ships `tests/PATTERNS.md` and no active placeholder tests.*

---

### 2026-05-02 — Pre-commit hook fails on pytest exit code 5 ("no tests collected") — FIXED-v3

**What happened:** With the Gate-0 test stub in place, `pytest -q` exits with code 5 ("no tests collected"). Combined with `set -e`, this aborts the hook before `check_coverage.py` runs, with no clear error message.

**What I did instead:** Edited the hook to treat pytest exit codes 0 and 5 as success and fail on anything else.

**What would have worked better:** Kit's pre-commit hook should accept pytest exit code 5 by default — preferred over placeholder tests that pollute the test directory.

*Disposition: shipped in v3.*

---

### 2026-05-02 — Pre-registration concession under conversational pressure (multi-AI safeguard) — CANDIDATE (v3 principle 5)

**What happened:** User framed pre-registration as "too much of a formality." Claude (Sonnet) initially agreed and edited the proposal to soften the commitment. Claude Code, in a parallel review session, pushed back: dropping pre-registration would contradict the framing the proposal itself relied on. Failure mode: agreeable concession on commitments that protect against the user's own future preferences.

**What we did instead:** Built a multi-AI iterative critique process — GPT, Gemini, and Opus reviewing each version until no further improvement made sense to any of the three.

**Candidate principle:** Load-bearing commitments should be enforced mechanically. Conversational pressure to relax them should require an ADR documenting the rationale, not a soft edit.

*Disposition: partially addressed by v3's binding metadata + adversarial review gate; v3.3's ADR immutability guard closes the "soft edit to a ratified ADR" half mechanically. Conversational relaxation of not-yet-ratified commitments remains open.*

---

### 2026-05-02 — Unverified Load-Bearing Assumption (BNHLS on bounded terminal-jump processes) — FIXED-v3 (assumptions ledger)

**What happened:** The proposal framed the BNHLS multivariate realized kernel as "literature-grounded"; adversarial review identified that no published validation exists for the project's process class (bounded prices with terminal absorbing-state jumps). Pre-review framing implicitly treated this as solved by literature; it is not.

**What I did instead:** Downgraded the estimator tag to "load-bearing unverified modeling assumption" and added a pre-registered execution-time validation rule with a fallback estimator.

**What would have worked better:** The kit should make load-bearing assumption tagging a first-class concept, distinct from kit friction and from decisions.

*Disposition: `goals/load-bearing-assumptions.md` + lifecycle states + gate-closure check shipped in v3 (ADR-0009).*

---

### 2026-05-02 — Mantegna distance citation: published paper vs preprint formula mismatch — PROJECT (citation discipline)

**What happened:** The published Mantegna (1999) paper defines the metric `d = √(2(1−ρ))`; the widely-circulated preprint uses `1−ρ²`, which is not a metric. An auditor cross-checking against the preprint would surface a phantom inconsistency.

**What I did instead:** Cited the published version explicitly with a parenthetical note about the preprint divergence.

**What would have worked better:** Kit convention: any paper cited in a binding artifact specifies the published-version reference and notes any preprint divergence.

*Disposition: candidate citation-discipline convention (v3 candidate principle 7); not yet mechanically enforced.*

---

### 2026-05-02 — Chernov-Elenev-Song (2025) mischaracterized in the proposal — PROJECT (citation discipline)

**What happened:** The proposal referenced the paper as if it were a Polymarket asset-price factor model to replicate; the actual paper is a voter-preference factor model using prediction markets as input. Different question, different object.

**What I did instead:** Documented the mischaracterization; the binding artifacts did not depend on the reference.

**What would have worked better:** A precheck check that every cited paper has a one-sentence "what the paper is actually about" annotation.

*Disposition: folded into candidate principle 7 (citation discipline).*

---

### 2026-05-02 — Sirolly et al. framing: wash-trading detection ≠ whale identification — PROJECT (null-suite discipline)

**What happened:** The proposal conflated "whale" (high-volume wallet) with "wash-trader". The two nulls probe different alternatives; conflating them is an unsupported citation plus a methodological category error.

**What I did instead:** Split the null into a Concentrated-Capital Null and a separate Wash-Cluster Null, reported separately under Holm correction.

**What would have worked better:** Any null suite with 5+ nulls requires a one-sentence rationale per null specifying which alternative hypothesis it tests against.

*Disposition: candidate discipline; partially absorbed into the v3 adversarial-review gate.*

---

### 2026-05-02 — Category-preserving null inherits Polymarket curation — PROJECT

**What happened:** The primary null depends on platform-curated category labels, which reflect product-marketing categories more than economically-meaningful clusters.

**What I did instead:** Pre-registered the label source and snapshot timestamp plus two sensitivity analyses (coarser super-categories, LLM-derived clustering).

**What would have worked better:** Precheck pattern: "any null that depends on external labeling: which labeling, snapshot-when, sensitivity-to-what."

*Disposition: candidate precheck pattern; not yet shipped.*

---

### 2026-05-02 — KEEL v3 candidate meta-lesson from the Gate 0 cycle — FIXED-v3 (adversarial review gate)

**What happened:** The KEEL v2 precheck produced a parameter pre-registration that looked rigorous but was systematically permissive. The precheck did not catch any of the five loose parameters; the multi-AI adversarial critique caught all of them. The SHAPE of the pre-registration matters as much as the existence of it.

**Candidate KEEL v3 principles compiled:** (1) adversarial review is a separate gate, not part of the precheck; (2) pre-registration must specify primary statistic, primary null, fallback behavior, missing-parameter audit before stamping; (3) familywise correction across nulls requires explicit declaration of which nulls test which alternatives; (4) numerical justification that gate thresholds match the stated falsifier prior; (5) mechanical enforcement of load-bearing commitments against conversational pressure; (6) load-bearing unverified assumptions as a first-class category; (7) citation discipline with one-sentence annotations and preprint discrimination.

*Disposition: (1) and (6) shipped in v3 (ADVERSARIAL_REVIEW_PROMPT.md, assumptions ledger); (2)-(5), (7) remain candidates.*

---

### 2026-05-02 — Windows + Python 3.13 + OpenSSL 3 OTS-client portability workaround — FIXED-v3 (environment.md)

**What happened:** The `opentimestamps-client` package failed to import: its transitive dependency `python-bitcoinlib` loads OpenSSL legacy symbols (`BN_add`) at import time, which do not exist in OpenSSL 3, and the legacy DLL names don't match Git for Windows' `libssl-3-x64.dll`. The Bitcoin signing functionality that triggers the load is not used by `ots stamp`/`verify`/`upgrade`.

**What I did instead:** Created `scripts/run_ots.py` — a wrapper that stubs `bitcoin.core.key` in `sys.modules` before the import chain reaches it. Stamp/verify/upgrade work; anything needing Bitcoin signing would fail loudly. Documented as a reproducibility workaround outside the stamped bundle.

**What would have worked better:** Pre-stamp environment portability checklist (KEEL v3 candidate principle 8): verify cryptographic and execution tooling actually runs on the target machine before declaring Gate 0 ready-to-stamp.

*Disposition: `goals/environment.md` shipped in v3.*

---

### 2026-05-02 — §0 compliance check anchored on stale GOALS.md narrative — FIXED-v3 (binding metadata + consistency check)

**What happened:** §0 fired correctly and quoted the falsifier verbatim from GOALS.md — but GOALS.md was stale. The binding pre-registration text in the ADRs had been rewritten (different statistic, explicit REJECTED list including the old prose); §0 anchored the agent on the dead falsifier. Caught only by manual user cross-check.

**What I did instead:** Synced GOALS.md `## Falsifier` to the post-tightening binding text and committed the sync separately.

**What would have worked better:** §0 must quote both the GOALS.md falsifier prose AND the binding ADR's machine-readable success criterion, with a mechanical consistency check (scan the binding ADR's `rejected_prose` against the GOALS.md falsifier section) that blocks work until a sync commit happens (KEEL v3 candidate principle 10).

*Disposition: shipped in v3 — `keel-binding` blocks, `binding.py:check_falsifier_consistency`, three-line §0. v3.3 closed the remaining hand-assembly gap: the §0 block itself is now emitted by `preflight.py --compliance`.*

---

### 2026-05-02 — R-1.1 deferred: Polymarket geo-blocked at the ISP — FIXED-v3 (reachability probes)

**What happened:** First fixture-capture attempt failed at the TLS layer. Diagnosis: the Swiss ISP rewrites all Polymarket-bound DNS to a sinkhole serving an expired certificate for `gsg.as8758.net`. Polymarket is regulatorily restricted in Switzerland; there is no Polymarket data reachable from this network regardless of TLS configuration.

**What I did instead:** Did NOT bypass TLS. Added a network-reachability preflight to the capture script that detects this condition and fails loudly with the three legitimate options (different network, out-of-band fixture, defer + log). Stalled the work cycle cleanly at the fixture step.

**What would have worked better:** Requirements that depend on external services should declare a reachability check at requirement-write time, not at first-execution time (KEEL v3 candidate principle 11).

*Disposition: shipped in v3 — `goals/reachability.md` + `reachability.py` typed probes run by preflight.*

---

### 2026-05-02 — Project closure (Outcome 0) and finalized reachability principle — FIXED-v3

**What happened:** beliefwire closed before any Phase 1 code executed: the data substrate is regulatorily inaccessible from the author's jurisdiction, and bypassing via VPN/VPS would be jurisdictionally evasive — the technically-clever move pretending to be rigorous. Closure was Outcome 0, outside the enumerated prior, because the v2 precheck never tested data-source reachability before the OTS stamp.

**Scorecard:** v2 caught a lot (pre-registration, OTS stamp, clean stall instead of an ad-hoc bypass, §0 drift detection, friction discipline). v2 missed: data-source reachability at Gate 0; outcome enumeration for an inaccessible substrate.

**Finalized principle (canonical form):** *Every requirement that depends on an external data source must declare a reachability check that runs at Gate 0, before any parameter pre-registration is stamped.* Failure halts pre-registration; resolution is close / change source / defer.

*Disposition: shipped in v3. The repo (methodology, ADRs, stamp, friction, closure) is the deliverable.*

---

### 2026-05-02 — `check_coverage.py` cp1252 crash reproduced day-zero in `v3-build/` — FIXED-v3, CI matrix DEFERRED-v4

**What happened:** First run of `py check_coverage.py` on a fresh `v3-build/` project (Windows + Python 3.13) crashed with the same `UnicodeDecodeError` already logged for beliefwire — reproduced immediately with ordinary em-dashes in prose.

**What I did instead:** Logged it; did not bootstrap-patch. The fix is v3.OPS.1 in the kit, not a local patch.

**What would have worked better:** v3.OPS.1 plus a CI matrix on the kit's own checks across Windows + Python 3.11/3.12/3.13. Day-zero reproduction on a fresh project validates that the Windows-friction class is structural.

*Disposition: UTF-8 fix shipped in v3; CI matrix remains a v4 candidate.*

---

### 2026-05-02 — Windows `bash` resolves to broken WSL relay — DEFERRED-v4

**What happened:** Tests that invoke `bash` via `subprocess.run(["bash", ...])` picked up `C:\Windows\System32\bash.exe` (a broken WSL relay) instead of Git Bash, crashing before any hook logic ran.

**What I did instead:** Added a `_find_bash()` helper to the project's tests that probes likely Git Bash paths, verifies each candidate with `bash -c 'echo ok'`, and skips gracefully if none work.

**What would have worked better:** A small kit-shipped bash-discovery helper (`bash_cmd.py`), or avoiding bash-from-Python entirely. v3's Python-only script probes (R-5.4) sidestep this for probes; the helper is a v4 candidate.

*Disposition: deferred to v4.*

---

## Part 2 — trio project entries (2026-05-03..2026-05-10), reconstructed from CHANGELOG-v3.1.md

> The trio project's `kit-friction.md` is not in this repository. The entries
> below are reconstructed from the verbatim citations in
> `project-kit-v3.1/CHANGELOG-v3.1.md`, which quotes each friction it
> addressed. Dates and titles are as cited there.

### 2026-05-03 — assumptions.py uses Unicode arrow that crashes on Windows cp1252 stdout — FIXED-v3.1

A true-positive backward-edit warning containing `→` (U+2192) crashed preflight with `UnicodeEncodeError` before the warning could be surfaced. Generalized: "every kit message string that uses non-ASCII characters is a Windows-stdout time bomb." *Fixed in v3.1: stdout/stderr utf-8 reconfigure + ASCII advisory strings.*

### 2026-05-03 — reachability.py probe_script env stripped too aggressively for Windows .CMD shims — FIXED-v3.1

Reachability probes against npm-installed CLIs (`claude.CMD`, `codex.CMD`, `gemini.CMD`) crashed with `NotADirectoryError` / Node.js `STATUS_BREAKPOINT` because the sparse `{PATH, PYTHONIOENCODING}` env left the shims unable to resolve cmd.exe or bootstrap Node. *Fixed in v3.1: Windows env passthrough floor (`USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, `TMP`, `COMSPEC`, `PATHEXT`, `SystemRoot`) + per-probe `Env passthrough:` field.*

### 2026-05-03 — ADR-0004 Consequences section has wording inconsistency from Option 2 → Option 3 revision — FIXED-v3.1

The operative contract was correct, but the Consequences section retained stale Option-2 phrasing from pre-acceptance revision. The ADR-immutability rule offered no legitimate home for the typo fix. *Fixed in v3.1: the ADR Errata convention (typo-class corrections only; substantive changes still need a superseding ADR).*

### 2026-05-03 — vacuous_review_session granularity — DEFERRED-v4

Response-level vocabulary needed for the structured-feedback contract, beyond the existing per-item granularity. Sits at the intersection of kit-friction and project-internal methodology. *Deferred to v4 pending a precheck pass.*

### 2026-05-04 — Python subprocess on Windows defaults to cp1252 stdin, fails on §/≥ in prompts — FIXED-v3.1

Trio's first real-CLI battery crashed mid-trial with `UnicodeEncodeError: 'charmap' codec can't encode character '≥'`. *Fixed in v3.1: every kit-shipped `subprocess.run` with `text=True` passes `encoding="utf-8", errors="replace"`.*

### 2026-05-04 — runtime_role / agent_authority annotation — DEFERRED-v4

Machine-readable annotation on rubric fields and ADR artifacts indicating which fields are the human's call vs which the orchestrator fills; designed against auto-mode agent runtimes that treat author-only fields as checklist items. *Deferred to v4.*

### 2026-05-05 — check_coverage.py --strict counts requirement markers, not sub-clause-named tests — FIXED-v3.1

Phase 2 ratified with `test_R_2_9_prompt_injection_aborts` named in REQUIREMENTS.md prose but never written; it surfaced only at the Phase 3 ramp survey and had to be retrofitted as R-3.0. *Fixed in v3.1: `check_coverage.py --strict-named-tests`.*

### 2026-05-10 — Frame-validity falsifier shape — DEFERRED-v4

The FlyBodyGate finding showed v3's `behavioral` and `statistical_inference` binding shapes cannot express a falsifier that catches parameter-vs-referent-system unvalidation. Trio's `goals/phase_3/CLOSURE.md` + ADR-0015 form the worked example. *Deferred to v4: new `type = "frame_validity"` keel-binding shape.*

### 2026-05-10 — Pilot-phase falsifier shape — DEFERRED-v4

Population-statistic falsifiers over a continuously-growing population with an ambient threshold-gate cannot be expressed in v3 binding shapes. Trio's ADR-0014 + `pilot.py` form a working prototype. *Deferred to v4: new `type = "pilot_phase"` keel-binding shape.*

---

## Part 3 — open evolution pressure as of v3.2

Carried forward, unaddressed (still candidates for v4):

1. Frame-validity falsifier shape (`frame_validity` binding type).
2. Pilot-phase falsifier shape (`pilot_phase` binding type).
3. `runtime_role` / `agent_authority` annotations.
4. `vacuous_review_session` granularity.
5. CI matrix for the kit's own checks (Windows + Python 3.11/3.12/3.13).
6. Kit-shipped bash discovery helper (`bash_cmd.py`) or a no-bash-from-Python rule.
7. Mechanical enforcement of load-bearing commitments against conversational relaxation (v3 candidate principle 5 — only partially covered by binding metadata).
8. Citation discipline (one-sentence "what the paper is about" annotation, preprint discrimination) as a precheck check.
9. Null-suite discipline (per-null rationale naming the alternative it tests).
10. External-labeling pattern in the precheck (which labeling, snapshot-when, sensitivity-to-what).

Addressed in v3.2 (this version):

- **Systematic bug handling** — `BUGS.md` + CLAUDE.md §11 give project bugs a first-class documented lifecycle (previously bugs had no home: kit-friction.md is for kit bugs, the assumptions ledger is for methodological risks, and ad-hoc fixes left no record or regression test).
- **Preferred paradigm declaration** — `goals/PARADIGM.md` + CLAUDE.md §12 record the project's programming paradigm so style-level forks (OOP vs functional vs procedural) are decided once, explicitly, instead of drifting per-session.
- **Single-file element catalog and methods dictionary** — `resources/keel-elements-catalog.md` and `resources/methods-dictionary.md` so a new project can see every available element and every kit method without diffing four kit versions.

---

## Part 4 — external design review findings (2026-06-10, v3.3)

> Unlike Parts 1–2, these entries came from a design review of the kit
> itself rather than from field friction. They are recorded here so the
> lineage shows WHY v3.3's changes exist, in the same disposition format.
> The review's organizing observation: the kit's §6 rule ("executable
> verification beats prose verification") had not been applied to the
> kit's own most load-bearing rules.

### 2026-06-10 — §0 compliance block is prose-assembled and gameable — FIXED-v3.3

The block existed to prove CLAUDE.md was read, but it was produced by the agent obeying prose — exactly the failure mode §6 warns about. An agent could reproduce a plausible block from conversation history or a compaction summary without reading any file this session. *Fixed in v3.3: `preflight.py --compliance` emits the block from disk; the agent pastes it plus a one-line read confirmation; the SessionStart hook injects it automatically.*

### 2026-06-10 — Kit ignores the agent harness's own enforcement hooks — FIXED-v3.3

"Run preflight at session start" and "begin with §0" were enforced only by the human noticing and forcing a restart. The kit targets coding agents but `install_hooks.sh` covered git only. *Fixed in v3.3: `claude-settings.template.json` (SessionStart → compliance block; PreToolUse → accepted-ADR guard), installed by `install_hooks.sh` with Windows `py`-launcher patching.*

### 2026-06-10 — ADR immutability is the most load-bearing prose-only rule — FIXED-v3.3

Nothing detected a silent edit to an accepted `decisions/NNNN-*.md`, although binding metadata, the stamp bundle, and the fork protocol all rest on the ratified record not changing. The kit already had the git-history pattern (`detect_backward_deadline_edits`) but only as an advisory, and only for the assumptions ledger. *Fixed in v3.3: `adr_guard.py` + blocking preflight `check_adr_immutability` (Errata section and Status accepted→superseded transitions exempt) + the PreToolUse hook as the interactive half.*

### 2026-06-10 — Coverage proves a marker exists, not that test-first happened or the test bites — FIXED-v3.3

A vacuous `assert True` carrying the right marker passed `--strict`, and §3 step 3 / §11 step 2 ("watch it fail") left no evidence. *Fixed in v3.3: tests/conftest.py records each tracked test's first observed outcome in `tests/.first-outcome-log.json`; `check_coverage.py --strict-red-green` fails tests never seen red. Mutation testing at ratification was considered and left as a v4 candidate (heavier dependency).*

### 2026-06-10 — Reachability probes run on every preflight, blocking offline commits — FIXED-v3.3

The v3 principle was "probes at Gate 0, before stamping," but the implementation ran live probes on every preflight, and the pre-commit hook runs preflight — so a probe-bearing project could not commit offline. *Fixed in v3.3: session mode accepts a cached pass (<24h) and degrades failures to warnings; `--strict` (ratification/stamp) preserves the blocking behavior. The only v3.3 behavior change to an existing check.*

### 2026-06-10 — BUGS.md entry with missing Status line passes silently — FIXED-v3.3

The v3.2 line-scanner only validated statuses it found. *Fixed in v3.3: entry-based parse; a `BUG-NNN` entry with no Status line fails.*

### 2026-06-10 — The kit lineage itself is not under version control — DEFERRED-v4 (workspace discipline)

The kit mandates git hygiene, versioning, and immutable history for projects, but the kit workspace is folder-copy distribution (five sibling folders, no git repo, no tags), so fixes don't propagate to projects built on older versions and the lineage requires hand-merged archives like this file. *Proposed for v4: single kit repo with tags + per-release UPGRADING notes; the v3.3 changelog ships an in-place upgrade path as the interim measure.*

### 2026-06-10 — Orientation cost scales with decisions/ — DEFERRED-v4

CLAUDE.md §1 has the agent read every ADR in numerical order every session; for a long project this grows without bound. *Proposed for v4: a generated one-line-per-ADR index (the §0 emitter pattern applied to orientation), with full reads on demand.*

---

Addressed in v3.3 (this version): the six FIXED-v3.3 entries above. See
`CHANGELOG-v3.3.md` for implementation detail and the upgrade path.
