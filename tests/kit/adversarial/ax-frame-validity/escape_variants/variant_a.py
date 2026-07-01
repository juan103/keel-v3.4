"""ax-frame-validity escape variant A: whitespace-only author_verdict (class predicate).

Class: frame_validity block with null/empty/whitespace author_verdict.
Mechanism: replaces author_verdict = "APPROVED" with author_verdict = "   "
  (whitespace-only string) -- a DIFFERENT null representation than the reference
  mutator which uses an empty string. Both fail the strip() check and are caught
  by _author_verdict_null. Flips True->False under the anchor weakening.

Provenance:
  Authoring identity: Claude as Task implementer (Phase 3.5b).
  Inputs seen: scenario_spec.py (class definition + clean ADR content).
  NOT derived from reading named_check.py internals.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations
import re
from pathlib import Path

_ADR = "decisions/0010-keel-binding.md"


def mutator(tree: Path) -> None:
    """Set author_verdict to whitespace-only (different null form from reference mutator)."""
    adr = Path(tree) / _ADR
    text = adr.read_text(encoding="utf-8")
    mutated = text.replace(
        'author_verdict = "APPROVED"',
        'author_verdict = "   "',
    )
    if mutated == text:
        # Fallback: regex replacement for any existing verdict value.
        mutated = re.sub(
            r'(author_verdict\s*=\s*)"[^"]*"',
            r'\1"   "',
            text,
        )
    adr.write_text(mutated, encoding="utf-8")
