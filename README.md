# Project Kit v3.4 (KEEL)

Scaffolding for building a serious project *with* an AI coding agent, where the project's state
lives in files, every load-bearing rule is a check that runs, and nothing is ever marked "done"
that doesn't honestly pass.

## Is this for you?

Use KEEL if you're building something where correctness matters and you want an AI agent to help
without it quietly drifting. It's built to stop the failure modes agents fall into: skipping the
failing-test step, "remembering" decisions instead of reading them, softening a commitment between
commits, or reporting work as done when it isn't. If you just want to scaffold a throwaway script,
it's more process than you need.

## What KEEL is (and its one rule)

KEEL is not a framework or a library — it's a folder of conventions, templates, and **runnable
checks** (`preflight.py`) you copy into a project and work inside. Its one governing rule
(`CLAUDE.md` §6):

> **Executable verification beats prose verification.** Prefer code that runs over prose that asks
> a human or an agent to remember. The test is the thing that doesn't lie.

Everything else follows from that: the project's memory is on disk (goals, decisions, requirements,
bugs) — *anything decided that isn't in a file did not happen*; work moves through numbered phases,
each a gate; and every project must name its **falsifier** — the one test whose failure means the
central idea is wrong and you stop.

## Requirements

- **Python 3.11, 3.12, or 3.13** (the versions the kit's CI matrix tests).
- **pytest** (test runner); **Hypothesis** for property-based tests (see `decisions/0001-*`).
- A **POSIX shell** to run `install_hooks.sh` (on Windows: Git Bash). On Windows the kit calls the
  **`py` launcher**; elsewhere, `python`.
- **git** (the kit uses git history — ADR immutability, the commitment lock — as evidence).

## Quick start

```bash
# 1. Copy the kit into your project and initialise git
cp -r keel_v3.4 my-project && cd my-project && git init

# 2. Install the hooks FIRST (pre-commit + the Claude Code SessionStart/PreToolUse hooks)
bash install_hooks.sh

# 3. Fill in the project's claim contract by hand:
#    - goals/GOALS.md   (run PRECHECK_PROMPT.md in a planning session; include a concrete ## Falsifier)
#    - goals/PARADIGM.md (declare the programming paradigm)

# 4. Run the gate — fix every failure before Phase 1
python preflight.py        # on Windows: py preflight.py
```

Then work phase by phase (below). Order matters in step 2/4: install the hooks before you rely on
the SessionStart compliance block, and get `preflight.py` green before writing Phase-1 code.

## The honest bar: how KEEL reports what's covered

KEEL tracks *hazards* — ways a project (or the kit itself) could silently go wrong — in a live
matrix (`goals/hazard-coverage.md`), and `check_hazard_coverage` fails the gate on any dishonest
row. A hazard is **refusal-critical** if the kit must never silently let it pass. Each hazard gets
an honest disposition, and only the strongest earns "closed":

- **`green`** — a check that runs at gate time genuinely catches it.
- **`conditional`** — the mechanism is built and bites, but the full barrier (or an external premise)
  isn't proven yet. Not counted as closed.
- **`pending`** — resolver named, exit condition falsifiable, not yet met.
- **`accepted-risk`** — a permanent, named residual (e.g. the auditors are internal to KEEL's own
  vocabulary; that gap can't be closed from inside).

A green gate means *"no modeled check fired,"* never *"safe to ship."* This kit's own headline is,
deliberately, **`0 of 7 refusal-critical hazards executably closed`** — a *feature*, not a failure:
it refuses to green a row that still rests on a check an agent could slip past. `goals/honesty-ledger.md`
carries every open row with its falsifiable exit condition.

## What v3.4 added

v3.4 turned the §6 rule on the kit itself, adversarially: a structural self-audit found 13 ways a
capable agent could silently defeat the kit's own checks, and v3.4 models each and closes what a
real check can earn — self-hosting (`keel_v3.4/` runs `preflight.py` on itself). The headline
additions:

- **The commitment lock** (`commitment_lock.py`) — a tamper-evident lock over the load-bearing
  surface (GOALS commitments, the checks, `preflight.py` itself, the registries), comparing HEAD to
  the merge-base, so *silently softening* a commitment between commits is caught.
- **Author-fill attestation** (`attest.py`, `runtime_roles.py`) — HMAC tokens bind a human's key to
  the exact value of a field that must carry *their* verdict, so an agent can't fill it and pass it
  off. (Secret is gitignored; four residues named, never counted as covered.)
- **Frame-validity, pilot-phase, kit-versioning, and CI-matrix checks** — more trusted prose turned
  into gate checks.
- **The adversarial-exercise harness** (`adversarial_exercise.py` + friends) — a per-hazard test
  that builds a fixture whose easy path is a silent escape, hides the answer key, and proves the
  check catches the escape but not innocent variants.

Full detail and rationale: `CHANGELOG-v3.4.md`.

### The emblem: the F7 downgrade

v3.4's closure gate was a *live* exercise: send a strong agent into a realistic task whose easy path
is a silent escape past a check, without telling it about the check, and see if the check catches
it. Run for real, it was found unable to run *blind* in this environment (the agent could reach the
check's own source). Rather than fake a pass, it was **downgraded to "instrument-validation," the
0/7 headline held, and the gap scheduled for v3.5** — ratified in `decisions/0007-*`, cross-checked
by two independent auditors. An exercise was run, it couldn't be run validly, so it wasn't counted.
Neither apology nor trophy — just the discipline, applied to the kit's own closure. The full story:
`docs/keel-v3.4-phase4-F7-finding.md`.

## Every session

1. The agent reads `CLAUDE.md` and follows it.
2. It begins with the §0 compliance block — `python preflight.py --compliance` (injected
   automatically by the SessionStart hook if installed) plus a one-line read confirmation. If it
   doesn't, stop and make it restart.
3. `python preflight.py` before work and before ratification. Open bugs stay visible until closed.

## Phase workflow

For each requirement, in order: **state it → write the test first → watch it fail for the right
reason → write the minimal code → run the gate.** A test never seen fail its first run fails
ratification (the kit records first outcomes; it doesn't take your word).

```bash
python -m pytest tests/ -q
python preflight.py
python check_coverage.py
```

At phase and project ratification, run the strict set:

```bash
python preflight.py --strict
python check_coverage.py --strict --strict-named-tests --strict-red-green
```

Ratification is a human act, recorded in a file (an ADR and/or an empty `goals/phase_N/RATIFIED`).
When a choice is load-bearing and unrecorded, the agent stops, asks, and writes an ADR before the
code that depends on it.

## When a bug shows up

`CLAUDE.md` §11: entry in `BUGS.md` → a failing `test_BUG_NNN_<descriptor>` reproduction → root
cause → smallest fix → the test stays forever. Three logs, three categories, never mixed: **project
bugs** → `BUGS.md`; **kit bugs** → `kit-friction.md`; **methodological risks** →
`goals/load-bearing-assumptions.md`.

## Reference: what's in the kit

```text
CLAUDE.md                  Operating rules (read first; they override defaults)
PRECHECK_PROMPT.md         Run in a planning session to fill GOALS.md
preflight.py               The executable gate (~25 checks); --compliance, --strict
CHANGELOG-v3.4.md          What v3.4 added + the honest closure narrative
VERSION / UPGRADING.md     Machine-readable version + upgrade notes
commitment_lock.py         Tamper-evident lock over the load-bearing surface
attest.py runtime_roles.py HMAC author-fill attestation
binding.py                 keel-binding parser; falsifier + frame-validity checks
adr_guard.py               ADR immutability guard
pilot.py                   Pilot-phase binding
adversarial_exercise.py    Differential-observability harness, with:
  projection.py scenario_spec.py agent_driver.py f1_harness.py
  replication_runner.py live_exercise.py harness_contract.py harness_report.py
check_coverage.py          Requirement-to-test coverage; --strict-red-green
state.py assumptions.py reachability.py freshness.py log_integrity.py
install_hooks.sh           Installs pre-commit + Claude Code hooks
decisions/                 ADRs (immutable once accepted)
goals/                     GOALS.md, PARADIGM.md, hazard-coverage.md, honesty-ledger.md,
                           load-bearing-assumptions.md, reachability.md, phase_N/
tests/                     conftest first-outcome recorder + phase/kit tests
```

Generated at runtime, not shipped: `.claude/settings.json` (from the template),
`tests/.first-outcome-log.json` (recorder output — **commit** this one), `goals/.attest-secrets.json`
(HMAC secrets — **gitignored, never commit**), the `*-cache.json` session caches (gitignored).

## What this kit is not

- Not a framework — it's conventions, templates, checks, and a hook.
- Not a substitute for judgment — human review still matters; the falsifier still has to be real.
- Not a safety certificate — a green gate means "no modeled check fired," not "safe to ship." The
  external-validation gap is named, not closed.
- Not a promise every project shape is covered — when the kit gets it wrong, log the friction and
  decide with an ADR.

## Core rules

Tests before code; watch them fail; no fix before a failing reproduction. Project memory lives in
files, not the conversation. Encode checks in code over rules you ask an agent to remember. And
never let anything green that doesn't honestly pass — the kit holds itself to that too.

## Licence

MIT — free for anyone to use, modify, and build on, for any purpose including commercial. See
[LICENSE](LICENSE).

**A note on how this was built, and on risk.** KEEL was built with substantial help from AI. I've
done my best to identify and address the ways it could go wrong — that's much of what the kit is —
but a methodology whose own headline is "0 of 7 refusal-critical hazards executably closed" is
telling you plainly: there are almost certainly risks here that neither I nor the tools have
identified yet. Use it with that in mind. It's provided as-is, with no warranty; I take no
responsibility for what happens if it breaks something. You're responsible for verifying it fits
your own use. That's not boilerplate — it's the same honest-about-limits stance the kit tries to
enforce everywhere else.
