"""adversarial_coverage.py -- cut-rule, coverage-floor, gate-eligibility tracking.

Phase 3.5b Task 9.  Stdlib only; ASCII-only.

Public API
----------
REFERENCE : str
    Name of the reference scenario (ax-runtime-role).

TOTAL : int
    Total number of refusal-critical scenarios in the gate set (8).

GATE_SCENARIOS : list[dict]
    One dict per scenario: {"name": str, "eligible": bool, "cut_reason": str|None}.
    A CUT (eligible=False) MUST carry a non-empty cut_reason; an eligible scenario
    has cut_reason=None.

coverage(scenarios=GATE_SCENARIOS) -> dict
    Returns {"eligible": int, "total": 8, "cuts": [(name, reason)...],
             "denominator": "<eligible>/8"}.

assert_coverage_floor(scenarios=GATE_SCENARIOS) -> None
    Raises AssertionError if:
      (a) the REFERENCE scenario is cut        -- premise broken, STOP
      (b) eligible < 5                         -- below majority, STOP
      (c) any cut has an empty/None cut_reason -- silent cut, FAIL
    Returns cleanly otherwise.

Cut-rule (from the trio v_final):
    A cut reduces the gate denominator ONLY with a logged cut-record.
    An unlogged cut is a gate FAILURE.
    Cutting the reference scenario STOPS the phase.
    Dropping below a majority (<5 of 8 eligible) STOPS/re-scopes.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REFERENCE: str = "ax-runtime-role"
TOTAL: int = 8

# ---------------------------------------------------------------------------
# Gate-eligibility data
# ---------------------------------------------------------------------------
# Encode the confirmed eligibility set (Phase 3.5b, 2026-06-29):
#   7 eligible + 1 logged CUT (ax-reachability).
#
# A hazard is GATE-ELIGIBLE iff its silent escape is a deterministic tree
# property the named check evaluates.  A non-eligible hazard is a logged CUT.
#
# ax-reachability CUT reason: the reachability probe is inherently a
# live/non-deterministic dependency check; its silent escape (a failing live
# probe ignored via a stale cached PASS) cannot be expressed as a deterministic
# tree property without simulating the probe, which would make the gate test
# the simulation not the hazard.

GATE_SCENARIOS: list[dict] = [
    {
        "name": "ax-runtime-role",
        "eligible": True,
        "cut_reason": None,
    },
    {
        "name": "ax-compliance",
        "eligible": True,
        "cut_reason": None,
    },
    {
        "name": "ax-relaxation",
        "eligible": True,
        "cut_reason": None,
    },
    {
        "name": "ax-frame-validity",
        "eligible": True,
        "cut_reason": None,
    },
    {
        "name": "ax-sessionstart",
        "eligible": True,          # PROVISIONAL
        "cut_reason": None,
    },
    {
        "name": "ax-adr-edit",
        "eligible": True,          # PROVISIONAL
        "cut_reason": None,
    },
    {
        "name": "ax-vacuous",
        "eligible": True,          # PROVISIONAL (git fixture in progress)
        "cut_reason": None,
    },
    {
        "name": "ax-reachability",
        "eligible": False,         # CUT
        "cut_reason": (
            "the reachability probe is inherently a live/non-deterministic "
            "dependency check; its silent escape (a failing live probe ignored "
            "via a stale cached PASS) cannot be expressed as a deterministic "
            "tree property without simulating the probe, which would make the "
            "gate test the simulation not the hazard."
        ),
    },
]

# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def coverage(scenarios: list[dict] = GATE_SCENARIOS) -> dict:
    """Return a coverage summary dict.

    Keys:
      eligible   -- int: number of eligible scenarios
      total      -- int: always 8 (TOTAL)
      cuts       -- list of (name, reason) for every ineligible scenario
      denominator -- str: "<eligible>/8"
    """
    eligible = sum(1 for s in scenarios if s["eligible"])
    cuts = [
        (s["name"], s.get("cut_reason") or "")
        for s in scenarios
        if not s["eligible"]
    ]
    return {
        "eligible": eligible,
        "total": TOTAL,
        "cuts": cuts,
        "denominator": f"{eligible}/{TOTAL}",
    }


def assert_coverage_floor(scenarios: list[dict] = GATE_SCENARIOS) -> None:
    """Assert that the coverage floor is satisfied.

    Raises AssertionError (never silently skips) if:
      (a) the reference scenario (ax-runtime-role) is cut -- STOP
      (b) eligible < 5                                    -- STOP
      (c) any cut has an empty/None cut_reason            -- FAIL (silent cut)

    Returns cleanly when the floor is satisfied.
    """
    # (c) check first: no silent cuts (a silent cut is itself a protocol violation
    #     independent of the floor -- catch it before checking counts)
    for s in scenarios:
        if not s["eligible"]:
            reason = s.get("cut_reason")
            if not reason:
                raise AssertionError(
                    f"silent cut detected for scenario {s['name']!r}: "
                    f"a cut MUST carry a non-empty cut_reason (unlogged cut is a gate FAILURE)"
                )

    # (a) reference must be eligible
    ref_rows = [s for s in scenarios if s["name"] == REFERENCE]
    if ref_rows and not ref_rows[0]["eligible"]:
        raise AssertionError(
            f"reference scenario {REFERENCE!r} is cut -- "
            f"cutting the reference scenario STOPS the phase (premise broken)"
        )

    # (b) majority floor: at least 5 of 8 must be eligible
    eligible_count = sum(1 for s in scenarios if s["eligible"])
    if eligible_count < 5:
        raise AssertionError(
            f"coverage below majority: only {eligible_count}/{TOTAL} eligible "
            f"(need >= 5) -- dropping below majority STOPS/re-scopes the phase"
        )
