"""ax-frame-validity: SURGICALLY WEAKENED twin of named_check.py (F1 Control 1).

This module is a verbatim copy of named_check.py EXCEPT for the body of the
class-predicate anchor _author_verdict_null, which is neutralized to
`return False`. Every other top-level function (_audit_artifact_missing, run)
is byte-identical, so the AST diff between named_check.py and this file is
confined to the single anchor function (f1_harness._ast_changed_functions
proves this executably for F1 Control 1 leg (a)).

Effect: the 'author_verdict null or empty' CLASS is no longer caught, but the
_audit_artifact_missing clause still fires, so the missing-artifact escape
and the missing-artifact retained witness remain caught. This is the surgical
weakening that makes the F1 cell (escape, weakened) -> caught=False.

This file is NOT a real check. It exists only as the Control-1 weakening twin.

ASCII-only.  Stdlib + binding.
"""
from __future__ import annotations
import sys
from pathlib import Path

_KIT_ROOT = str(Path(__file__).resolve().parents[4])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import binding  # noqa: E402


def _author_verdict_null(block: dict) -> bool:
    """SURGICALLY WEAKENED CLASS PREDICATE ANCHOR.

    The intact anchor returns True iff author_verdict is absent, null, or
    empty/whitespace. This weakened twin returns False unconditionally, so the
    'null verdict' CLASS is no longer caught. The change is confined to THIS
    function; _audit_artifact_missing and run are untouched.
    """
    return False


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
