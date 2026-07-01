"""F1 -- the differential-observability gate for ax-runtime-role (Phase 3.5a/3.5b).

This is the trio's FIRST KILL-GATE.  F1 is a 4-cell truth table plus 3 controls.

Phase 3.5b, Task 1: the 4-cell + 3-control logic was lifted into the REUSABLE
`f1_harness` module (so Tasks 2-8 instantiate it in one line).  This file is now a
THIN binding of the ax-runtime-role scenario pieces to the harness: each test
delegates to one F1 phase (assert_f1 composes the same four phases).  The full
one-liner is exercised by tests/kit/adversarial/test_f1_harness.py.

What F1 PROVES (and only this):
  - SENSITIVITY: `caught` is True for the escape tree under the intact check and
    False when the class clause is surgically removed (theatre is excluded).
  - SPECIFICITY: `caught` is False on a clean tree and on a benign-noisy tree under
    the intact check (no always-fires / brittle over-trigger).
  - EXECUTION-BINDING: every cell verdict is bound to a content-addressed execution
    trace that an independent replicator reproduces byte-identically (fabrication
    without execution is excluded).

What F1 does NOT prove (explicit residues, deferred to Phase 4):
  - live faithfulness of the named-check observable to the REAL escape class,
  - that the scenario provokes the real live escape vector,
  - observable_faithfulness / any detector-recall number.
These are UNVALIDATED(Phase4) and are asserted nowhere here.

The required 4-cell table for ax-runtime-role (a genuine harness yields exactly this):
    | tree   | named check | caught |
    | escape | intact      | True   |
    | escape | weakened    | False  |
    | clean  | intact      | False  |
    | noisy  | intact      | False  |

ASCII-only. Stdlib only (test-side).
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

import f1_harness  # noqa: E402  (the reusable F1 gate under exercise)

_AX_DIR = Path(__file__).resolve().parent / "ax-runtime-role"
_WIT_DIR = _AX_DIR / "retained_witnesses"


# ---------------------------------------------------------------------------
# Module loader (the ax-runtime-role dir is hyphenated -> not importable)
# ---------------------------------------------------------------------------

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scn_mod = _load("ax_t6_scenario_spec", _AX_DIR / "scenario_spec.py")
SCENARIO = _scn_mod.AX_RUNTIME_ROLE

_weak = _load("ax_t6_weakenings", _AX_DIR / "weakenings.py")
INTACT = _weak.intact
SURGICAL_WEAK = _weak.surgical_weak
GLOBAL_DISABLE = _weak.global_disable

# The held-out variant caught via the CLASS predicate (must flip under weakening).
CLASS_VARIANT = _load(
    "ax_t6_variant_a", _AX_DIR / "escape_variants" / "variant_a.py"
).mutator

_ANCHOR = "_author_field_unattested"


# ---------------------------------------------------------------------------
# F1 -- thin per-phase bindings of ax-runtime-role to the reusable harness.
# (assert_f1 composes exactly these four phases; see test_f1_harness.py for the
# full one-liner.)
# ---------------------------------------------------------------------------

def test_F1_truth_table_ax_runtime_role(tmp_path):
    """F1 headline: run_scenario yields exactly (True, False, False, False)."""
    f1_harness.assert_headline_4cell(
        SCENARIO, intact=INTACT, surgical_weak=SURGICAL_WEAK, work_dir=tmp_path
    )


def test_F1_control1_surgical_weakening_admissible(tmp_path):
    """C1: the weakening is surgical, class-flipping, witness-preserving (+ neg control)."""
    f1_harness.assert_control1_surgical_admissible(
        SCENARIO,
        intact=INTACT,
        surgical_weak=SURGICAL_WEAK,
        global_disable=GLOBAL_DISABLE,
        predicate_anchor=_ANCHOR,
        class_variant=CLASS_VARIANT,
        witnesses_dir=_WIT_DIR,
        work_dir=tmp_path,
    )


def test_F1_control2_invariance_under_relocation(tmp_path):
    """C2: verdict is INVARIANT under consistent relocation (throw = misroute)."""
    f1_harness.assert_control2_relocation_invariance(
        SCENARIO, intact=INTACT, witnesses_dir=_WIT_DIR, work_dir=tmp_path
    )


def test_F1_control3_execution_binding(tmp_path):
    """C3: each cell verdict is trace-bound; replicate() reproduces all 4 byte-identically."""
    f1_harness.assert_control3_execution_binding(
        SCENARIO, intact=INTACT, surgical_weak=SURGICAL_WEAK, work_dir=tmp_path
    )
