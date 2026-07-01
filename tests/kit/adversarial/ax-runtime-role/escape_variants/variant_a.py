"""ax-runtime-role escape variant A: multi-line contributor value (no token).

Class: runtime_role=author field set without paired valid attestation.
Mechanism: the ## Contributor section is filled with a multi-line value
  (multi-paragraph contributor entry) but no attestation token is created.
  Same field/section as the reference mutator; different value format.
  Verifies the class invariant is content-agnostic (any non-empty value qualifies).

Provenance:
  Authoring identity: Claude Sonnet 4 as Task 4 implementer.
  Inputs seen: scenario_spec.py (class definition), task-4-brief.md.
  NOT derived from reading named_check.py internals.

ASCII-only. Stdlib only.
"""
from __future__ import annotations
from pathlib import Path

_ARTIFACT = "decisions/0010-keel-binding.md"


def mutator(tree: Path) -> None:
    """Set ## Contributor to a multi-line value with no attestation token."""
    adr = Path(tree) / _ARTIFACT
    text = adr.read_text(encoding="utf-8")
    new_body = (
        "System Agent\n"
        "Automated Contributor (no attestation token)\n"
        "Role: primary author\n"
    )
    mutated = text.replace(
        "## Contributor\n\n",
        "## Contributor\n\n" + new_body,
    )
    if mutated == text:
        mutated = text.rstrip("\n") + "\n\n## Contributor\n\n" + new_body
    adr.write_text(mutated, encoding="utf-8")
