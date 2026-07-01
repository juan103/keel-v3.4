"""KEEL v3.4: tamper-evidence for the first-outcome (red-green) log.
falsifier_strength: partial, falsifier_layer: post_hoc -- detects after the
fact (auditability), does not prevent at runtime. Reuses the git-history-diff
pattern from adr_guard.py / assumptions.py."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

_LOG_REL = "tests/.first-outcome-log.json"


def _git(args, cwd):
    try:
        return subprocess.run(["git"] + args, cwd=cwd, capture_output=True,
                              text=True, check=True, encoding="utf-8",
                              errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _commits_touching_log(repo_root):
    r = _git(["log", "--format=%H", "--", _LOG_REL], repo_root)
    if r is None or not r.stdout.strip():
        return []
    return r.stdout.split()  # newest first


def _log_at(repo_root, commit):
    r = _git(["show", f"{commit}:{_LOG_REL}"], repo_root)
    if r is None:
        return {}
    try:
        data = json.loads(r.stdout)
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _files_in_commit(repo_root, commit):
    r = _git(["show", "--name-only", "--format=", commit], repo_root)
    return set(line for line in r.stdout.splitlines() if line) if r else set()


def detect_first_outcome_log_tampering(repo_root: Path) -> list[str]:
    """Flag commits that flipped a recorded first-outcome from 'failed' to
    'passed', or dropped an entry, without a code change in the same commit.
    Empty list == OK. Silent skip when not a git repo.

    Caveat: the same-commit code-change carve-out is a heuristic -- a real
    code change in a DIFFERENT commit than the flip, or a merge commit, may
    not be detected (acceptable for a partial/post_hoc falsifier)."""
    if _git(["rev-parse", "--git-dir"], repo_root) is None:
        return []
    commits = _commits_touching_log(repo_root)
    violations: list[str] = []
    # commits is newest-first; compare each commit C to its parent state.
    for i, commit in enumerate(commits):
        parent_commits = commits[i + 1:]
        if not parent_commits:
            continue  # the first commit that introduced the log: nothing to compare
        before = _log_at(repo_root, parent_commits[0])
        after = _log_at(repo_root, commit)
        touched = _files_in_commit(repo_root, commit)
        code_changed = any(f != _LOG_REL and f.endswith(".py") for f in touched)
        for nodeid, prev in before.items():
            if nodeid not in after:
                violations.append(
                    f"first-outcome entry dropped in commit {commit[:7]}: {nodeid}")
                continue
            if prev.get("first") == "failed" and after[nodeid].get("first") == "passed" \
                    and not code_changed:
                violations.append(
                    f"first-outcome flip failed->passed without code change in "
                    f"commit {commit[:7]}: {nodeid}")
    return violations
