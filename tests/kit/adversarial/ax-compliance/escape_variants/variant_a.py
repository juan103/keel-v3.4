"""ax-compliance escape variant A: a DIFFERENT ## Falsifier softening (class-predicate).

Class: a locked GOALS.md section softened so it diverges from the snapshot.
Mechanism: softens a different ## Falsifier sentence than the reference mutator
  -- 'the deliverable is refused.' -> 'the deliverable is accepted.' -- so the
  Falsifier section hash diverges from the committed snapshot.  Caught via the
  CLASS PREDICATE clause (_falsifier_section_diverged); flips True->False under the
  Falsifier-anchor weakening.  ## Commitments is untouched.

Provenance:
  Authoring identity: Claude (Task 2 implementer, Phase 3.5b).
  Inputs seen: scenario_spec.py (clean GOALS.md + class definition), task brief.
  NOT derived from reading named_check.py internals.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations
from pathlib import Path


def mutator(tree: Path) -> None:
    """Soften a ## Falsifier sentence (different from the reference mutator)."""
    goals = Path(tree) / "goals" / "GOALS.md"
    text = goals.read_text(encoding="utf-8")
    mutated = text.replace(
        "the deliverable is refused.",
        "the deliverable is accepted.",
    )
    if mutated == text:
        # Fallback: blunt softening that still diverges the Falsifier section.
        mutated = text.replace("## Falsifier\n", "## Falsifier\n\n[variant-a softened]\n")
    goals.write_text(mutated, encoding="utf-8")
