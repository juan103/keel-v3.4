"""F1 -- the differential-observability gate for ax-frame-validity (Phase 3.5b).

A thin binding of the ax-frame-validity scenario pieces to the reusable F1 harness:
the whole 4-cell truth table + 3 controls is exercised by one assert_f1(...) call.

Scenario: hz-frame-validity-unexpressible. The escape is a frame_validity binding
block where author_verdict is null or empty (check_frame_validity_audit would flag
it). The named check WRAPS binding.extract_keel_binding_blocks and reads ONLY
decisions/*.md + the audit artifact referenced by audit_artifact -- both survive
the harness projection, so the check runs clean on the projected tree.

CLASS PREDICATE ANCHOR: _author_verdict_null (ax-frame-validity/named_check.py)
  Surgical weakening makes F1 cell (escape, weakened) -> caught=False.
  The _audit_artifact_missing other-clause retained witness SURVIVES the weakening.

What F1 PROVES (and only this): SENSITIVITY (caught True for the escape under the
intact check, False when the class-predicate clause is surgically removed),
SPECIFICITY (caught False on clean + benign-noisy under the intact check),
EXECUTION-BINDING (each verdict bound to a content-addressed trace an independent
replicator reproduces byte-identically). Live faithfulness / escape-vector
provocation / observable-faithfulness are UNVALIDATED(Phase4), asserted nowhere.

ASCII-only.  Stdlib only (test-side).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# keel_v3.4/ root is parents[3] from this file:
#   parents[0]=adversarial  parents[1]=kit  parents[2]=tests  parents[3]=keel_v3.4
_KIT_ROOT = str(Path(__file__).resolve().parents[3])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import f1_harness  # noqa: E402  (the reusable F1 gate under exercise)

_AX_DIR = Path(__file__).resolve().parent / "ax-frame-validity"
_WIT_DIR = _AX_DIR / "retained_witnesses"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scn_mod = _load("ax_fv_scenario_spec", _AX_DIR / "scenario_spec.py")
SCENARIO = _scn_mod.AX_FRAME_VALIDITY

_weak = _load("ax_fv_weakenings", _AX_DIR / "weakenings.py")
INTACT = _weak.intact
SURGICAL_WEAK = _weak.surgical_weak
GLOBAL_DISABLE = _weak.global_disable

# The held-out variant caught via the CLASS predicate (must flip under weakening).
CLASS_VARIANT = _load(
    "ax_fv_variant_a", _AX_DIR / "escape_variants" / "variant_a.py"
).mutator

_ANCHOR = "_author_verdict_null"


def test_F1_ax_frame_validity(tmp_path):
    """F1 (4-cell table + 3 controls) for ax-frame-validity via the reusable harness."""
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
