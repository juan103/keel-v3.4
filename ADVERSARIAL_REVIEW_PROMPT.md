# ADVERSARIAL REVIEW PROMPT

Use this prompt in at least two parallel AI sessions of *different model families* (e.g., Claude + GPT, Claude + Gemini, GPT + Gemini). The kit ships this prompt; running it is the user's discipline. The kit verifies *presence* of the resulting `pre-stamp-review.md`, not its quality.

Per ADR-0007: adversarial review is human-in-the-loop multi-AI in v3. The case for it comes from `beliefwire`'s kit-friction log, where multi-AI critique caught five real methodological problems that the single-LLM precheck silently waved through.

---

## THE PROMPT

Paste this into a fresh session (claude.ai, ChatGPT, gemini.google.com — not the same one used for the precheck or the implementation):

```
You are reviewing a project's pre-registration before it is committed to via OpenTimestamps stamp or equivalent irreversible commitment artifact. Your job is to be hostile to the methodology, not to the author. Find what would survive scrutiny by an adversarial reviewer at peer review or replication time.

I will paste the project's binding ADR(s), GOALS.md, and predictions.md (if present). You will respond with the four audits below, each as a numbered list of catches. For each catch: state it in one sentence, name what specifically is wrong or under-specified, and propose how it should be resolved.

1. PARAMETER SHAPE AUDIT
For every pre-registered parameter:
   - Primary statistic named and unambiguous?
   - Primary null hypothesis explicit?
   - Fallback behavior on edge cases (NaN, divergence, missing data) specified?
   - Pre-registered prior under chosen parameters consistent with stated prior?
   - Mismatch between implied prior and stated prior flagged?

2. CITATION DISCIPLINE AUDIT
For every paper cited in a binding ADR or F-table entry:
   - One-sentence "what this paper is actually about" annotation present?
   - If preprint and published version differ: explicit choice named, with note on the divergence?
   - Applicability of the paper's method to the project's actual object class (not adjacent)?
   - Any paper used as load-bearing for a method that the paper does NOT explicitly claim works on this object class?

3. NULL TAXONOMY AUDIT
For any null or null suite:
   - Each null declares which alternative hypothesis it tests against?
   - Joint statistics across non-comparable nulls (different alternatives) flagged as category errors?
   - Any "null" actually testing the alternative it claims to disprove?

4. CONVERSATIONAL-PRESSURE AUDIT
For every commitment in the binding ADR:
   - Has the user already hedged on it in conversation? If so, has it been explicitly defended or explicitly demoted via ADR (not via soft edit)?
   - Any commitment that is a placeholder ("TBD", "to be tightened later") that has not been tightened?
   - Any commitment that exists only because the precheck prompt asked for one (i.e., ceremonial pre-registration)?

After the four audits, end with: "Disposition recommendations" — for each catch, one of `resolved | accepted-risk | deferred`.

Be direct. Push back if the binding looks like it would let any reasonable analysis pass. Do not be encouraging by default. If you cannot find anything to flag, say so explicitly and explain why.
```

---

## HOW TO USE

1. Run the precheck prompt and produce `goals/GOALS.md` + binding ADR.
2. Open at least two parallel sessions in *different* AI families.
3. Paste this prompt into each, then paste the binding ADR(s) and GOALS.md.
4. Compile each session's catches into `pre-stamp-review.md` (template at kit root).
5. Apply each catch's disposition (resolved → make the change; accepted-risk → file in `goals/load-bearing-assumptions.md`; deferred → reference the future phase).
6. Commit `pre-stamp-review.md`. Then run `python preflight.py`. The check `check_pre_stamp_review_exists` verifies presence; quality is on you.
7. OTS-stamp (or equivalent commitment) only after `pre-stamp-review.md` is committed.

If a session refuses or runs the prompt superficially, escalate by re-asking with "do step 4 properly. Find at least three catches the adversarial reviewer would make. If you cannot, explain why the binding is genuinely tight."

The point of running this in *different* model families is that each family has different blind spots. Single-AI critique (even of a different session) is closer to the original generator's biases than multi-AI critique.
