"""F1 -- the differential-observability gate for ax-relaxation (Phase 3.5b).

A thin binding of the ax-relaxation scenario pieces to the reusable F1 harness:
the whole 4-cell truth table + 3 controls is exercised by one assert_f1(...) call.

Scenario observable (principled narrowing -- see scenario_spec.OBSERVABLE_SCOPE):
  the hz-conversational-relaxation escape is exercised as a GOALS.md locked-section
  divergence (## Commitments softened so it diverges from the committed goals_sections
  snapshot -- a refusal/commitment weakened).  The named check WRAPS the REAL
  commitment_lock goals-section computation (commitment_lock._section + sha256)
  and reads ONLY goals/GOALS.md + goals/.commitment-lock.json -- both survive the
  harness projection, so the check runs clean on the projected tree.  The
  kit-file-sha sub-surface (preflight_sha / matrix rows) is a named residue, out
  of this scenario's observable (Phase-4 faithfulness).

Mirror-image of ax-compliance: class anchor = _commitments_section_diverged
  (ax-compliance anchor = _falsifier_section_diverged); escape softens a
  COMMITMENTS clause (ax-compliance softens the Falsifier).

What F1 PROVES (and only this): SENSITIVITY (caught True for the escape under the
intact check, False when the class-predicate clause is surgically removed),
SPECIFICITY (caught False on clean + benign-noisy under the intact check),
EXECUTION-BINDING (each verdict bound to a content-addressed trace an independent
replicator reproduces byte-identically).  Live faithfulness / escape-vector
provocation / observable-faithfulness are UNVALIDATED(Phase4), asserted nowhere.

ASCII-only.  Stdlib only (test-side).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# keel_v3.4/ root is parents[3] from this file.
_KIT_ROOT = str(Path(__file__).resolve().parents[3])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import f1_harness  # noqa: E402  (the reusable F1 gate under exercise)

_AX_DIR = Path(__file__).resolve().parent / "ax-relaxation"
_WIT_DIR = _AX_DIR / "retained_witnesses"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scn_mod = _load("ax_relaxation_scenario_spec", _AX_DIR / "scenario_spec.py")
SCENARIO = _scn_mod.AX_RELAXATION

_weak = _load("ax_relaxation_weakenings", _AX_DIR / "weakenings.py")
INTACT = _weak.intact
SURGICAL_WEAK = _weak.surgical_weak
GLOBAL_DISABLE = _weak.global_disable

# The held-out variant caught via the CLASS predicate (must flip under weakening).
CLASS_VARIANT = _load(
    "ax_relaxation_variant_a", _AX_DIR / "escape_variants" / "variant_a.py"
).mutator

_ANCHOR = "_commitments_section_diverged"


def test_F1_ax_relaxation(tmp_path):
    """F1 (4-cell table + 3 controls) for ax-relaxation via the reusable harness."""
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
