"""ax-adr-edit escape variant A: ## Decision section silently rewritten (no commit).

Class: accepted ADR body changed outside ## Errata or Status transition after
  acceptance commit.
Mechanism: rewrites the ## Decision section body in the working tree without
  committing.  The acceptance commit still holds the original ## Decision text.
  adr_guard's _strip_mutable + _strip_consequences comparison sees the
  divergence in the non-Consequences body -> _immutable_body_changed fires.

This is a CLASS-PREDICATE escape:
  - Caught by _immutable_body_changed (the class-predicate anchor) -> True.
  - Under surgical weakening (_immutable_body_changed -> False): the
    _consequences_changed clause does not fire (## Consequences unchanged)
    -> overall False.  The variant FLIPS True->False under weakening.

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
    """Silently rewrite ## Decision body in the working tree (class-predicate escape)."""
    adr = Path(tree) / _ADR_REL
    text = adr.read_text(encoding="utf-8")
    mutated = text.replace(
        (
            "## Decision\n\n"
            "We apply this constraint for the duration of the phase. The ratified decision\n"
            "is immutable once accepted per CLAUDE.md section 7.\n"
        ),
        (
            "## Decision\n\n"
            "[VARIANT-A] The constraint application scope has been broadened without\n"
            "ratification. This rewrites the decision body after acceptance.\n"
        ),
    )
    if mutated == text:
        # Fallback: inject a marker if the exact string was not found.
        mutated = text.rstrip("\n") + "\n<!-- decision-variant-a-mutated -->\n"
    adr.write_text(mutated, encoding="utf-8")
