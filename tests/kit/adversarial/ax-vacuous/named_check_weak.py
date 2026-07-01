"""ax-vacuous: SURGICALLY WEAKENED twin of named_check.py (F1 Control 1).

Verbatim copy of named_check.py EXCEPT the body of the class-predicate anchor
_green_without_red, neutralized to `return False`.  Every other top-level function
(_violations_for, _entry_dropped, run) is byte-identical, so the AST diff between
named_check.py and this file is confined to the single anchor function
(f1_harness._ast_changed_functions proves this for F1 Control 1 leg (a)).

Effect: the vacuous-green CLASS (flip failed->passed without code change) is no
longer caught, but the _entry_dropped clause still fires, so the dropped-entry
variant and the dropped-entry-caught retained witness remain caught.  This is the
surgical weakening that makes the F1 cell (escape, weakened) -> caught=False while
(witness_2, weakened) -> caught=True (survives).

This file is NOT a real check.  It exists only as the Control-1 weakening twin.

ASCII-only.  Stdlib + log_integrity.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# keel_v3.4/ root is parents[4] from this file.
_KIT_ROOT = str(Path(__file__).resolve().parents[4])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

try:
    import log_integrity
except ImportError as _e:
    raise ImportError(
        f"log_integrity not found on sys.path (kit root: {_KIT_ROOT!r}): {_e}"
    ) from _e

# The retained-witness git-history bundle (sidecar snapshot of real commits).
_BUNDLE_NAME = "git-history.bundle"

# Stable violation-string substrings emitted by the REAL detector
# (log_integrity.detect_first_outcome_log_tampering).
_FLIP_MARKER = "flip failed->passed without code change"
_DROP_MARKER = "entry dropped"


def _violations_for(tree: Path) -> list:
    """Return the REAL detector's output (list[str]) for tree.

    - Real git repo (.git/ present): call the real detector directly.
    - Witness bundle present (no .git/): clone the bundle into a throwaway repo and
      call the real detector on the clone.
    - Neither: [] (the real detector would also skip a non-git tree).
    """
    tree = Path(tree)
    if (tree / ".git").is_dir():
        return log_integrity.detect_first_outcome_log_tampering(tree)
    bundle = tree / _BUNDLE_NAME
    if bundle.is_file():
        work_root = Path(tempfile.mkdtemp(prefix="ax_vacuous_witness_"))
        try:
            repo = work_root / "repo"
            proc = subprocess.run(
                ["git", "clone", "--quiet", str(bundle), str(repo)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if proc.returncode != 0:
                return []
            return log_integrity.detect_first_outcome_log_tampering(repo)
        finally:
            shutil.rmtree(work_root, ignore_errors=True)
    return []

def _green_without_red(violations: list) -> bool:
    """SURGICALLY WEAKENED CLASS PREDICATE ANCHOR.

    The intact anchor returns True iff the real detector reported a flip
    failed->passed without code change.  This weakened twin returns False
    unconditionally, so the vacuous-green CLASS is no longer caught.  The change is
    confined to THIS function; _violations_for, _entry_dropped, and run are
    byte-identical to named_check.py.
    """
    return False

def _entry_dropped(violations: list) -> bool:
    """Other clause.

    True iff the REAL detector reported an "entry dropped" violation -- a
    first-outcome entry that existed in an earlier commit was removed in a later
    one (its red evidence silently deleted).  Separable from _green_without_red: a
    dropped entry leaves no flip marker, so this clause survives the surgical
    weakening of the anchor.
    """
    return any(_DROP_MARKER in v for v in violations)


def run(tree: Path) -> bool:
    """True iff tree exhibits the escape class (via the REAL detector's output)."""
    violations = _violations_for(tree)
    if _green_without_red(violations):
        return True
    if _entry_dropped(violations):
        return True
    return False
