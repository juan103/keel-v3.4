"""Tests for replication_runner.py -- execution-trace machinery (Phase 3.5a Task 5).

TDD Step 1: failing tests written BEFORE implementation.

Three tests:
  test_run_cell_emits_trace       -- a cell yields a trace dict with all required fields.
  test_replicate_reproduces       -- re-running reproduces the trace byte-identically -> [].
  test_replicate_detects_fabrication -- hand-altered trace (flipped verdict) -> problem.

All tests use the ax-runtime-role scenario + named_check.run as check_fn.
The ax-runtime-role/ directory contains a hyphen, so we load it via importlib.
ASCII-only.  Stdlib only.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# keel_v3.4/ root is parents[3] from this file's location:
#   parents[0] = adversarial/
#   parents[1] = kit/
#   parents[2] = tests/
#   parents[3] = keel_v3.4/
_KIT_ROOT = str(Path(__file__).resolve().parents[3])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import pytest  # noqa: E402
from replication_runner import run_cell, replicate, _check_id  # noqa: E402

# ---------------------------------------------------------------------------
# Load ax-runtime-role scenario + named_check via importlib (hyphenated dir)
# ---------------------------------------------------------------------------

_AX_DIR = Path(__file__).resolve().parent / "ax-runtime-role"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ax_mod = _load_module("ax_runtime_role_scenario_spec", _AX_DIR / "scenario_spec.py")
SCENARIO = _ax_mod.AX_RUNTIME_ROLE

_nc_mod = _load_module("ax_runtime_role_named_check", _AX_DIR / "named_check.py")
CHECK_FN = _nc_mod.run


# ---------------------------------------------------------------------------
# test_run_cell_emits_trace
# ---------------------------------------------------------------------------

def test_run_cell_emits_trace(tmp_path):
    """run_cell for the 'escape' tree_kind returns a trace dict with all required fields.

    Checks:
    - All five keys present: cell, tree_hash, check, verdict, contract_hash.
    - cell == 'escape'.
    - tree_hash is a 64-hex-char sha256 string.
    - check is a non-empty string (stable id).
    - verdict is True (escape mutator -> named check detects the escape).
    - contract_hash == 'n/a'.
    """
    trace = run_cell(SCENARIO, "escape", CHECK_FN, tmp_path / "work")

    assert isinstance(trace, dict), "run_cell must return a dict"
    for key in ("cell", "tree_hash", "check", "verdict", "contract_hash"):
        assert key in trace, f"trace must contain key {key!r}; got keys {list(trace)}"

    assert trace["cell"] == "escape", f"expected cell='escape', got {trace['cell']!r}"

    assert isinstance(trace["tree_hash"], str), "tree_hash must be a str"
    assert len(trace["tree_hash"]) == 64, (
        f"tree_hash must be 64 hex chars (sha256); got {len(trace['tree_hash'])} chars"
    )
    assert all(c in "0123456789abcdef" for c in trace["tree_hash"]), (
        "tree_hash must be lowercase hex"
    )

    assert isinstance(trace["check"], str) and trace["check"], \
        "check must be a non-empty string"

    assert trace["verdict"] is True, (
        "verdict must be True for the escape tree_kind (named check detects the escape)"
    )

    assert trace["contract_hash"] == "n/a", (
        f"contract_hash must be 'n/a' (Phase 3.5a); got {trace['contract_hash']!r}"
    )


# ---------------------------------------------------------------------------
# test_replicate_reproduces
# ---------------------------------------------------------------------------

def test_replicate_reproduces(tmp_path):
    """Re-running the same cell from the same inputs reproduces the trace byte-identically.

    replicate() must return [] (no problems) when the recorded trace exactly
    matches the re-execution result.
    """
    work1 = tmp_path / "run1"
    work2 = tmp_path / "replicate"

    trace = run_cell(SCENARIO, "escape", CHECK_FN, work1)

    check_id = _check_id(CHECK_FN)
    check_fns = {check_id: CHECK_FN}

    problems = replicate([trace], SCENARIO, check_fns, work2)
    assert problems == [], (
        "replicate() must return [] (byte-identical reproduction); "
        f"got problems:\n" + "\n".join(problems)
    )


# ---------------------------------------------------------------------------
# test_replicate_detects_fabrication
# ---------------------------------------------------------------------------

def test_replicate_detects_fabrication(tmp_path):
    """A hand-altered trace with a flipped verdict is detected as a fabrication.

    replicate() must return at least one problem string when the recorded trace
    does not match the re-execution result (the classic fabrication case: a
    'true, false, false, false' tuple that was never actually run cannot
    reproduce the intermediate execution trace).
    """
    work1 = tmp_path / "run1"
    trace = run_cell(SCENARIO, "escape", CHECK_FN, work1)

    # Fabricate: flip the verdict so the trace does not reflect real execution.
    fabricated = dict(trace)
    fabricated["verdict"] = not trace["verdict"]

    check_id = _check_id(CHECK_FN)
    check_fns = {check_id: CHECK_FN}

    problems = replicate([fabricated], SCENARIO, check_fns, tmp_path / "rep")
    assert problems, (
        "replicate() must detect a fabricated verdict; "
        "a trace with the wrong verdict must not reproduce byte-identically"
    )
