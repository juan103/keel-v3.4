"""test_coverage_floor.py -- cut-rule + coverage-floor + gate-eligibility tests.

Phase 3.5b Task 9.  Stdlib only; ASCII-only.

Tests (TDD order -- written before adversarial_coverage.py existed):
  test_reference_cut_stops       -- ax-runtime-role cut => AssertionError
  test_below_majority_stops      -- eligible=4 => AssertionError
  test_silent_cut_fails          -- cut with no reason => AssertionError
  test_current_coverage_ok       -- GATE_SCENARIOS => floor passes, no exception
  test_coverage_prints_denominator -- coverage() returns 7/8 + reachability cut
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# helpers to build synthetic scenario lists for error-path tests
# ---------------------------------------------------------------------------

def _make(name: str, eligible: bool, cut_reason=None) -> dict:
    return {"name": name, "eligible": eligible, "cut_reason": cut_reason}


REFERENCE = "ax-runtime-role"


def _all_eligible() -> list:
    """Eight eligible scenarios (no cuts)."""
    names = [
        "ax-runtime-role", "ax-compliance", "ax-relaxation", "ax-frame-validity",
        "ax-sessionstart", "ax-adr-edit", "ax-vacuous", "ax-reachability",
    ]
    return [_make(n, True) for n in names]


# ---------------------------------------------------------------------------
# Step-1 tests (RED before implementation)
# ---------------------------------------------------------------------------

def test_reference_cut_stops():
    """Cutting the reference scenario (ax-runtime-role) must raise AssertionError."""
    from adversarial_coverage import assert_coverage_floor
    scenarios = _all_eligible()
    # Replace reference with a cut
    scenarios = [
        _make(s["name"], False, "test cut reason") if s["name"] == REFERENCE else s
        for s in scenarios
    ]
    with pytest.raises(AssertionError, match="reference"):
        assert_coverage_floor(scenarios)


def test_below_majority_stops():
    """Fewer than 5 eligible scenarios must raise AssertionError."""
    from adversarial_coverage import assert_coverage_floor
    # Only 4 eligible (reference is eligible, but 3 others + reference = 4 total)
    names_all = [
        "ax-runtime-role", "ax-compliance", "ax-relaxation", "ax-frame-validity",
        "ax-sessionstart", "ax-adr-edit", "ax-vacuous", "ax-reachability",
    ]
    # Make reference + 3 others eligible, rest cut
    scenarios = []
    eligible_count = 0
    for name in names_all:
        if eligible_count < 4:
            scenarios.append(_make(name, True))
            eligible_count += 1
        else:
            scenarios.append(_make(name, False, "cut for test"))
    # Confirm reference is eligible (it's first)
    assert scenarios[0]["name"] == REFERENCE
    assert scenarios[0]["eligible"] is True
    # Confirm we have exactly 4 eligible
    assert sum(1 for s in scenarios if s["eligible"]) == 4
    with pytest.raises(AssertionError, match="majority"):
        assert_coverage_floor(scenarios)


def test_silent_cut_fails():
    """A cut with no cut_reason must raise AssertionError (silent cut => FAIL)."""
    from adversarial_coverage import assert_coverage_floor
    scenarios = _all_eligible()
    # Add a silent cut (cut_reason=None)
    scenarios = [
        _make(s["name"], False, None) if s["name"] == "ax-reachability" else s
        for s in scenarios
    ]
    with pytest.raises(AssertionError, match="silent"):
        assert_coverage_floor(scenarios)


def test_current_coverage_ok():
    """The real GATE_SCENARIOS passes the coverage floor without raising.

    Invariants:
    - eligible >= 5
    - reference (ax-runtime-role) is eligible
    - every cut has a non-empty cut_reason
    """
    from adversarial_coverage import GATE_SCENARIOS, REFERENCE as REF, assert_coverage_floor
    # Must not raise
    assert_coverage_floor(GATE_SCENARIOS)
    eligible_count = sum(1 for s in GATE_SCENARIOS if s["eligible"])
    assert eligible_count >= 5, f"eligible={eligible_count} < 5"
    ref_scenarios = [s for s in GATE_SCENARIOS if s["name"] == REF]
    assert ref_scenarios, "reference scenario not in GATE_SCENARIOS"
    assert ref_scenarios[0]["eligible"], "reference scenario must be eligible"
    for s in GATE_SCENARIOS:
        if not s["eligible"]:
            assert s.get("cut_reason"), (
                f"cut scenario {s['name']!r} has no cut_reason (silent cut)"
            )


def test_coverage_prints_denominator():
    """coverage() returns the expected shape: eligible=7, total=8, denominator='7/8',
    reachability in cuts with a non-empty reason."""
    from adversarial_coverage import GATE_SCENARIOS, coverage
    result = coverage(GATE_SCENARIOS)
    assert result["eligible"] == 7, f"expected 7 eligible, got {result['eligible']}"
    assert result["total"] == 8, f"expected total=8, got {result['total']}"
    assert result["denominator"] == "7/8", (
        f"expected denominator='7/8', got {result['denominator']!r}"
    )
    cut_names = [name for name, _reason in result["cuts"]]
    assert "ax-reachability" in cut_names, (
        f"ax-reachability should appear in cuts; got {cut_names}"
    )
    for name, reason in result["cuts"]:
        assert reason, f"cut {name!r} has empty reason in coverage() output"
