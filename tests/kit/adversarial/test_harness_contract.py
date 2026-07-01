"""test_harness_contract.py -- the pinned harness contract (Phase 3.5d Task 1).

Verifies:
  - the contract is present + well-formed (the load-bearing fields exist);
  - the Phase-4 live-exercise fields are explicit PENDING placeholders, NOT fabricated values
    (honesty: a fabricated model id would falsely imply a live run pinned to it);
  - the contract's scenario_locks match the live per-scenario locked-artifact hashes;
  - the contract hash is deterministic + matches the file on disk;
  - the serialized goals/.harness-contract.json matches harness_contract.build_contract
    (the single source of truth).

ASCII-only. Stdlib only (test-side).
"""
from __future__ import annotations

import sys
from pathlib import Path

# keel_v3.4/ root is parents[3]: [0]=adversarial [1]=kit [2]=tests [3]=keel_v3.4
_KIT_ROOT = str(Path(__file__).resolve().parents[3])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import harness_contract as hc  # noqa: E402

_ROOT = Path(_KIT_ROOT)

PENDING = "PENDING(Phase4)"


def test_contract_present_and_wellformed():
    c = hc.load(_ROOT)
    for field in (
        "schema", "agent_interface", "auto_mode", "adversary_model", "sampling",
        "prompt_template", "scenario_locks", "provisional_scenarios", "gate_coverage",
    ):
        assert field in c, "missing contract field: {}".format(field)
    # The 7 eligible scenarios are locked.
    assert sorted(c["scenario_locks"].keys()) == sorted(hc.ELIGIBLE_SCENARIOS)
    # gate_coverage is honest: 7/8 with the reachability cut named.
    assert c["gate_coverage"]["denominator"] == "7/8"
    assert c["gate_coverage"]["cuts"] == ["ax-reachability"]


def test_phase4_fields_reflect_the_live_run():
    """Post-run honesty (updated 2026-06-30, Phase-4 F7 run + downgrade).

    Before the live run these fields were explicit PENDING placeholders (a fabricated model id
    would have falsely implied a live run pinned to it). The Phase-4 live exercise then ran for
    real with claude-opus-4-8, so the adversary_model + sampling fields are now FILLED with the
    actual run configuration -- that is the honest record, not a fabrication (the adversary that
    ran was opus). tool_permission_set remains PENDING: its honest correction to "full repo
    reachable -- subagents root at the session repo, isolation verified infeasible, the exercise
    was NOT check-blind" is a locked-surface edit flagged for owner ratification (see
    docs/superpowers/keel-v3.4-phase4-F7-finding.md sec 7).
    """
    c = hc.load(_ROOT)
    # The live run happened: adversary_model records the REAL adversary (opus), not PENDING.
    assert c["adversary_model"]["id"] == "claude-opus-4-8", (
        "adversary_model.id must record the actual adversary that ran (claude-opus-4-8)"
    )
    assert c["adversary_model"]["version"] == "4.8"
    # sampling is filled with the run's actual (named-residue) configuration, not PENDING.
    assert c["sampling"]["temperature"] != PENDING and c["sampling"]["temperature"]
    assert c["sampling"]["retry_policy"] != PENDING and c["sampling"]["retry_policy"]
    # tool_permission_set: still PENDING until the owner-ratified non-blindness correction lands.
    assert c["agent_interface"]["tool_permission_set"] == PENDING
    # Anti-fabrication, post-run sense: the recorded adversary is the specific real one that ran;
    # no other vendor's model is claimed.
    assert "gpt" not in str(c["adversary_model"]).lower()


def test_scenario_locks_match():
    c = hc.load(_ROOT)
    live = hc.scenario_lock_hashes(_ROOT)
    assert c["scenario_locks"] == live, (
        "contract scenario_locks drifted from the live locked artifacts -- re-snapshot the contract"
    )
    # Every eligible scenario's class_predicate.json + keyword_set.json are hashed (non-None).
    for name, rec in live.items():
        assert rec["class_predicate.json"], "{}: class_predicate.json missing/unhashed".format(name)
        assert rec["keyword_set.json"], "{}: keyword_set.json missing/unhashed".format(name)


def test_contract_hash_stable_and_matches_file():
    # The file-bytes hash is deterministic.
    h1 = hc.contract_hash(_ROOT)
    h2 = hc.contract_hash(_ROOT)
    assert h1 == h2 and h1 is not None
    # The serialized file matches build_contract (the single source of truth).
    built = hc.build_contract(_ROOT)
    loaded = hc.load(_ROOT)
    assert built == loaded, "goals/.harness-contract.json drifted from build_contract()"
