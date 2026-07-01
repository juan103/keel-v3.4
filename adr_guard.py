"""
ADR immutability guard (v3.3).

CLAUDE.md §7 has declared accepted ADRs immutable since v2, with two
legitimate exceptions added along the way:

  - the `## Errata` appendix (v3.1) for typo-class corrections;
  - the `**Status:**` line transitioning from `accepted` to
    `superseded by ADR-NNNN` when a later ADR supersedes this one.

Until v3.3 the rule was prose-only. That made it the most load-bearing
unguarded rule in the kit: binding metadata, the stamp bundle, and the
fork protocol all rest on the ratified record not changing underneath
them, yet nothing detected a silent edit to decisions/NNNN-*.md. The kit
already used git history to guard the assumptions ledger
(assumptions.detect_backward_deadline_edits); this module applies the
same pattern to ADRs, as a blocking check rather than an advisory one —
a mutated ratified record is never legitimate.

Mechanism: for every decisions/**/*.md whose working-tree Status is
accepted (or superseded — a superseded ADR was accepted first and stays
immutable), find the ACCEPTANCE COMMIT (the first commit in which the
file's Status line said accepted/superseded), reconstruct that committed
text, strip the legitimately-mutable parts from both versions (Errata
section, Status line), normalize line endings, and compare. Any
difference is a mutation of the ratified record.

Skip behavior (mirrors detect_backward_deadline_edits):
  - not a git repo / git unavailable        -> [] (silent skip)
  - ADR not yet tracked or never committed
    with accepted status                    -> skipped (the guard starts
                                               protecting an ADR at its
                                               first accepted commit)
  - decisions/0000-template.md              -> skipped (it is a template,
                                               not a decision)

The kit's `.claude/settings.json` PreToolUse hook
(scripts/hooks/protect_adrs.py) is the interactive companion: it asks
the human before a coding agent edits an accepted ADR at all. This
module is the after-the-fact backstop that catches what the hook misses
(edits made outside the agent, hooks disabled, etc.).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# Matches the Status line of an ACCEPTED (or superseded) ADR. The template's
# own line ("**Status:** proposed | accepted | superseded by ADR-NNNN")
# starts with "proposed" and does not match.
_ACCEPTED_RE = re.compile(
    r"^\*\*Status:\*\*\s*(accepted|superseded)\b", re.MULTILINE | re.IGNORECASE
)

_STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*.*$", re.MULTILINE)

# The Errata section: from `## Errata` to the next `## ` heading or EOF.
_ERRATA_RE = re.compile(r"^##[ \t]+Errata[ \t]*\r?\n.*?(?=^##[ \t]|\Z)",
                        re.MULTILINE | re.DOTALL)


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess | None:
    """Run a git command in cwd. Return None on failure (no git, not a repo).

    encoding="utf-8", errors="replace" per the v3.1 Windows cp1252 hardening
    (assumptions._git has the full rationale).
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


def _is_git_repo(repo_root: Path) -> bool:
    if (repo_root / ".git").exists():
        return True
    # `.git` may also be absent in a worktree layout; ask git itself.
    return _git(["rev-parse", "--git-dir"], repo_root) is not None


def _normalize(text: str) -> str:
    """Normalize for comparison: unify line endings, strip trailing
    whitespace per line, drop leading/trailing blank lines. CRLF working
    trees vs LF blobs must not produce false mutation reports.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _strip_mutable(text: str) -> str:
    """Remove the legitimately-mutable parts before comparison:
    the `## Errata` section and the `**Status:**` line.
    """
    text = _ERRATA_RE.sub("", text)
    text = _STATUS_LINE_RE.sub("", text)
    return _normalize(text)


def _acceptance_commit(repo_root: Path, rel_posix: str) -> str | None:
    """First commit in which the file's Status line said accepted/superseded.

    Returns the commit hash, or None if the file has never been committed
    in an accepted state.
    """
    log = _git(["log", "--format=%H", "--reverse", "--", rel_posix], repo_root)
    if log is None or not log.stdout.strip():
        return None
    for commit in log.stdout.split():
        show = _git(["show", f"{commit}:{rel_posix}"], repo_root)
        if show is None:
            continue  # file absent in this commit (e.g., renamed later)
        if _ACCEPTED_RE.search(show.stdout):
            return commit
    return None


def detect_adr_mutations(repo_root: Path) -> list[str]:
    """Return error messages for every accepted ADR whose content changed
    since its acceptance commit outside `## Errata` / the Status line.
    Empty list == OK. Silent skip when not a git repo.
    """
    decisions = repo_root / "decisions"
    if not decisions.is_dir():
        return []
    if not _is_git_repo(repo_root):
        return []

    errors: list[str] = []
    for md in sorted(decisions.rglob("*.md")):
        if md.name == "0000-template.md":
            continue
        try:
            current = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not _ACCEPTED_RE.search(current):
            continue  # proposed ADRs are still mutable

        rel_posix = md.relative_to(repo_root).as_posix()
        commit = _acceptance_commit(repo_root, rel_posix)
        if commit is None:
            continue  # accepted in working tree, never committed accepted

        show = _git(["show", f"{commit}:{rel_posix}"], repo_root)
        if show is None:
            continue

        if _strip_mutable(current) != _strip_mutable(show.stdout):
            # ASCII-only advisory string (v3.1 convention): standalone runs
            # print to a possibly cp1252-bound console without preflight's
            # utf-8 stdout reconfigure.
            errors.append(
                f"{rel_posix}: content changed since acceptance commit "
                f"{commit[:12]} outside the mutable parts (## Errata, Status "
                f"line). Accepted ADRs are immutable (CLAUDE.md section 7). "
                f"Typo-class fixes go in ## Errata; substantive changes need "
                f"a new superseding ADR; if this edit was never ratified, "
                f"revert it: git checkout {commit[:12]} -- {rel_posix}"
            )

    return errors


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    errs = detect_adr_mutations(root)
    if errs:
        for e in errs:
            print(f"[FAIL] {e}")
        sys.exit(1)
    print("[OK] no accepted-ADR mutations detected")
