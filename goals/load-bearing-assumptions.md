# Load-bearing assumptions

Project-internal assumptions that the literature does not directly support — load-bearing in the sense that the project's claim depends on them, but unverified at declaration time. This file is the canonical home for these. Keep `kit-friction.md` for kit bugs only.

## Lifecycle states

Each assumption has one of five states. Transitions require dated resolution-log entries pointing to evidence.

- **`unverified`** — entry default. The assumption is named but not yet validated.
- **`verified`** — validated by executable evidence (test result, validation output). Resolution log names where.
- **`falsified`** — validation failed. Typically triggers a project pivot or closure ADR.
- **`accepted-risk`** — validation deferred; the project accepts the risk under specified conditions, with a re-review deadline.
- **`retired`** — no longer load-bearing because project scope changed. Dated rationale required.

## Closure discipline

Every assumption with `Resolution required before: Gate N` must be in a terminal state (`verified`, `falsified`, `accepted-risk`, `retired`) before that gate is ratified. The kit's `check_load_bearing_assumptions_closed_at_gate` enforces this mechanically.

**Deadlock escape (ADR-0009):** if an assumption tagged for Gate N cannot be verified at Gate N because of an upstream dependency, the legitimate path is `accepted-risk` with a `Resolution required before:` deadline naming a future gate. **Editing the original deadline backward (e.g., from `Gate 1` to `Gate 3` because Gate 1 is upon us and the assumption isn't ready) is forbidden.** That move turns the discipline into ceremony. The kit cannot mechanically prevent the edit (this file is editable), but the convention is named: backward-edits violate the discipline and should be ADR'd as scope changes if they're real. The kit's `detect_backward_deadline_edits` warns advisorily when it finds backward edits in git history.

## Format

```markdown
### <ID> — <short title>

**Tagged in:** ADR-NNNN, predictions.md F<N>
**Status:** unverified | verified | falsified | accepted-risk | retired
**Resolution required before:** Gate <N> | project closure
**Validation rule:** <pre-registered procedure for verifying this at execution time>
**Fallback:** <what the project does if validation fails>
**Resolution log:**
- YYYY-MM-DD: <event> <evidence pointer>
```

## Entries

### §8 — External-validation monoculture (hazard list and adversary exercise)

**Tagged in:** ADR-0002, GOALS.md §Named assumption
**Status:** accepted-risk
**Resolution required before:** the Commitment-12 pilot gate
**Validation rule:** At the Commitment-12 pilot gate: produce evidence of at least one external human expert review of the v3.4 hazard list, OR a cross-audit comparison with an independently-derived hazard enumeration covering the same refusal-critical surface. Alternatively, document a principled argument for why monoculture risk is acceptable given the pilot's scope.
**Fallback:** If external validation cannot be obtained before the pilot gate, escalate to project leadership; do not silently extend the deadline. If the risk is accepted again, create a new `accepted-risk` entry with the updated deadline and record the re-acceptance rationale.
**Resolution log:**
- 2026-06-21: declared at Gate 0 ratification; state set to `accepted-risk`. The hazard list derives solely from the v3.3 self-audit (AI-generated). Both the hazard enumeration and the planned adversary exercise (Phase 3) rely on AI judgment, creating potential for shared blind spots. Accepted as risk at this stage; deadline set to the Commitment-12 pilot gate.
