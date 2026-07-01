"""ax-vacuous escape variant A: backdate a DIFFERENT test (class-predicate escape).

Class: a recorded first-outcome flipped failed->passed across commits with no code
  change (vacuous green).
Mechanism: 2nd commit flips test_b (NODE_B) failed->passed in the log with NO .py
  change -- a different entry than the reference mutator (which flips test_a).  The
  real detector reports "flip failed->passed without code change" -> caught via the
  CLASS PREDICATE clause (_green_without_red).

This is a CLASS-PREDICATE escape:
  - Caught by _green_without_red (intact) -> True.
  - Under surgical weakening (_green_without_red -> False) no other clause fires
    (no entry dropped) -> overall False.  The variant FLIPS True->False.

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
    spec = _ilu.spec_from_file_location("ax_vacuous_gitutil_variant_a", path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mutator(tree: Path) -> None:
    """Flip test_b failed->passed with no code change (class-predicate escape)."""
    gu = _load_gitutil()
    tree = Path(tree)
    log = gu.read_log(tree)
    log[gu.NODE_B]["first"] = "passed"
    gu.write_log(tree, log)
    gu.commit_log_change(tree, "backdate test_b to passing", also_code=False)
