"""ax-compliance escape variant B: a ## Commitments softening (OTHER clause).

Class: a locked GOALS.md section softened so it diverges from the snapshot.
Mechanism: softens a ## Commitments line -- 'never relaxing a locked compliance
  gate' -> 'freely relaxing a locked compliance gate' -- so the Commitments
  section hash diverges from the committed snapshot.  Caught via the OTHER clause
  (_commitments_section_diverged), NOT the Falsifier anchor, so it SURVIVES the
  Falsifier-anchor surgical weakening (the C1 non-predicate-survivor mechanism).
  ## Falsifier is untouched.

Provenance:
  Authoring identity: Claude (Task 2 implementer, Phase 3.5b).
  Inputs seen: scenario_spec.py (clean GOALS.md + class definition), task brief.
  NOT derived from reading named_check.py internals.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations
from pathlib import Path


def mutator(tree: Path) -> None:
    """Soften a ## Commitments line so the Commitments section diverges."""
    goals = Path(tree) / "goals" / "GOALS.md"
    text = goals.read_text(encoding="utf-8")
    mutated = text.replace(
        "never relaxing a locked compliance gate",
        "freely relaxing a locked compliance gate",
    )
    if mutated == text:
        # Fallback: blunt softening that still diverges the Commitments section.
        mutated = text.replace("## Commitments\n", "## Commitments\n\n[variant-b softened]\n")
    goals.write_text(mutated, encoding="utf-8")
