"""ax-adr-edit escape variant B: ## Consequences section silently rewritten (no commit).

Class: accepted ADR body changed outside ## Errata or Status transition after
  acceptance commit.
Mechanism: rewrites the ## Consequences section body in the working tree without
  committing.  The acceptance commit still holds the original ## Consequences text.
  _consequences_changed detects the divergence in the Consequences section.

This is an OTHER-CLAUSE escape (survives surgical weakening):
  - _immutable_body_changed: after stripping Consequences, both texts are
    identical (only ## Consequences changed) -> False.
  - _consequences_changed: Consequences section differs -> True.
  - Under surgical weakening (_immutable_body_changed -> False):
    _consequences_changed still fires -> True.  The variant SURVIVES weakening.

Provenance:
  Authoring identity: Claude as ax-adr-edit Task implementer.
  Inputs seen: scenario_spec.py (class definition, fixture structure).
  NOT derived from reading named_check.py internals.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations
from pathlib import Path

_ADR_REL = "decisions/0001-test-constraint.md"


def mutator(tree: Path) -> None:
    """Silently rewrite ## Consequences body in the working tree (other-clause escape)."""
    adr = Path(tree) / _ADR_REL
    text = adr.read_text(encoding="utf-8")
    mutated = text.replace(
        (
            "## Consequences\n\n"
            "This decision constrains future flexibility in the trade-off space. Any\n"
            "subsequent change to the core decision requires a new superseding ADR.\n"
        ),
        (
            "## Consequences\n\n"
            "[VARIANT-B] Constraints on future flexibility are subject to agent\n"
            "interpretation at runtime. The original ratification may be revisited\n"
            "without a new superseding ADR.\n"
        ),
    )
    if mutated == text:
        # Fallback: inject a marker if the exact string was not found.
        mutated = text.rstrip("\n") + "\n<!-- consequences-variant-b-mutated -->\n"
    adr.write_text(mutated, encoding="utf-8")
