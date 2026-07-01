"""
Load-bearing assumption parsing + closure check + backward-edit detection.

Spec: ../proposal_v3.md "v3.SPINE.D — Load-bearing-unverified-assumption tagging"
      v3-build/decisions/0009-assumption-tracking-policy.md (project-side ADR)

The file `goals/load-bearing-assumptions.md` lists assumptions the project is
making that the literature does not directly support. Each entry has:

    ### <ID> — <short title>
    **Tagged in:** <ADR-NNNN, predictions.md F<N>, ...>
    **Status:** unverified | verified | falsified | accepted-risk | retired
    **Resolution required before:** Gate <N> | project closure
    **Validation rule:** ...
    **Fallback:** ...
    **Resolution log:** ...

The closure check (R-4.2) refuses gate ratification when any assumption with
`Resolution required before: Gate <= current_gate` is still `unverified`.
The backward-edit detector (R-4.3) warns when a deadline gets pushed back
across commits — that is named as a discipline violation in the proposal,
not a hard error.

Plus check_pre_stamp_review_exists (R-4.1) — state-aware via state.py:
  precheck    skip silently
  pre_stamp   warn if pre-stamp-review.md missing; do not fail
  post_stamp  fail if pre-stamp-review.md missing
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# Lazy state.py import to avoid hard dependency for non-state-aware callers.
def _import_state():
    import state
    return state


# ---------------------------------------------------------------------------
# R-4.1: check_pre_stamp_review_exists
# ---------------------------------------------------------------------------


def check_pre_stamp_review_exists(repo_root: Path) -> tuple[str, str]:
    """Return ('ok'|'warn'|'fail', message). State-aware via Dimension 1.

    precheck   → ('ok', '')
    pre_stamp  + missing review file → ('warn', explanation)
    post_stamp + missing review file → ('fail', explanation)
    """
    state = _import_state()
    dim_1 = state.detect_dimension_1(repo_root)
    review = repo_root / "pre-stamp-review.md"

    if dim_1 == "precheck":
        return ("ok", "")

    if review.exists():
        return ("ok", "")

    if dim_1 == "pre_stamp":
        return (
            "warn",
            "pre-stamp-review.md missing in pre_stamp state; required before stamp",
        )

    # post_stamp without review.
    return (
        "fail",
        "pre-stamp-review.md missing in post_stamp state; "
        "the project has stamped artifacts but no adversarial-review record",
    )


# ---------------------------------------------------------------------------
# Parsing for load-bearing-assumptions.md
# ---------------------------------------------------------------------------


_ENTRY_RE = re.compile(
    r"^### (?P<id>\S+)(?:\s*[—-]\s*(?P<title>.+))?$",
    re.MULTILINE,
)
_FIELD_RE = re.compile(
    r"^\*\*(?P<key>[^*]+):\*\*\s*(?P<value>.*)$",
    re.MULTILINE,
)
_GATE_RE = re.compile(r"Gate\s*(\d+)", re.IGNORECASE)


def parse_assumptions_md(path: Path) -> list[dict]:
    """Parse goals/load-bearing-assumptions.md into a list of assumption dicts.

    Each dict has at least the parsed fields the file defines (id, title,
    Status, Resolution required before, etc.). Unknown fields are preserved.
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")

    # Split on `### <id>` boundaries.
    matches = list(_ENTRY_RE.finditer(text))
    entries: list[dict] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]

        entry: dict = {
            "id": match.group("id"),
            "title": (match.group("title") or "").strip(),
        }
        for fm in _FIELD_RE.finditer(body):
            key = fm.group("key").strip()
            value = fm.group("value").strip()
            entry[key] = value
        entries.append(entry)
    return entries


def _parse_deadline_gate(value: str) -> int | None:
    """Extract the gate number from a 'Resolution required before' value.
    Returns int N for 'Gate N', or None for sentinels like 'project closure'.
    """
    m = _GATE_RE.search(value)
    if not m:
        return None
    return int(m.group(1))


# ---------------------------------------------------------------------------
# R-4.2: check_load_bearing_assumptions_closed_at_gate
# ---------------------------------------------------------------------------


TERMINAL_STATES = {"verified", "falsified", "accepted-risk", "retired"}


def check_load_bearing_assumptions_closed_at_gate(
    repo_root: Path,
) -> list[str]:
    """Refuse ratification while any assumption due at or before current_gate
    is still `unverified`. Returns list of error messages; empty == OK.

    No assumptions file → returns []. (Projects without load-bearing
    assumptions don't trigger the check.)
    """
    state = _import_state()
    current_gate, _ = state.detect_phase_state(repo_root)
    path = repo_root / "goals" / "load-bearing-assumptions.md"
    if not path.exists():
        return []

    errors: list[str] = []
    for entry in parse_assumptions_md(path):
        status = entry.get("Status", "").strip().lower()
        deadline_text = entry.get("Resolution required before", "")
        deadline_gate = _parse_deadline_gate(deadline_text)

        if deadline_gate is None:
            continue
        if deadline_gate > current_gate:
            continue
        if status in TERMINAL_STATES:
            continue
        if status == "unverified" or status == "":
            errors.append(
                f"assumption {entry.get('id', '?')!r}: "
                f"Status={status or '(empty)'!r}, "
                f"Resolution required before Gate {deadline_gate}, "
                f"but current_gate = {current_gate}. Move to a terminal state "
                f"({', '.join(sorted(TERMINAL_STATES))}), or record accepted-risk "
                f"with a dated rationale and a future-gate review deadline. Per "
                f"ADR-0009, the original deadline must NOT be edited backward "
                f"without a scope-change ADR."
            )
        else:
            errors.append(
                f"assumption {entry.get('id', '?')!r}: "
                f"unknown Status {status!r}. Allowed: unverified, "
                f"{', '.join(sorted(TERMINAL_STATES))}."
            )

    return errors


# ---------------------------------------------------------------------------
# R-4.3: backward-deadline edit detection (advisory)
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess | None:
    """Run a git command in cwd. Return None on failure (no git, not a repo).

    v3.1: explicit encoding="utf-8", errors="replace" on text=True. Without
    these, `git log` output on Windows is decoded via locale.getpreferredencoding
    (cp1252), and the moment a commit message, author name, or diff payload
    contains a non-ASCII char (em-dash, accented name, an arrow) the call
    raises UnicodeDecodeError and the backward-edit scan dies instead of
    surfacing the warning it exists to surface.
    """
    try:
        return subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def detect_backward_deadline_edits(repo_root: Path) -> list[str]:
    """Scan git history for `Resolution required before:` edits that move the
    deadline to a LATER gate. Returns list of advisory warnings; empty == none.

    Skips silently if the project is not a git repo.
    """
    if not (repo_root / ".git").exists():
        # `.git` may also be a file (worktree); check `git rev-parse`.
        rev = _git(["rev-parse", "--git-dir"], repo_root)
        if rev is None:
            return []

    path = "goals/load-bearing-assumptions.md"
    log = _git(["log", "-p", "--", path], repo_root)
    if log is None or not log.stdout:
        return []

    # Walk diffs in reverse chronological order. For each `### <id>` we see,
    # track the most recent + and - lines for `Resolution required before:`.
    # If a + line moves the deadline to a higher Gate N than the immediately
    # preceding - line, warn.
    warnings: list[str] = []

    # Simpler but effective: split log into commits, then within each commit
    # find -line/+line pairs for 'Resolution required before' and compare.
    commits = re.split(r"^commit [0-9a-f]+", log.stdout, flags=re.MULTILINE)
    for commit_block in commits:
        # Find pairs of `-...Resolution required before...` and `+...Resolution required before...`
        # in this commit. They appear consecutively in unified diff hunks.
        lines = commit_block.splitlines()
        prev_deadline: int | None = None
        prev_id: str | None = None
        # Track entry id by scanning headers in diff context.
        for line in lines:
            # Diff context line for the entry header.
            id_match = re.match(r"^[ +-]### (\S+)", line)
            if id_match:
                prev_id = id_match.group(1)
            if line.startswith("-") and "Resolution required before" in line:
                m = _GATE_RE.search(line)
                if m:
                    prev_deadline = int(m.group(1))
            elif line.startswith("+") and "Resolution required before" in line:
                m = _GATE_RE.search(line)
                if m and prev_deadline is not None and int(m.group(1)) > prev_deadline:
                    new_deadline = int(m.group(1))
                    # v3.1: ASCII arrow (was U+2192 RIGHTWARDS ARROW). Even with
                    # preflight reconfiguring stdout to utf-8, downstream tools
                    # that consume these strings (CI logs, grep pipelines) may
                    # still be cp1252-bound. Keep advisory strings ASCII-safe.
                    warnings.append(
                        f"assumption {prev_id or '?'!r}: deadline edited "
                        f"backward (Gate {prev_deadline} -> Gate {new_deadline}). "
                        f"Per ADR-0009, backward-edits violate the discipline "
                        f"and should be ADR'd as scope changes if real."
                    )
                prev_deadline = None

    return warnings


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print("=== check_pre_stamp_review_exists ===")
    print(check_pre_stamp_review_exists(root))
    print("=== check_load_bearing_assumptions_closed_at_gate ===")
    for e in check_load_bearing_assumptions_closed_at_gate(root):
        print(f"[FAIL] {e}")
    print("=== detect_backward_deadline_edits ===")
    for w in detect_backward_deadline_edits(root):
        print(f"[WARN] {w}")
