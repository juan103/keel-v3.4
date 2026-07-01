"""Gate-1 idempotency + exclusion-list invariants (spec 5.3). Slow: runs preflight
--strict in a subprocess. Run from the kit root (keel_v3.4/)."""
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]   # keel_v3.4/
EXCLUDED = [".reachability-cache.json", ".checks-cache.json"]


def _git(*args):
    return subprocess.run(["git", *args], cwd=str(KIT), capture_output=True, text=True)


def test_excluded_artifacts_are_untracked():
    # Each ephemeral cache must be git-untracked (ignored), so writing it never dirties
    # a tracked path. ls-files --error-unmatch exits non-zero for an untracked path.
    for name in EXCLUDED:
        r = _git("ls-files", "--error-unmatch", name)
        assert r.returncode != 0, f"{name} is tracked but must be gitignored (5.3)"


def test_first_outcome_log_is_tracked():
    # The "not written by --strict" half of this invariant is covered by
    # test_strict_writes_no_tracked_path (the tracked log would surface as a non-?? line).
    r = _git("ls-files", "--error-unmatch", "tests/.first-outcome-log.json")
    assert r.returncode == 0, "tests/.first-outcome-log.json must be committed (tracked)"


def test_strict_writes_no_tracked_path():
    # Run preflight --strict, then assert no TRACKED file changed (porcelain shows only
    # ignored/untracked caches, which are filtered out by --porcelain's default).
    before = _git("status", "--porcelain").stdout
    r = subprocess.run([sys.executable, "preflight.py", "--strict"],
                       cwd=str(KIT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]
    after = _git("status", "--porcelain").stdout
    # Tracked-file modifications appear as ' M ' / 'M  ' lines; untracked as '??'.
    tracked_changes = [ln for ln in after.splitlines() if not ln.startswith("??")]
    tracked_before = [ln for ln in before.splitlines() if not ln.startswith("??")]
    assert tracked_changes == tracked_before, \
        f"--strict modified tracked paths: {set(tracked_changes) - set(tracked_before)}"
