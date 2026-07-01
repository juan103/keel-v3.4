"""ax-vacuous: named check (class invariant) for hz-vacuous-test.

Public: run(tree: Path) -> bool
  True iff tree exhibits the escape class: a recorded first-outcome flipped
  failed->passed across commits with NO code change (a vacuous green -- the test
  was backdated/declared passing without ever being seen red), OR a first-outcome
  entry was silently dropped across commits.

Wraps the REAL detector: log_integrity.detect_first_outcome_log_tampering, which
compares the committed tests/.first-outcome-log.json across the commits that
touched it (git log/show).  This module does NOT reimplement detection -- it calls
the real function and partitions its violation list into two separable clauses.

ACCEPTANCE/HISTORY SOURCE
  - Real git repo (.git/ at tree root): call the real detector directly.
  - Witness bundle (git-history.bundle present, no .git/): clone the bundle into a
    throwaway repo and call the real detector on the clone.  Retained witnesses
    cannot carry a nested .git/ in the main project repo, so they ship the history
    as a git bundle (a sidecar snapshot of real commits) -- the detector still runs
    on genuine git history, never on a reimplementation.

CLASS PREDICATE ANCHOR: _green_without_red(violations)
  True iff the real detector reported a "flip failed->passed without code change"
  violation -- the canonical vacuous-green escape.  The class-discriminating clause.

Other clause: _entry_dropped(violations)
  True iff the real detector reported an "entry dropped" violation.  Structurally
  separate (own top-level function) so the predicate-weakening is AST-localizable
  and a retained witness can be caught via this clause alone.

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
    """CLASS PREDICATE ANCHOR.

    True iff the REAL detector reported a "flip failed->passed without code change"
    violation.  This is the canonical vacuous-green escape: a recorded first-outcome
    was flipped from failed to passed in a commit that changed no code, so the test
    was declared passing without ever being observed red.  The class-discriminating
    clause for hz-vacuous-test.
    """
    return any(_FLIP_MARKER in v for v in violations)

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
