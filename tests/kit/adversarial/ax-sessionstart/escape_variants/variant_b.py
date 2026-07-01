"""ax-sessionstart escape variant B: a removed PreToolUse ADR guard (OTHER clause).

Class: a .claude/settings.json that fails to wire a required hook.
Mechanism: removes the PreToolUse Edit|Write 'protect_adrs.py' guard group, so the
  accepted-ADR immutability guard is no longer wired.  Caught via the OTHER clause
  (_pretooluse_guard_missing), NOT the SessionStart anchor, so it SURVIVES the
  SessionStart-anchor surgical weakening (the C1 non-predicate-survivor mechanism).
  The SessionStart compliance hook is untouched.

Provenance:
  Authoring identity: Claude (Phase 3.5b implementer).
  Inputs seen: scenario_spec.py (clean settings + class definition), task brief.
  NOT derived from reading named_check.py internals.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations
import json
from pathlib import Path

_SETTINGS = ".claude/settings.json"


def mutator(tree: Path) -> None:
    """Remove the PreToolUse ADR guard so the accepted-ADR guard is unwired."""
    path = Path(tree) / ".claude" / "settings.json"
    settings = json.loads(path.read_text(encoding="utf-8"))
    hooks = settings.get("hooks") or {}
    hooks.pop("PreToolUse", None)
    settings["hooks"] = hooks
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
