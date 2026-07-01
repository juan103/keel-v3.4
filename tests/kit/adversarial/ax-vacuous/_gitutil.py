"""ax-vacuous: internal git-fixture helper (NOT a contract file).

Shared by scenario_spec.py and the escape_variants so that the REAL
log_integrity.detect_first_outcome_log_tampering can run against a REAL git
repository (the function returns [] -- silent skip -- when not in a git repo,
so a real repo with real commit history is mandatory).

Determinism (for F1 Control 3 byte-identical replication):
  - GIT_AUTHOR_DATE / GIT_COMMITTER_DATE pinned to epoch-0 -> stable commit hash.
  - Fixed author/committer identity.
  - Non-deterministic git internals (.git/index, .git/logs/, .git/hooks/,
    ORIG_HEAD, FETCH_HEAD) deleted after every commit; git log/show need only
    .git/objects/ and .git/refs/.
  - Second commits use `git read-tree HEAD` to repopulate the index from HEAD
    (the index was deleted post-baseline) so foo.py stays tracked and the
    escape commit touches ONLY the log (-> code_changed=False in the real fn).

ASCII-only.  Stdlib only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

LOG_REL = "tests/.first-outcome-log.json"
CODE_REL = "foo.py"
NODE_A = "tests/test_phase_1.py::test_R_1_1_data_is_hashable"
NODE_B = "tests/test_phase_1.py::test_R_1_2_hash_stable"

_EPOCH = "1970-01-01T00:00:00 +0000"
_IDENT = {
    "GIT_AUTHOR_DATE": _EPOCH,
    "GIT_COMMITTER_DATE": _EPOCH,
    "GIT_AUTHOR_NAME": "AX-Vacuous-Test",
    "GIT_AUTHOR_EMAIL": "test@ax-vacuous.test",
    "GIT_COMMITTER_NAME": "AX-Vacuous-Test",
    "GIT_COMMITTER_EMAIL": "test@ax-vacuous.test",
}


def git(args: list, cwd: Path, env: dict | None = None):
    """Run a git command; return CompletedProcess or None on failure."""
    _env = os.environ.copy()
    if env:
        _env.update(env)
    try:
        return subprocess.run(
            ["git"] + args, cwd=str(cwd), capture_output=True, text=True,
            check=True, encoding="utf-8", errors="replace", env=_env,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def serialize(log: dict) -> str:
    return json.dumps(log, indent=2) + "\n"


def read_log(dest: Path) -> dict:
    return json.loads((Path(dest) / LOG_REL).read_text(encoding="utf-8"))


def write_log(dest: Path, log: dict) -> None:
    (Path(dest) / LOG_REL).write_text(serialize(log), encoding="utf-8")


def clean_internals(dest: Path) -> None:
    """Delete non-deterministic git internals for C3 byte-identical replication."""
    g = Path(dest) / ".git"
    for name in ("index", "ORIG_HEAD", "FETCH_HEAD"):
        p = g / name
        if p.exists():
            p.unlink()
    for dname in ("logs", "hooks"):
        d = g / dname
        if d.exists():
            shutil.rmtree(d)


def init_baseline(dest: Path) -> None:
    """git init + identity + write foo.py and an HONEST red log, then first commit.

    The honest baseline records BOTH tracked tests with first: "failed" (each was
    observed to fail first -- the test-first protocol).  This single-commit tree is
    the CLEAN baseline: the real detector finds nothing to compare against -> [].
    """
    dest = Path(dest)
    if git(["-c", "init.defaultBranch=main", "init"], dest) is None:
        git(["init"], dest)
    git(["config", "user.name", "AX-Vacuous-Test"], dest)
    git(["config", "user.email", "test@ax-vacuous.test"], dest)
    git(["config", "commit.gpgsign", "false"], dest)

    (dest / "tests").mkdir(parents=True, exist_ok=True)
    (dest / CODE_REL).write_text("def data_hash(x):\n    return hash(x)\n", encoding="utf-8")
    write_log(dest, {
        NODE_A: {"first": "failed", "head": "aaa0000"},
        NODE_B: {"first": "failed", "head": "bbb1111"},
    })
    git(["add", CODE_REL], dest)
    git(["add", LOG_REL], dest)
    git(["commit", "-m", "baseline: honest first-outcome log (red)"], dest, env=_IDENT)
    clean_internals(dest)


def commit_log_change(dest: Path, msg: str, also_code: bool = False) -> None:
    """Make a SECOND commit staging the already-edited log (+ optionally a code change).

    `git read-tree HEAD` repopulates the index from HEAD first (the post-baseline
    index was deleted), so foo.py stays tracked.  With also_code=False the commit
    touches ONLY the log -> the real detector sees no .py change -> code_changed=False
    (a vacuous-green flip is flagged).  With also_code=True a foo.py change rides in
    the same commit -> code_changed=True -> the real detector's carve-out suppresses
    the flip (the legitimate red->green-with-code path).
    """
    dest = Path(dest)
    git(["read-tree", "HEAD"], dest)
    if also_code:
        (dest / CODE_REL).write_text("def data_hash(x):\n    return hash(repr(x))\n", encoding="utf-8")
        git(["add", CODE_REL], dest)
    git(["add", LOG_REL], dest)
    git(["commit", "-m", msg], dest, env=_IDENT)
    clean_internals(dest)
