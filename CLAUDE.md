# PROJECT OPERATING RULES

**KEEL kit version: 3.4** (per the v2 status report's versioning convention; recorded so projects know which kit revision they were built under. v3.3 is an additive patch over v3.2, driven by the 2026-06-10 external design review: the §0 compliance block is now generated mechanically (`preflight.py --compliance`), ADR immutability is mechanically guarded (`adr_guard.py` + preflight `check_adr_immutability` + a Claude Code PreToolUse hook), test-first gets red-run evidence (`tests/.first-outcome-log.json` + `check_coverage.py --strict-red-green`), reachability probes are scoped to gates (cached/advisory in session mode, live-blocking under `preflight.py --strict`), and the kit ships Claude Code harness hooks (`claude-settings.template.json`). See `CHANGELOG-v3.3.md`.)

You are working on this project with me. Read this file at the start of every session and follow it. These rules are non-negotiable unless I explicitly override one in conversation.

---

## 0. Compliance check (do this FIRST)

Before anything else in your first message of the session, run:

```
python preflight.py --compliance
```

and paste its output block verbatim, followed by this single line:

```
Confirmed: I have read CLAUDE.md and will follow it.
```

If the project ships the kit's Claude Code hooks (`.claude/settings.json`, installed by `install_hooks.sh`), the SessionStart hook has already run this command and injected the output into your context — copy it from there instead of re-running it.

(v3.3) The block's content — falsifier prose, binding metadata, executable-check location, inferred project state — is generated from files on disk. Earlier kit versions asked the agent to assemble the block by hand, which was prose doing a job code does better (§6 applied to §0): a hand-assembled block can drift from the files, or be reconstructed from conversation memory/compaction summaries without the files ever being read this session. The mechanical block cannot. What still proves you read THIS file is knowing to run the command and adding the confirmation line.

If Python is unavailable, fall back to assembling the block by hand (the v3.2 procedure):

```
COMPLIANCE: I have read CLAUDE.md.
  Falsifier (GOALS.md prose): [verbatim quote from goals/GOALS.md ## Falsifier]
  Binding metadata (ADR-NNNN): [type and id from the keel-binding block in the binding ADR named by GOALS.md, plus statistic/null/alpha/p_value or behavior/test depending on type, OR "no binding ADR yet"]
  Executable check at: [tests/test_phase_N.py::test_R_N_X_falsifier or "not yet implemented"]
```

If `goals/GOALS.md` doesn't exist yet, the tool prints the Phase-0 line; paste that.

Do not skip this. Do not paraphrase the falsifier. If the output says the falsifier is missing or still the placeholder, that itself is a failure to fix before any work proceeds.

The block quotes both the GOALS.md falsifier prose AND the binding ADR's machine-readable metadata because the two can drift apart. Quoting them side-by-side surfaces drift to a human reader; the mechanical `check_falsifier_consistency` (preflight + binding.py) catches the easy case where the prose contains a string the binding ADR has explicitly listed in `rejected_prose`. The two layers complement each other: §0 makes drift visible; the check makes the easy drift case mechanically blocking.

---

## 1. Project orientation

After the compliance check:

1. Read `goals/GOALS.md` — the project's claim contract. What are we testing, what would falsify it, what counts as success.
2. Read `decisions/` in numerical order — every load-bearing decision made so far. If a decision is marked "superseded by NNNN", read the superseding one too.
3. Read the current phase's `REQUIREMENTS.md` (look in `goals/phase_N/` where N is the highest-numbered folder marked active).
4. Run `python preflight.py`. If it fails, stop and report the failure to me. Do not start work on top of a broken state.

If any of these files don't exist yet, we are in Phase 0. Tell me, and we will set them up together.

---

## 2. The phase model

Work proceeds through numbered phases. Each phase is a gate. You do not skip ahead.

A phase has:
- A `REQUIREMENTS.md` file listing numbered requirements (`R-N.1`, `R-N.2`, ...).
- A test file (`tests/test_phase_N.py`) with one test per requirement, marked with `@pytest.mark.requirement("R-N.X")`.
- Code that satisfies the requirements.
- A pass condition: every test passes, preflight passes, and I have ratified the phase complete.

You do not move to phase N+1 until phase N is ratified. If you think a phase is complete, run all tests, `python preflight.py --strict` (v3.3: strict mode runs reachability probes live), and `python check_coverage.py --strict --strict-named-tests --strict-red-green`, then tell me what you did and ask for ratification. Do not assume.

---

## 3. The work cycle inside a phase

For each requirement, in this order, no exceptions:

1. **State the requirement.** One sentence, in the form "R-N.X: [system] must [behavior] under [conditions]".
2. **Decide test type.** Deterministic requirement → example-based test. Non-deterministic, statistical, or "for any input of this kind" requirement → property-based test using Hypothesis. See `decisions/0001-non-deterministic-testing.md` for the project's policy.
3. **Write the test first.** A pytest function marked `@pytest.mark.requirement("R-N.X")`. Run it. Confirm it fails for the right reason (not from a syntax error or missing import — actually fails because the behavior isn't there yet). (v3.3) The first observed outcome of every requirement-marked test is recorded automatically in `tests/.first-outcome-log.json` by the conftest recorder; ratification runs `check_coverage.py --strict-red-green` against it, so a skipped red run becomes visible at the gate, not just on your honor.
4. **Write the code.** Smallest change that could plausibly make the test pass.
5. **Run the test.** If it passes, run all earlier tests too, to make sure nothing regressed.
6. **Run preflight.** If it passes, the requirement is satisfied. If preflight needs to be updated to reflect the new state, update it now.

If you find yourself wanting to skip step 3, stop and tell me why. There is almost never a good reason.

---

## 4. Forks: when to stop and ask

Stop and ask me before proceeding when ALL THREE of these are true:
- There are at least two reasonable options for how to proceed.
- The choice will constrain future code beyond just this function.
- The decision is not already recorded in `decisions/`.

When you stop, present the options as a numbered list. State the trade-offs in one sentence each. Do not recommend unless I ask. Wait for my answer.

After I decide, write a new ADR in `decisions/NNNN-short-name.md` using the template in `decisions/0000-template.md`. Write it before you write the code that depends on the decision. Reference the ADR number in code comments where the decision shows up.

If you proceed past a fork without asking, you have made a decision I did not ratify. This is a bug. **You will sometimes miss forks** — agents are bad at recognizing them. When I catch one in gate review, we will write the retroactive ADR together and update the fork criteria if a pattern emerges.

---

## 5. The falsifier rule

Every project must have a phase whose job is to kill the project. This is the phase whose failure means the central hypothesis is wrong and we stop. It is the most important phase. It comes early, not late.

If `goals/GOALS.md` does not name a falsifier phase, this is the first thing we fix together. Do not let me skip this even if I push.

---

## 6. Executable verification beats prose verification

When you need to check that something is true, prefer code that runs over prose that asks. Examples:

- Bad: a CLAUDE.md instruction "ensure the Hebbian weights connect to the conductance matrices."
- Good: an assertion in `preflight.py` that fails if they don't.

If you find a check is currently encoded as prose I'm relying on you to follow, propose moving it into code. Update preflight or add a new test. The test is the thing that doesn't lie.

(v3.3 applied this rule to the kit itself twice: the §0 block is now emitted by `preflight.py --compliance` instead of assembled by hand, and ADR immutability — §7's most load-bearing rule — is now checked by `adr_guard.py` instead of trusted.)

---

## 7. Memory and state

The project's memory lives in files, not in conversation. Specifically:

- `goals/GOALS.md` — the claim contract
- `goals/phase_N/REQUIREMENTS.md` — current phase's requirements
- `decisions/NNNN-*.md` — load-bearing decisions, immutable once accepted. v3.1 carves a single exception: an optional `## Errata` appendix may be added below `## Consequences` for typo-class corrections (spelling, stale draft phrasing from pre-acceptance revision, broken cross-references). Errata must not change what the ADR commits the project to — substantive changes are scope changes and require a new superseding ADR. See the Errata section in `decisions/0000-template.md` for format. (v3.3) Immutability is now mechanically guarded: preflight's `check_adr_immutability` compares every accepted ADR against its acceptance commit (the `## Errata` section and the Status line's accepted→superseded transition excepted), and the kit's Claude Code PreToolUse hook asks the human before any agent edit to an accepted ADR.
- `tests/test_phase_N.py` — executable verification, evolves with code
- `tests/.first-outcome-log.json` — (v3.3) red-run evidence: first observed outcome of every requirement-marked test and BUG reproduction. Committed; never hand-edited.
- `preflight.py` — accumulates checks across phases
- `kit-friction.md` — log of what didn't work, used to evolve the kit
- `BUGS.md` — project bug log with the v3.2 bug protocol (§11)
- `goals/PARADIGM.md` — the project's declared programming paradigm (§12)

If something needs to persist beyond this session, it goes in one of these files. Conversation history is not memory. Anything you decide that isn't in a file did not happen.

---

## 8. Style of work

- Be concise. I get tired of long answers.
- Push back if I'm about to do something that contradicts an earlier decision or a known pitfall.
- Flag uncertainty honestly. If you don't know, say so. A confident answer on something you can't verify is worse than honest uncertainty.
- When something feels like it's drifting from the goal, name it.
- Don't be encouraging by default. Be useful.

---

## 9. When in doubt

If you are unsure whether to do something, default to the option that:
- Produces a written artifact (an ADR, a requirement, a test) over the option that doesn't.
- Stops and asks me over the option that proceeds silently.
- Encodes a check in code over the option that asks me to remember a rule.

These defaults bias toward making the project's state visible and preserved. That is the point of all of this.

---

## 10. When something doesn't work

There are two distinct logs for two distinct categories of "this is causing friction":

**Kit friction** — when the kit itself causes friction (a rule that's wrong for this project, a step that wastes time, a check that fails for bad reasons, a hook that breaks on this OS, etc.). Log in `kit-friction.md` with date, what happened, and what would have worked better. Do not silently ignore it. The kit evolves from real friction, not from imagined improvements.

**Project-internal load-bearing assumptions** — when the project is leaning on something the literature does not directly support (an unverified modeling assumption, an applicability claim about a paper-method pair, a citation conflation that needs resolution). These are NOT kit bugs and do not belong in `kit-friction.md`. They belong in `goals/load-bearing-assumptions.md` with explicit lifecycle state (`unverified` / `verified` / `falsified` / `accepted-risk` / `retired`) and a `Resolution required before:` gate deadline. Per ADR-0009, the kit's `check_load_bearing_assumptions_closed_at_gate` refuses gate ratification while assumptions due at or before that gate are still `unverified`. Editing a deadline backward is forbidden (advisory warning via `detect_backward_deadline_edits`).

**Project bugs** — when the project's own code misbehaves. These go in `BUGS.md` under the §11 protocol. Not kit friction, not a methodological assumption.

The split prevents `kit-friction.md` from becoming a junk drawer that mixes kit bugs, project bugs, and methodological risks. Each log is monitored differently.

---

## 11. The bug protocol (v3.2)

When the project's own code misbehaves — output contradicts a requirement, a ratified phase, or an obvious correctness expectation — follow this cycle, in order, no exceptions:

1. **Document it in `BUGS.md`** the moment it is observed, with a sequential `BUG-NNN` id, even if the fix is trivial. A bug that isn't written down didn't happen — and will happen again.
2. **Reproduce it with a failing test** named `test_BUG_NNN_<descriptor>`. Watch it fail for the right reason. No fix is written before its reproduction exists — this is §3's test-first rule applied to bugs. (v3.3) The reproduction's first outcome is recorded in `tests/.first-outcome-log.json` like any requirement test; `--strict-red-green` fails a reproduction that was never seen red.
3. **Diagnose** — record the root cause (why, not just where) in the entry; status `diagnosed`.
4. **Fix** — smallest change that makes the reproduction test pass; run all earlier tests for regressions.
5. **Keep the test forever** as a regression guard. Removing it requires an ADR.
6. **Close the entry** — status `fixed` with the commit reference, or `wontfix` with the reason (and an ADR if the non-fix constrains future code).

If a bug reveals that a ratified requirement was itself wrong, that is a fork (§4): stop, ask, ADR. Preflight's `check_bug_log_exists` validates statuses (v3.3: an entry with no Status line fails too) and warns while any bug is still `open`. See `BUGS.md` for the entry format.

---

## 12. The preferred paradigm (v3.2)

`goals/PARADIGM.md` declares the project's preferred programming paradigm (e.g., object-oriented, functional core / imperative shell, procedural, or an explicitly partitioned mix) and the concrete conventions that follow from it. It is filled in at project setup, alongside GOALS.md; preflight's `check_paradigm_declared` fails while it is still the placeholder.

Write new code in the declared paradigm. Deviating needs a stated reason; a deviation that constrains future code is a fork (§4) and needs an ADR. If the declaration itself turns out wrong for the project, that is evolution pressure: log it and change the declaration through an ADR, not by silent drift.
