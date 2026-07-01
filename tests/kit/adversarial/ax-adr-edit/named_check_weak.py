"""ax-adr-edit: SURGICALLY WEAKENED twin of named_check.py (F1 Control 1).

This module is a verbatim copy of named_check.py EXCEPT for the body of the
class-predicate anchor _immutable_body_changed, which is neutralized to
`return False`.  Every other top-level function (_strip_consequences,
_extract_consequences, _get_acceptance_text, _consequences_changed, run) is
byte-identical, so the AST diff between named_check.py and this file is
confined to the single anchor function.

Effect: the 'immutable ADR body changed' CLASS is no longer caught, but the
_consequences_changed clause still fires, so a Consequences-only mutation and
the other-clause retained witness remain caught.  This is the surgical
weakening that makes the F1 cell (escape, weakened) -> caught=False while
(witness_2, weakened) -> caught=True (survives).

This file is NOT a real check.  It exists only as the Control-1 weakening twin.

ASCII-only.  Stdlib + adr_guard.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_KIT_ROOT = str(Path(__file__).resolve().parents[4])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

try:
    import adr_guard
except ImportError as _e:
    raise ImportError(
        f"adr_guard not found on sys.path (kit root: {_KIT_ROOT!r}): {_e}"
    ) from _e

_SNAPSHOT_FILE = ".adr-acceptance-snapshots.json"

_CONSEQUENCES_RE = re.compile(
    r"^##[ \t]+Consequences[ \t]*\r?\n.*?(?=^##[ \t]|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _strip_consequences(text: str) -> str:
    """Remove the ## Consequences section (heading + body) from text."""
    return _CONSEQUENCES_RE.sub("", text)


def _extract_consequences(text: str) -> str:
    """Return the ## Consequences section (heading + body), or '' if absent."""
    m = _CONSEQUENCES_RE.search(text)
    return m.group(0) if m else ""


def _get_acceptance_text(tree: Path, rel_posix: str) -> str | None:
    """Return the ADR text as of its acceptance commit.

    Mode 1 -- real git repo (.git/ directory at tree root):
      Uses adr_guard._acceptance_commit / _git show.
      Returns None if the ADR was never committed in an accepted state.
      NOTE: checks (tree / ".git").is_dir() rather than adr_guard._is_git_repo
      because _is_git_repo also traverses parent directories (worktree support),
      which would incorrectly find the main project's git repo for witness trees.
      We want git mode ONLY when the fixture's OWN repo is rooted at tree.

    Mode 2 -- sidecar snapshot (.adr-acceptance-snapshots.json present):
      Used by retained witnesses that cannot carry .git/ in the main repo.
      Returns the snapshot entry for rel_posix, or None if absent.
    """
    if (tree / ".git").is_dir():
        commit = adr_guard._acceptance_commit(tree, rel_posix)
        if commit is None:
            return None
        show = adr_guard._git(["show", f"{commit}:{rel_posix}"], tree)
        if show is None:
            return None
        return show.stdout

    # Sidecar fallback for retained witnesses.
    snap_path = tree / _SNAPSHOT_FILE
    if not snap_path.exists():
        return None
    try:
        data = json.loads(snap_path.read_text(encoding="utf-8"))
        return data.get(rel_posix)
    except (OSError, ValueError):
        return None


def _immutable_body_changed(acceptance_text: str, current_text: str) -> bool:
    """SURGICALLY WEAKENED CLASS PREDICATE ANCHOR.

    The intact anchor returns True iff the non-mutable, non-Consequences body
    changed between acceptance_text and current_text.  This weakened twin
    returns False unconditionally, so the 'immutable body changed' CLASS is no
    longer caught.  The change is confined to THIS function; _consequences_changed
    and run are untouched.
    """
    return False


def _consequences_changed(acceptance_text: str, current_text: str) -> bool:
    """Other clause: True iff the ## Consequences section changed.

    Extracts just the ## Consequences section from each text and compares.
    A Consequences-only edit survives the surgical weakening of the class-
    predicate anchor (_immutable_body_changed -> False), so this clause is
    the retained-witness / C1-leg-(c) mechanism.

    Covers: ## Consequences prose was reworded, section was removed, or a
    new Consequences-like block was injected with different content.
    """
    a = adr_guard._normalize(_extract_consequences(acceptance_text))
    c = adr_guard._normalize(_extract_consequences(current_text))
    return a != c


def run(tree: Path) -> bool:
    """True iff tree exhibits the escape class.

    Iterates over accepted ADRs in decisions/, retrieves their acceptance
    text (via git or sidecar), and applies both clauses.  Returns True as
    soon as any clause fires on any ADR.
    """
    tree = Path(tree)
    decisions = tree / "decisions"
    if not decisions.is_dir():
        return False

    for md in sorted(decisions.rglob("*.md")):
        if md.name == "0000-template.md":
            continue
        try:
            current_text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not adr_guard._ACCEPTED_RE.search(current_text):
            continue

        rel_posix = md.relative_to(tree).as_posix()
        acceptance_text = _get_acceptance_text(tree, rel_posix)
        if acceptance_text is None:
            continue

        if _immutable_body_changed(acceptance_text, current_text):
            return True
        if _consequences_changed(acceptance_text, current_text):
            return True

    return False
