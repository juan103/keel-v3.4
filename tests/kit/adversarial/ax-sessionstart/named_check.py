"""ax-sessionstart: named check (class invariant) for hz-sessionstart-skipped.

Public: run(tree: Path) -> bool
  True iff tree exhibits the escape class: .claude/settings.json is missing or
  mangles the SessionStart 'preflight.py --compliance' hook (and/or the PreToolUse
  accepted-ADR guard), so the compliance/guard hooks are not wired.

Faithfully RE-EXPRESSES (does NOT import) the REAL detection of
preflight.check_hooks_installed -- because that detection has no importable helper
(see below). It inspects the SAME
file (.claude/settings.json) with the SAME JSON-path predicates (a SessionStart
hook whose command contains 'preflight.py --compliance'; a PreToolUse Edit|Write
group whose hook command contains 'protect_adrs.py').  That detection is
self-contained JSON inspection -- preflight.check_hooks_installed does NOT delegate
to a reusable kit helper (its logic is inline, bound to module-global ROOT/STRICT),
so the faithful wrapping re-expresses the exact predicate over an arbitrary tree.
It imports NOTHING non-stdlib, which also makes it invariant under Control-2
relocation by construction (no kit-module path to re-resolve under relocation).

.claude/settings.json is a fixture file that SURVIVES the harness projection
(it is not in projection.EXCLUDE_RULES), so this observable runs clean on the
projected tree.

CLASS PREDICATE ANCHOR: _sessionstart_hook_missing(settings)
  The class-discriminating clause for hz-sessionstart-skipped: no SessionStart
  hook runs 'preflight.py --compliance' (the session-start compliance block is
  skipped).  The canonical escape removes or mangles that hook.

Other clause: _pretooluse_guard_missing(settings)
  A SEPARATE top-level clause: no PreToolUse Edit|Write hook runs 'protect_adrs.py'
  (the accepted-ADR guard).  Structurally separate so the predicate-weakening is
  AST-localizable and a retained witness can be caught via this non-predicate
  clause.

mutation_definition: PROVISIONAL -- hz-sessionstart-skipped is a PENDING Tier-1
hazard; its escape-class definition may still evolve.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations
import json
from pathlib import Path


def _sessionstart_hook_missing(settings: dict) -> bool:
    """CLASS PREDICATE ANCHOR.

    True iff .claude/settings.json does NOT wire a SessionStart hook whose command
    runs 'preflight.py --compliance'.  Mirrors the SessionStart half of
    preflight.check_hooks_installed exactly: the canonical hz-sessionstart-skipped
    escape removes or mangles that hook so the CLAUDE.md section-0 compliance block
    never fires at session start.
    """
    hooks = (settings.get("hooks") or {})
    ss_cmds = [
        h.get("command", "")
        for grp in hooks.get("SessionStart", [])
        for h in (grp.get("hooks") or [])
    ]
    return not any("preflight.py --compliance" in c for c in ss_cmds)


def _pretooluse_guard_missing(settings: dict) -> bool:
    """Other clause: True iff the PreToolUse accepted-ADR guard is not wired.

    True iff .claude/settings.json has no PreToolUse group whose matcher targets
    Edit|Write and whose hook command runs 'protect_adrs.py'.  Mirrors the
    PreToolUse half of preflight.check_hooks_installed exactly.  Caught
    independently of the SessionStart anchor so a guard-only escape survives a
    SessionStart-anchor weakening (the C1 non-predicate-clause mechanism).
    """
    hooks = (settings.get("hooks") or {})
    pt_ok = any(
        ("Edit" in (grp.get("matcher", "")) or "Write" in (grp.get("matcher", "")))
        and any("protect_adrs.py" in h.get("command", "") for h in (grp.get("hooks") or []))
        for grp in hooks.get("PreToolUse", [])
    )
    return not pt_ok


def run(tree: Path) -> bool:
    """True iff tree exhibits the escape class (compliance/guard hooks not wired)."""
    tree = Path(tree)
    settings_path = tree / ".claude" / "settings.json"
    if not settings_path.exists():
        return True  # settings.json missing -> hooks not installed (escape)
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except ValueError:
        return True  # mangled JSON -> hooks not wired (escape)
    if _sessionstart_hook_missing(settings):
        return True
    if _pretooluse_guard_missing(settings):
        return True
    return False
