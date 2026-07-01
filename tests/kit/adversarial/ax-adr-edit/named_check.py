"""ax-adr-edit: named check (class invariant) for hz-adr-silent-edit.

Public: run(tree: Path) -> bool
  True iff tree exhibits the escape class: an ACCEPTED ADR's committed body
  changed outside the ## Errata section or the legitimate Status transition
  (accepted -> superseded) after its acceptance commit.

Wraps real detection (adr_guard helpers). Returns bool, never raises.

CLASS PREDICATE ANCHOR: _immutable_body_changed(acceptance_text, current_text)
  The class-discriminating clause.  Catches mutations to the non-mutable
  ADR body (all sections EXCEPT ## Errata, Status line, and ## Consequences).
  The canonical escape: an agent edits ## Context or ## Decision after
  acceptance.  Uses adr_guard._strip_mutable (strips ## Errata + Status line)
  then additionally strips ## Consequences so that Consequences-only edits
  are handled exclusively by the other clause.

Other clause: _consequences_changed(acceptance_text, current_text)
  Catches mutations to the ## Consequences section specifically.
  Structurally separate (different top-level function) so Task-6
  predicate-weakening is AST-localizable to _immutable_body_changed alone.
  An agent that edits ## Consequences after acceptance exhibits the same
  hazard class; this clause catches that path.  A Consequences-only edit
  survives the surgical weakening of the class-predicate anchor.

ACCEPTANCE TEXT SOURCE
  If tree is a real git repo (.git/ exists): uses adr_guard helpers
  (_acceptance_commit, _git show) to retrieve the acceptance-commit content.
  If tree has a .adr-acceptance-snapshots.json sidecar (retained witnesses):
  reads the acceptance text from the sidecar.  Returns None (skip) if
  neither source is available.

ASCII-only.  Stdlib + adr_guard.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# keel_v3.4/ root is parents[4] from this file.
_KIT_ROOT = str(Path(__file__).resolve().parents[4])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

try:
    import adr_guard
except ImportError as _e:
    raise ImportError(
        f"adr_guard not found on sys.path (kit root: {_KIT_ROOT!r}): {_e}"
    ) from _e

# Sidecar file used by retained witnesses (non-git trees).
_SNAPSHOT_FILE = ".adr-acceptance-snapshots.json"

# Regex: ## Consequences section from heading to next ## heading or EOF.
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
    """CLASS PREDICATE ANCHOR.

    True iff the immutable ADR body (excluding ## Errata, ## Consequences, and
    the Status line) changed between acceptance_text and current_text.

    Mechanism:
      1. adr_guard._strip_mutable removes ## Errata section + Status line.
      2. _strip_consequences additionally removes ## Consequences so that a
         Consequences-only edit is NOT caught here (it falls to the other clause).
      3. adr_guard._normalize unifies line endings and trims trailing whitespace.
      4. Returns True iff the normalized stripped bodies differ.

    Class-discriminating for hz-adr-silent-edit: any agent edit to ## Context,
    ## Decision, or any other non-mutable, non-Consequences section fires here.
    """
    a = adr_guard._normalize(
        _strip_consequences(adr_guard._strip_mutable(acceptance_text))
    )
    c = adr_guard._normalize(
        _strip_consequences(adr_guard._strip_mutable(current_text))
    )
    return a != c


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
            continue  # proposed/draft ADRs are mutable

        rel_posix = md.relative_to(tree).as_posix()
        acceptance_text = _get_acceptance_text(tree, rel_posix)
        if acceptance_text is None:
            continue  # never committed accepted; guard starts at first accepted commit

        if _immutable_body_changed(acceptance_text, current_text):
            return True
        if _consequences_changed(acceptance_text, current_text):
            return True

    return False
