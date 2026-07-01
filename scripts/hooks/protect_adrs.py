"""Claude Code PreToolUse hook: ask the human before an agent edits an
accepted ADR (v3.3).

Wired in .claude/settings.json against Edit|Write. Claude Code pipes the
pending tool call as JSON on stdin; if the target file is an existing
decisions/**/*.md whose Status line says accepted (or superseded), the
hook returns permissionDecision "ask" so the human ratifies the edit
explicitly — the interactive half of the ADR-immutability guard
(preflight's check_adr_immutability via adr_guard.py is the blocking,
after-the-fact half).

Deliberately allowed without prompting:
  - creating a NEW ADR (target file does not exist yet);
  - editing a proposed ADR (not yet accepted — still mutable);
  - decisions/0000-template.md (a template, not a decision);
  - anything outside decisions/.

A prompted edit is not necessarily wrong: adding an ## Errata line and
flipping Status to superseded are legitimate. The prompt exists so a
human sees the edit happen, instead of discovering it at the next
preflight failure.

Exit code is always 0; a hook crash must never block unrelated edits.
"""

import json
import re
import sys
from pathlib import Path

_ACCEPTED_RE = re.compile(
    r"^\*\*Status:\*\*\s*(accepted|superseded)\b", re.MULTILINE | re.IGNORECASE
)


def _read_stdin_json():
    """Claude Code writes raw UTF-8 JSON. Windows shells used for manual
    testing (PowerShell 5.1 pipes) may prepend a BOM or re-encode to
    UTF-16; tolerate both (kit Windows-hardening convention, v3.1).
    """
    raw = sys.stdin.buffer.read()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16", errors="replace")
    else:
        text = raw.decode("utf-8-sig", errors="replace")
    return json.loads(text)


def _accepted_adr_target(tool_input, project_dir):
    """Return the repo-relative Path of the targeted file iff it is an existing,
    accepted-or-superseded decisions/*.md (not the template); else None. Shared by
    should_block (the pure predicate) and main (which needs the path for its message)."""
    file_path = (tool_input or {}).get("file_path") or ""
    if not file_path:
        return None
    project = Path(project_dir) if project_dir else Path.cwd()
    target = Path(file_path)
    if not target.is_absolute():
        target = project / target
    try:
        rel = target.resolve().relative_to(project.resolve())
    except (ValueError, OSError):
        return None
    if not rel.parts or rel.parts[0] != "decisions" or rel.suffix != ".md":
        return None
    if rel.name == "0000-template.md":
        return None
    if not target.exists():
        return None  # new ADR being created -- allowed
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if _ACCEPTED_RE.search(text):
        return rel
    return None


def should_block(tool_input, project_dir):
    """Pure predicate (contract: falsy_bool). True iff this tool call edits an
    existing accepted/superseded ADR -- the raw-tool-call form the kit must not let
    an agent change silently. Returns False for new ADRs, drafts, the template, and
    non-decisions files. NOTE (1c-B, behavior-preserving): superseded-content vs
    accepted->draft / superseded->accepted resurrection are NOT yet distinguished;
    that lifecycle taxonomy is fixed in Phase 1c-C (ADR-0003, trio F-0)."""
    return _accepted_adr_target(tool_input, project_dir) is not None


def main():
    try:
        data = _read_stdin_json()
    except (ValueError, OSError):
        return
    tool_input = data.get("tool_input") or {}
    project = data.get("cwd") or str(Path.cwd())
    rel = _accepted_adr_target(tool_input, project)
    if rel is None:
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"{rel.as_posix()} is an ACCEPTED ADR -- immutable per "
                f"CLAUDE.md Sec. 7. Legitimate edits: an ## Errata addition "
                f"(typo-class only) or a Status flip to 'superseded by "
                f"ADR-NNNN'. Substantive changes need a new superseding "
                f"ADR instead. Approve only if this edit is one of those."
            ),
        }
    }))


if __name__ == "__main__":
    main()
    sys.exit(0)
