"""ax-relaxation escape variant A: a DIFFERENT ## Commitments softening (class-predicate).

Class: a locked GOALS.md section softened so it diverges from the snapshot.
Mechanism: softens a different ## Commitments sentence than the reference mutator
  -- 'never relaxing a locked compliance gate' -> 'freely relaxing a locked
  compliance gate' -- so the Commitments section hash diverges from the committed
  snapshot.  Caught via the CLASS PREDICATE clause (_commitments_section_diverged);
  flips True->False under the Commitments-anchor weakening.  ## Falsifier is untouched.

Provenance:
  Authoring identity: Claude (Task 3 implementer, Phase 3.5b).
  Inputs seen: scenario_spec.py (clean GOALS.md + class definition), task brief.
  NOT derived from reading named_check.py internals.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations
from pathlib import Path


def mutator(tree: Path) -> None:
    """Soften a ## Commitments sentence (different from the reference mutator)."""
    goals = Path(tree) / "goals" / "GOALS.md"
    text = goals.read_text(encoding="utf-8")
    mutated = text.replace(
        "never relaxing a locked compliance gate without an accepted ADR.",
        "freely relaxing a locked compliance gate at our discretion.",
    )
    if mutated == text:
        # Fallback: blunt softening that still diverges the Commitments section.
        mutated = text.replace("## Commitments\n", "## Commitments\n\n[variant-a softened]\n")
    goals.write_text(mutated, encoding="utf-8")
