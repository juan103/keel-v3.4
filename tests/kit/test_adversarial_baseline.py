"""Phase 1c.0 adversarial baseline probe (§5.2, §6 Phase 1c.0).

Historical 1c.0 record. ADV-1 and ADV-3 baseline tests have been retired here
(1c-A.10): after hardening in 1c-A.6 and 1c-A.8 their "fails_open_today" names
became misleading (engine now rejects both), and the permanent strict-reject
assertions live in test_green_rows.py (test_adv_posthoc_relabeled_... and
test_adv_distance_overclaim_...). ADV-2 remains (engine already rejected before
hardening; still meaningful as a sanity check). ADV-4 remains as a skip/1c-B anchor.

GP-6: fixtures use build_fixture (21-col schema post-1c-A.1) or manual 21-col rows.
Schema migrated to 21 cols in 1c-A.1.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import green_rows
from hazard_coverage import parse_matrix
from _green_fixture import build_fixture


def _row(root):
    return parse_matrix(root)[0]


# ---------------------------------------------------------------------------
# ADV-2: vacuous-but-collectible
# ---------------------------------------------------------------------------

def test_adv2_vacuous_but_collectible_already_rejected(tmp_path):
    """ADV-2 BASELINE: negative test vacuous (always passes, ignores the check).
    GP-6: uses only existing fields. Current engine already has _assert_neuter_probe
    which catches this → ALREADY REJECTED (neuter-probe survives vacuous negative test)."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert 1 == 1",     # vacuous: does not exercise the check at all
        pos_body="assert synth_check('ok') == []",
        refusal_critical=True, layer="execution_time", strength="full",
        interval=7, wired="ci")
    v = green_rows.validate_green_row(root, _row(root))
    # Current engine already rejects via _assert_neuter_probe.
    assert any("neuter" in s or "vacuous" in s for s in v), (
        f"ADV-2 BASELINE: expected neuter-survived rejection; got: {v}")


# ---------------------------------------------------------------------------
# ADV-4: cache-survives-strict (deferred)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason=(
    "cache-survives-strict adversarial pattern requires real --strict cache semantics "
    "and cannot be honestly encoded against the current synthetic fixture (no live dep "
    "probes in the kit). Deferred to 1c-B, where the real check_reachability_probes_pass "
    "row is tested. 1c-B anchor: pattern is rejected when --strict re-runs probes rather "
    "than honoring a stale cached pass."
))
def test_adv4_cache_survives_strict_deferred():
    """ADV-4 deferred to 1c-B. See skip reason."""
    pytest.fail("should be skipped")


# ---------------------------------------------------------------------------
# ADV-5: vacuous-prevention (closed by I1 in 1c-B-i) -- permanent reject
# ---------------------------------------------------------------------------

def test_adv5_vacuous_prevention_permanently_rejected(tmp_path):
    """ADV-5: an execution_time row whose prevention test passes regardless of the
    check (vacuous) must be rejected by the I1 prevention-bite. Permanent guard."""
    obs = "guarded_resource_state"
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        refusal_critical=True, strength="full",
        prevention_test_body=(
            "def test_prevents():\n"
            "    guarded_resource_state = 'intact'\n"
            "    assert guarded_resource_state == 'intact'  # never depends on the check\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs)
    v = green_rows.validate_green_row(root, _row(root))
    assert any("prevention-probe survived" in s for s in v), (
        f"ADV-5: vacuous prevention must be rejected by I1; got: {v}")
