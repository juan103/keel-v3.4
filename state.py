"""
Filesystem-inferred project state for v3 state-aware checks (SPINE.C, SPINE.D).

Two orthogonal dimensions:

  Dimension 1 — Pre-registration commitment state:
    precheck    no `keel-binding` block in any decisions/*.md
    pre_stamp   binding present; no stamp artifacts
    post_stamp  binding + (bundle/ non-empty OR *.ots outside tests/) OR commitment-artifact override

  Dimension 2 — Phase progression:
    current_gate    largest N such that goals/phase_N/RATIFIED exists; 0 if none
    active_phase    current_gate+1 if goals/phase_(current_gate+1)/REQUIREMENTS.md exists, else current_gate

Spec: ../proposal_v3.md "Filesystem state machine (specification for SPINE.C and SPINE.D)"
Refinements: v3-build/decisions/0010-state-battery-construction-and-bundle-signal.md
            (bundle/ must be non-empty to signal post_stamp).

Per ADR-0005, this module is the single source of truth for state inference. State-aware
preflight checks (Phase 4) consume `detect()` here; they do not re-implement detection.
"""

from __future__ import annotations

import re
from pathlib import Path

# Match the literal fenced opener `` ```keel-binding `` at the start of a line.
# `\s` after the fence allows newline immediately, or trailing whitespace before content.
_BINDING_RE = re.compile(r"^```keel-binding\b", re.MULTILINE)

# Match the GOALS.md ## Commitment-artifact section. The path is the first non-empty
# line after the heading. Stops at the next `## ` heading or end of file.
_COMMITMENT_RE = re.compile(
    r"^##[ \t]+Commitment-artifact[ \t]*\r?\n(.*?)(?=^##[ \t]|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _has_keel_binding(repo_root: Path) -> bool:
    """Any markdown file under decisions/ contains a fenced keel-binding block."""
    decisions = repo_root / "decisions"
    if not decisions.is_dir():
        return False
    for md in decisions.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _BINDING_RE.search(text):
            return True
    return False


def _is_in_tests_path(rel_parts: tuple[str, ...]) -> bool:
    """True if any path part is `tests` (any depth) or starts with `test_`."""
    return any(p == "tests" or p.startswith("test_") for p in rel_parts)


def _has_stamp_artifacts(repo_root: Path) -> bool:
    """post_stamp signal: bundle/ contains a non-scaffolding file (per ADR-0011),
    OR any *.ots outside tests/ and **/test_*."""
    bundle = repo_root / "bundle"
    if bundle.is_dir():
        # Non-empty (in the stamp-evidence sense) iff at least one file other than
        # .gitkeep exists at any depth. Per ADR-0011, .gitkeep is git-convention
        # scaffolding — its presence does not indicate a stamp event.
        for entry in bundle.rglob("*"):
            if entry.is_file() and entry.name != ".gitkeep":
                return True

    for ots in repo_root.rglob("*.ots"):
        try:
            rel = ots.relative_to(repo_root)
        except ValueError:
            continue
        if _is_in_tests_path(rel.parts):
            continue
        return True

    return False


def _commitment_artifact_path(repo_root: Path) -> Path | None:
    """Read goals/GOALS.md ## Commitment-artifact section. Return resolved Path or None.

    Rejects absolute paths and paths containing `..` (must stay within repo).
    """
    goals = repo_root / "goals" / "GOALS.md"
    if not goals.exists():
        return None
    try:
        text = goals.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    m = _COMMITMENT_RE.search(text)
    if not m:
        return None

    # First non-empty line of the section body.
    body = m.group(1)
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        # Reject Markdown formatting noise — take the first plain path-like line.
        # Reject absolute paths and parent-escapes.
        if line.startswith(("/", "\\")) or ".." in line:
            return None
        # Reject if it contains characters unlikely in a path
        # (bullets, table separators, etc.). Accept simple relative paths.
        if any(c in line for c in "|`*<>?\""):
            return None
        return repo_root / line
    return None


def _has_commitment_artifact(repo_root: Path) -> bool:
    """The commitment-artifact override signal: GOALS.md names a path AND it exists."""
    artifact = _commitment_artifact_path(repo_root)
    if artifact is None:
        return False
    return artifact.exists()


def detect_dimension_1(repo_root: Path) -> str:
    """Return 'precheck' | 'pre_stamp' | 'post_stamp'."""
    if not _has_keel_binding(repo_root):
        return "precheck"
    if _has_stamp_artifacts(repo_root) or _has_commitment_artifact(repo_root):
        return "post_stamp"
    return "pre_stamp"


def detect_phase_state(repo_root: Path) -> tuple[int, int]:
    """Return (current_gate, active_phase) inferred from RATIFIED markers and phase folders.

    current_gate: largest N such that goals/phase_N/RATIFIED exists; 0 if none.
    active_phase: current_gate+1 if goals/phase_<that>/REQUIREMENTS.md exists, else current_gate.
    """
    current_gate = 0
    for ratified in (repo_root / "goals").glob("phase_*/RATIFIED") if (repo_root / "goals").is_dir() else ():
        n_str = ratified.parent.name.removeprefix("phase_")
        try:
            n = int(n_str)
        except ValueError:
            continue
        if n > current_gate:
            current_gate = n

    next_phase = current_gate + 1
    if (repo_root / "goals" / f"phase_{next_phase}" / "REQUIREMENTS.md").exists():
        active_phase = next_phase
    else:
        active_phase = current_gate

    return (current_gate, active_phase)


def detect(repo_root: Path) -> dict:
    """Return the full state as a dict: dimension_1, current_gate, active_phase."""
    cg, ap = detect_phase_state(repo_root)
    return {
        "dimension_1": detect_dimension_1(repo_root),
        "current_gate": cg,
        "active_phase": ap,
    }


if __name__ == "__main__":
    import json
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print(json.dumps(detect(root), indent=2))
