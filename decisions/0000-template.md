<!--
ADR numbering: 4-digit (NNNN). The kit ships ADR-0001 (non-determinism testing).
Project ADRs continue from 0002. Keeping 4 digits avoids collisions and matches
the kit's preflight, which expects `decisions/0001-non-deterministic-testing.md`.
-->

# ADR-NNNN: [Short name of the decision]

**Status:** proposed | accepted | superseded by ADR-NNNN
**Date:** YYYY-MM-DD

## Context

What's the situation that forced this decision? Two or three sentences. What were we doing when this came up?

## Options considered

1. Option A — one sentence
2. Option B — one sentence
3. Option C — one sentence (if applicable)

## Decision

What we're doing. One or two sentences.

## Consequences

What this commits us to. What now becomes harder. What we won't do as a result. Three to five lines maximum.

## Errata

(v3.1) ONE explicit-erratum appendix per ADR, for typo-class corrections
that do NOT change the Decision or Consequences content. Format: one dated
line per entry. Do not retro-edit Context / Options / Decision / Consequences
to "tidy up" wording: those sections are the historical record of what was
ratified. Use Errata only for:

- Spelling/grammar fixes.
- Stale phrasing left over from a draft Option that was rejected before
  acceptance (e.g., a Consequences line that still names Option 2 after the
  ADR was revised to Option 3 pre-acceptance).
- Broken cross-references (e.g., a paragraph cites ADR-0006 when it means
  ADR-0007).

Errata that would change what the ADR commits the project to are NOT errata.
Those are scope changes and require a new, superseding ADR.

(v3.3) Immutability is now checked mechanically: preflight's
`check_adr_immutability` diffs every accepted ADR against its acceptance
commit, exempting only this Errata section and the Status line's
accepted → superseded transition. Any other change fails preflight.

Format:

    ### YYYY-MM-DD
    - One-line correction. Original wording in §Consequences ("...") corrected to
      ("..."). Reason: Option 2 phrasing left over from pre-acceptance revision
      to Option 3; the Decision section and operative code already reflect
      Option 3.

Leave the section absent (delete this heading and explainer) until the first
erratum is actually needed; an empty Errata section is not load-bearing.

<!--
keel-binding example (FOR REFERENCE ONLY — do NOT uncomment in this template).

Binding ADRs that pre-register a falsifier or behavioral contract include
a fenced TOML block with the language identifier `keel-binding`. The kit's
preflight extracts these blocks and runs check_falsifier_consistency.

For a project that pre-registers a statistical falsifier (post-precheck,
empirical project shape):

    ```keel-binding-example
    type = "statistical_inference"
    id = "falsifier.primary"
    statistic = "mean_fisher_z_tmfg_edges"
    null = "category_preserving_permutation"
    alpha = 0.05
    p_value = "one_sided_1_plus_count_over_k_plus_1"
    rejected = ["distance_threshold_tail"]
    rejected_prose = ["low-distance tail", "D-rule"]
    ```

For a tool/behavioral project:

    ```keel-binding-example
    type = "behavioral"
    id = "falsifier.primary"
    behavior = "cli_accepts_piped_stdin"
    test = "tests/test_phase_1.py::test_stdin_accepted"
    rejected = ["positional_arg_only"]
    rejected_prose = ["positional argument only"]
    ```

To make a real binding block in your ADR, copy one of the patterns above
into a NEW ADR (not this template), change the language identifier from
`keel-binding-example` to `keel-binding`, and remove the surrounding
HTML comment markers. The kit's extractor only matches the literal
`keel-binding` fence — examples in this template are deliberately
shielded by both the HTML comment and the language-identifier mismatch.

See proposal_v3.md "v3.SPINE.A" and ADR-0006 for context.
-->

<!--
Citation discipline (for ADRs that cite papers):

Any paper cited in the Context, Decision, or Consequences sections must
include a one-sentence "what this paper is actually about" annotation in
prose. If the paper has both a preprint and a published version with
divergent content, the citation explicitly names which version is the
source and notes the divergence. This catches the Mantegna/Chernov class
of phantom inconsistency. See proposal_v3.md v3.DOC.2.
-->
