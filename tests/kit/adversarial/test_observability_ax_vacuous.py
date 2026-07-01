"""F1 -- the differential-observability gate for ax-vacuous (Phase 3.5b, PROVISIONAL).

A thin binding of the ax-vacuous scenario pieces to the reusable F1 harness: the
whole 4-cell truth table + 3 controls is exercised by one assert_f1(...) call.

Scenario: hz-vacuous-test.  The escape is a vacuous green -- a recorded
first-outcome flipped failed->passed across commits with NO code change (the test
declared passing without ever being seen red), or a first-outcome entry dropped
across commits.  Detection WRAPS the REAL
log_integrity.detect_first_outcome_log_tampering (git log/show comparison); the
named check partitions its violation list into two separable clauses.

GIT FIXTURE NOTE
  The fixture creates a REAL git repo (git init + commits, epoch-0 dates for C3
  determinism); the real detector returns [] outside a git repo.  Retained
  witnesses ship their history as a git-history.bundle sidecar (a nested .git/
  cannot be committed to the main repo); named_check clones the bundle and runs the
  real detector on the clone.  See scenario_spec.PROJECTION_NOTE.

Named check clauses:
  CLASS PREDICATE ANCHOR: _green_without_red -- the real detector reported a
    "flip failed->passed without code change" violation.
  OTHER CLAUSE:           _entry_dropped     -- the real detector reported an
    "entry dropped" violation; survives the surgical weakening.

What F1 PROVES (and only this): SENSITIVITY (caught True for the escape under the
intact check, False when _green_without_red is surgically removed), SPECIFICITY
(caught False on clean + benign-noisy under the intact check), EXECUTION-BINDING
(each verdict bound to a content-addressed trace an independent replicator
reproduces byte-identically).  Live faithfulness / escape-vector provocation /
observable-faithfulness are UNVALIDATED(Phase4), asserted nowhere.

The required 4-cell table for ax-vacuous:
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

# keel_v3.4/ root is parents[3] from this file.
_KIT_ROOT = str(Path(__file__).resolve().parents[3])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import f1_harness  # noqa: E402  (the reusable F1 gate)

_AX_DIR = Path(__file__).resolve().parent / "ax-vacuous"
_WIT_DIR = _AX_DIR / "retained_witnesses"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scn_mod = _load("ax_vacuous_scenario_spec", _AX_DIR / "scenario_spec.py")
SCENARIO = _scn_mod.AX_VACUOUS

_weak = _load("ax_vacuous_weakenings", _AX_DIR / "weakenings.py")
INTACT = _weak.intact
SURGICAL_WEAK = _weak.surgical_weak
GLOBAL_DISABLE = _weak.global_disable

# The held-out variant caught via the CLASS predicate (must flip under weakening).
CLASS_VARIANT = _load(
    "ax_vacuous_variant_a", _AX_DIR / "escape_variants" / "variant_a.py"
).mutator

_ANCHOR = "_green_without_red"


def test_F1_ax_vacuous(tmp_path):
    """F1 (4-cell table + 3 controls) for ax-vacuous via the reusable harness.

    PROVISIONAL: hz-vacuous-test exercised via the git-history branch of the real
    detector's surface.
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
