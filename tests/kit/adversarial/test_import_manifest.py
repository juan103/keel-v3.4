"""test_import_manifest.py -- tests for the transitive import-disjointness manifest.

Phase 3.5c -- Task 4: NARROW import-hygiene (anti-correlation).

All 7 eligible scenarios are tested for disjointness, plus:
- an injected shared deep import is caught (the load-bearing transitive property),
- flag_dynamic detects importlib and subprocess.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# keel_v3.4/ root
_KIT_ROOT = Path(__file__).resolve().parents[3]
if str(_KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(_KIT_ROOT))

from import_manifest import assert_disjoint, flag_dynamic, transitive_nonstdlib_imports

# Directory containing this file (keel_v3.4/tests/kit/adversarial/)
_ADV = Path(__file__).resolve().parent

ELIGIBLE_SCENARIOS = [
    "ax-runtime-role",
    "ax-compliance",
    "ax-relaxation",
    "ax-frame-validity",
    "ax-sessionstart",
    "ax-adr-edit",
    "ax-vacuous",
]


def test_all_eligible_scenarios_disjoint():
    """All 7 eligible scenarios have disjoint non-stdlib transitive import closures.

    A failure here is a genuine finding -- do NOT loosen the check.
    """
    failures = []
    for scenario in ELIGIBLE_SCENARIOS:
        nc = _ADV / scenario / "named_check.py"
        det = _ADV / scenario / "escape_detector.py"
        assert nc.is_file(), f"missing named_check.py for {scenario}"
        assert det.is_file(), f"missing escape_detector.py for {scenario}"
        problems = assert_disjoint(nc, det, _KIT_ROOT)
        if problems:
            failures.append(f"[{scenario}] {problems}")
    assert not failures, (
        "disjointness violations (genuine finding -- investigate):\n"
        + "\n".join(failures)
    )


def test_injected_shared_deep_import_caught(tmp_path: Path):
    """A shared non-stdlib dep one hop deep is caught by assert_disjoint.

    Proves the TRANSITIVE property: a shared dependency introduced via a
    local-kit helper (not a direct import in the detector) is still caught.

    Setup:
      shared_helper.py  (local kit in tmp_path): directly imports fake_external_lib
      named_check_tmp.py: directly imports fake_external_lib
      detector_tmp.py:    imports shared_helper (which imports fake_external_lib)

    Both named_check_tmp and detector_tmp reach fake_external_lib through
    different paths; assert_disjoint must report the intersection.
    """
    # Local kit helper: imports a fake non-stdlib module
    helper = tmp_path / "shared_helper.py"
    helper.write_text("import fake_external_lib\n", encoding="utf-8")

    # named_check: imports the fake module directly
    nc = tmp_path / "named_check_tmp.py"
    nc.write_text("import fake_external_lib\n", encoding="utf-8")

    # escape_detector: reaches fake_external_lib via shared_helper (one hop)
    det = tmp_path / "detector_tmp.py"
    det.write_text("import shared_helper\n", encoding="utf-8")

    # kit_root = tmp_path so shared_helper.py is resolved as a local kit module
    problems = assert_disjoint(nc, det, tmp_path)

    assert problems, (
        "expected assert_disjoint to catch shared deep import; got []"
    )
    assert any("fake_external_lib" in p for p in problems), (
        f"expected 'fake_external_lib' in problems; got {problems}"
    )


def test_flag_dynamic_detects_importlib_and_subprocess(tmp_path: Path):
    """flag_dynamic flags importlib and subprocess (dynamic-evading imports)."""
    mod = tmp_path / "dynamic_mod.py"
    mod.write_text(
        textwrap.dedent("""\
            import importlib
            import subprocess
            mod = importlib.import_module("os")
            result = subprocess.run(["echo", "hi"])
        """),
        encoding="utf-8",
    )
    problems = flag_dynamic(mod)
    assert problems, f"expected flag_dynamic to return problems; got []"
    combined = " ".join(problems)
    assert "importlib" in combined, (
        f"importlib not flagged; problems={problems}"
    )
    assert "subprocess" in combined, (
        f"subprocess not flagged; problems={problems}"
    )
