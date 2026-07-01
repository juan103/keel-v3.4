"""ax-frame-validity: named check (class invariant) for hz-frame-validity-unexpressible.

Public: run(tree: Path) -> bool
  True iff tree exhibits the escape class: a frame_validity binding block in
  decisions/ has its author_verdict null or empty, OR its audit_artifact file
  is absent from the tree.

Wraps real detection via binding.extract_keel_binding_blocks. Returns bool, never raises.

CLASS PREDICATE ANCHOR: _author_verdict_null(block)
  The class-discriminating clause. Catches the primary escape: author_verdict
  is absent, null, or empty/whitespace in the frame_validity block, meaning
  the frame-validity audit is unverified.

Other clause: _audit_artifact_missing(block, tree)
  Catches the structural-absence escape: the audit_artifact path is declared
  but the file does not exist at tree / audit_artifact.
  Structurally separate so predicate-weakening is AST-localizable and a
  retained witness can be caught via this non-predicate clause.

ASCII-only.  Stdlib + binding (the REAL keel-binding block extraction).
"""
from __future__ import annotations
import sys
from pathlib import Path

# File location: keel_v3.4/tests/kit/adversarial/ax-frame-validity/named_check.py
#   parents[0]=ax-frame-validity  parents[1]=adversarial  parents[2]=kit
#   parents[3]=tests               parents[4]=keel_v3.4   <- kit root
_KIT_ROOT = str(Path(__file__).resolve().parents[4])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import binding  # noqa: E402


def _author_verdict_null(block: dict) -> bool:
    """CLASS PREDICATE ANCHOR.

    True iff the frame_validity block's author_verdict is absent, null, or
    empty/whitespace. This is the class-discriminating clause for
    hz-frame-validity-unexpressible: the canonical escape clears the verdict
    field so the frame-validity audit is unverified in the binding block.
    """
    verdict = block.get("author_verdict", "")
    return not (isinstance(verdict, str) and verdict.strip())


def _audit_artifact_missing(block: dict, tree: Path) -> bool:
    """Other clause: True iff the audit_artifact file does not exist on tree.

    The audit_artifact field may be empty/missing (caught here) or non-empty
    but pointing to a file that does not exist under tree (the structural-
    absence escape). Separate from the class-predicate anchor so predicate-
    weakening is AST-localizable and this clause remains active under that
    weakening.
    """
    artifact_str = block.get("audit_artifact", "")
    if not artifact_str:
        return True  # missing or empty field: treat as absent
    return not (Path(tree) / artifact_str).exists()


def run(tree: Path) -> bool:
    """True iff tree exhibits the escape class."""
    tree = Path(tree)
    for adr in binding.find_binding_adrs(tree):
        try:
            blocks = binding.extract_keel_binding_blocks(adr)
        except ValueError:
            return True  # malformed TOML block: treat as caught
        for block in blocks:
            if block.get("type") != "frame_validity":
                continue
            if _author_verdict_null(block):
                return True
            if _audit_artifact_missing(block, tree):
                return True
    return False
