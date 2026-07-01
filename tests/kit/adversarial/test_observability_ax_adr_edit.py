"""F1 -- the differential-observability gate for ax-adr-edit (Phase 3.5b, PROVISIONAL).

A thin binding of the ax-adr-edit scenario pieces to the reusable F1 harness:
the whole 4-cell truth table + 3 controls is exercised by one assert_f1(...) call.

Scenario: hz-adr-silent-edit (PENDING Tier-1 hazard; mutation_definition=PROVISIONAL)
  An ACCEPTED ADR's committed body is changed outside the ## Errata section or
  the legitimate Status transition (accepted->superseded) AFTER its acceptance commit.
  Detection wraps adr_guard.detect_adr_mutations (git log/show comparison).

GIT FIXTURE NOTE
  The scenario fixture creates a REAL git repo (subprocess git init + commit) so
  the named check can use adr_guard._acceptance_commit / _git show.  See
  scenario_spec.PROJECTION_NOTE for determinism design (fixed GIT_AUTHOR_DATE,
  deleted .git/index and .git/logs/ post-commit).

Named check clauses:
  CLASS PREDICATE ANCHOR: _immutable_body_changed -- catches mutations to the
    non-mutable, non-Consequences body (e.g. ## Context, ## Decision).
  OTHER CLAUSE:           _consequences_changed   -- catches mutations to the
    ## Consequences section; survives the surgical weakening.

What F1 PROVES (and only this): SENSITIVITY (caught True for the escape under
the intact check, False when _immutable_body_changed is surgically removed),
SPECIFICITY (caught False on clean + benign-noisy under the intact check),
EXECUTION-BINDING (each verdict bound to a content-addressed trace an independent
replicator reproduces byte-identically).  Live faithfulness / escape-vector
provocation / observable-faithfulness are UNVALIDATED(Phase4), asserted nowhere.

The required 4-cell table for ax-adr-edit:
    | tree   | named check | caught |
    | escape | intact      | True   |
    | escape | weakened    | False  |
    | clean  | intact      | False  |
    | noisy  | intact      | False  |

ASCII-only.  Stdlib only (test-side).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# keel_v3.4/ root is parents[3] from this file:
#   parents[0]=adversarial parents[1]=kit parents[2]=tests parents[3]=keel_v3.4
_KIT_ROOT = str(Path(__file__).resolve().parents[3])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import f1_harness  # noqa: E402  (the reusable F1 gate)

_AX_DIR = Path(__file__).resolve().parent / "ax-adr-edit"
_WIT_DIR = _AX_DIR / "retained_witnesses"


# ---------------------------------------------------------------------------
# Module loader (the ax-adr-edit dir is hyphenated -> not importable as a pkg)
# ---------------------------------------------------------------------------

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scn_mod = _load("ax_adr_edit_scenario_spec", _AX_DIR / "scenario_spec.py")
SCENARIO = _scn_mod.AX_ADR_EDIT

_weak = _load("ax_adr_edit_weakenings", _AX_DIR / "weakenings.py")
INTACT = _weak.intact
SURGICAL_WEAK = _weak.surgical_weak
GLOBAL_DISABLE = _weak.global_disable

# The held-out variant caught via the CLASS predicate (must flip under weakening).
# variant_a changes ## Decision -> caught by _immutable_body_changed -> flips False
# when the class-predicate anchor is surgically neutralized.
CLASS_VARIANT = _load(
    "ax_adr_edit_variant_a", _AX_DIR / "escape_variants" / "variant_a.py"
).mutator

_ANCHOR = "_immutable_body_changed"


# ---------------------------------------------------------------------------
# F1 -- the full 4-cell truth table + 3 controls via the reusable harness.
# ---------------------------------------------------------------------------

def test_F1_ax_adr_edit(tmp_path):
    """F1 (4-cell table + 3 controls) for ax-adr-edit via the reusable harness.

    PROVISIONAL: hz-adr-silent-edit is a PENDING Tier-1 hazard.  The F1 gate
    exercises the git-fixture branch of the detection surface.
    """
    f1_harness.assert_f1(
        SCENARIO,
        intact=INTACT,
        surgical_weak=SURGICAL_WEAK,
        global_disable=GLOBAL_DISABLE,
        predicate_anchor=_ANCHOR,
        class_variant=CLASS_VARIANT,
        witnesses_dir=_WIT_DIR,
        work_dir=tmp_path,
    )
