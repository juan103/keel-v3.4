# Pre-stamp adversarial review

Template for the adversarial-review artifact required by `check_pre_stamp_review_exists` (v3.SPINE.C).

Per ADR-0007: adversarial review is human-in-the-loop multi-AI in v3, not automated. The kit ships `ADVERSARIAL_REVIEW_PROMPT.md` (Phase 6 deliverable). The user takes the proposal's pre-registration to at least two parallel AI sessions of different model families (e.g., Claude + GPT, Claude + Gemini), runs the prompt, and produces this file with each catch and its disposition.

The kit verifies *presence* of this file in `post_stamp` state. It does not verify *quality* — that is on the user. Pretending to verify quality would be ceremony.

---

**Date:** YYYY-MM-DD
**Reviewers:** <list of AI sessions / model families that produced this artifact, e.g., "Claude Sonnet 4.6, GPT-5">
**Project:** <project name>

## Catches and dispositions

Each catch from any reviewer becomes a numbered subsection. Disposition is one of:

- **resolved** — change made; reference where (commit hash, ADR, predictions.md row).
- **accepted-risk** — change not made; risk acknowledged. Reference the corresponding entry in `goals/load-bearing-assumptions.md`.
- **deferred** — change deferred to a future phase. Name the phase.

### C1 — <short title>

**Source:** <which reviewer flagged this>
**Catch:** <what they flagged, in their words>
**Disposition:** resolved | accepted-risk | deferred
**Action:** <commit hash / ADR-NNNN / load-bearing-assumption ID / phase reference>
**Notes:** <optional explanation>

### C2 — ...

## Reviewer summaries

(Optional. Each reviewer's high-level read of the pre-registration after their pass.)
