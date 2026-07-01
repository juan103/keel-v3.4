"""ax-vacuous escape variant B: drop a first-outcome entry (other-clause escape).

Class: a first-outcome entry silently dropped across commits (its red evidence
  deleted) -- a member of the same hazard class as the vacuous-green flip.
Mechanism: 2nd commit removes the test_a (NODE_A) entry from the log with NO .py
  change.  The real detector reports "entry dropped" -> caught via the OTHER clause
  (_entry_dropped), NOT the vacuous-green anchor.

This is an OTHER-CLAUSE escape (survives surgical weakening):
  - _green_without_red: no flip marker (entry is gone, not flipped) -> False.
  - _entry_dropped: "entry dropped" reported -> True.
  - Under surgical weakening (_green_without_red -> False) _entry_dropped still
    fires -> True.  The variant SURVIVES weakening.

Provenance:
  Authoring identity: Claude as ax-vacuous rebuild implementer (Phase 3.5b).
  Inputs seen: scenario_spec.py (class definition, fixture structure), task brief.
  NOT derived from reading named_check.py internals.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations

import importlib.util as _ilu
from pathlib import Path


def _load_gitutil():
    path = Path(__file__).resolve().parent.parent / "_gitutil.py"
    spec = _ilu.spec_from_file_location("ax_vacuous_gitutil_variant_b", path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mutator(tree: Path) -> None:
    """Drop the test_a entry from the log with no code change (other-clause escape)."""
    gu = _load_gitutil()
    tree = Path(tree)
    log = gu.read_log(tree)
    log.pop(gu.NODE_A, None)
    gu.write_log(tree, log)
    gu.commit_log_change(tree, "remove stale test_a entry", also_code=False)
