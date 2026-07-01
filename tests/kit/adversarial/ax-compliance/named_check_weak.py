"""ax-compliance: SURGICALLY WEAKENED twin of named_check.py (F1 Control 1).

This module is a verbatim copy of named_check.py EXCEPT for the body of the
class-predicate anchor _falsifier_section_diverged, which is neutralized to
`return False`.  Every other top-level function (_current_goals_sections,
_snapshot_goals_sections, _commitments_section_diverged, run) is byte-identical,
so the AST diff between named_check.py and this file is confined to the single
anchor function (f1_harness._ast_changed_functions proves this executably for
F1 Control 1 leg (a)).

Effect: the ## Falsifier-divergence CLASS is no longer caught, but the
## Commitments-divergence clause (_commitments_section_diverged) still fires, so
the Commitments-softening variant and the Commitments-caught retained witness
remain caught.  This is the surgical weakening that makes the F1 cell
(escape, weakened) -> caught=False.

This file is NOT a real check.  It exists only as the Control-1 weakening twin.

ASCII-only.  Stdlib + commitment_lock (the real goals-section computation).
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

_KIT_ROOT = str(Path(__file__).resolve().parents[4])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import commitment_lock

_LOCKED_SECTIONS = ("Falsifier", "Commitments")


def _current_goals_sections(tree: Path) -> dict:
    """Compute the live goals_sections for tree, exactly as snapshot_lock does.

    Reuses the REAL commitment_lock._section extractor + sha256 (the same
    computation commitment_lock.snapshot_lock uses for its goals_sections key),
    so this observable is a faithful subset of the commitment-lock surface and
    not a re-implementation of the divergence philosophy.
    """
    goals = (Path(tree) / "goals" / "GOALS.md").read_text(encoding="utf-8")
    return {
        n: hashlib.sha256(commitment_lock._section(goals, n).encode("utf-8")).hexdigest()
        for n in _LOCKED_SECTIONS
    }


def _snapshot_goals_sections(tree: Path) -> dict:
    """Read the committed goals_sections snapshot from goals/.commitment-lock.json."""
    lock_path = Path(tree) / "goals" / ".commitment-lock.json"
    if not lock_path.exists():
        return {}
    snapshot = json.loads(lock_path.read_text(encoding="utf-8"))
    return snapshot.get("goals_sections", {})


def _falsifier_section_diverged(snapshot_sections: dict, current_sections: dict) -> bool:
    """SURGICALLY WEAKENED CLASS PREDICATE ANCHOR.

    The intact anchor returns True iff the ## Falsifier locked section diverged.
    This weakened twin returns False unconditionally, so the Falsifier-divergence
    CLASS is no longer caught.  The change is confined to THIS function;
    _commitments_section_diverged and run are byte-identical to named_check.py.
    """
    return False


def _commitments_section_diverged(snapshot_sections: dict, current_sections: dict) -> bool:
    """Other clause: True iff the ## Commitments locked section diverged.

    A separate locked GOALS.md section.  Caught independently of the Falsifier
    anchor so a Commitments-softening witness survives a Falsifier-anchor
    weakening (the C1 retained-witness / non-predicate-clause mechanism).
    """
    return snapshot_sections.get("Commitments") != current_sections.get("Commitments")


def run(tree: Path) -> bool:
    """True iff tree exhibits the escape class (a locked GOALS.md section diverged)."""
    tree = Path(tree)
    snapshot_sections = _snapshot_goals_sections(tree)
    if not snapshot_sections:
        return False
    current_sections = _current_goals_sections(tree)
    if _falsifier_section_diverged(snapshot_sections, current_sections):
        return True
    if _commitments_section_diverged(snapshot_sections, current_sections):
        return True
    return False
