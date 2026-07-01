"""ax-frame-validity escape variant B: missing audit artifact file (other clause).

Class: frame_validity block where the audit_artifact file does not exist on tree.
Mechanism: deletes the audit/frame_validity_audit.json file from the tree.
  The binding block still has audit_artifact = "audit/frame_validity_audit.json"
  (field is non-empty) but the referenced file is absent.
  Caught via the OTHER CLAUSE (_audit_artifact_missing), NOT the class-predicate
  anchor (_author_verdict_null), so it SURVIVES the anchor surgical weakening
  (the C1 non-predicate-survivor mechanism). The author_verdict is untouched.

Provenance:
  Authoring identity: Claude as Task implementer (Phase 3.5b).
  Inputs seen: scenario_spec.py (class definition + fixture layout).
  NOT derived from reading named_check.py internals.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations
from pathlib import Path

_AUDIT_ARTIFACT = "audit/frame_validity_audit.json"


def mutator(tree: Path) -> None:
    """Delete the audit artifact file so _audit_artifact_missing fires."""
    audit_path = Path(tree) / _AUDIT_ARTIFACT
    if audit_path.exists():
        audit_path.unlink()
    # If the file already does not exist, the escape is already present.
