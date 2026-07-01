from pathlib import Path
from commitment_lock import snapshot_lock
ROOT = Path(__file__).resolve().parents[2]

def test_snapshot_captures_refusal_critical_rows_and_checks():
    snap = snapshot_lock(ROOT)
    assert "goals_sections" in snap and "refusal_critical_rows" in snap and "registered_checks" in snap
    rc = {r["hazard_id"] for r in snap["refusal_critical_rows"]}
    assert "hz-runtime-role-unannotated" in rc
    assert "check_hazard_coverage" in snap["registered_checks"]


def test_snapshot_includes_preflight_and_registries():
    snap = snapshot_lock(ROOT)
    # New broadened keys
    assert "preflight_sha" in snap, "snapshot must include preflight_sha"
    assert "attest_keys_sha" in snap, "snapshot must include attest_keys_sha"
    assert "runtime_roles_sha" in snap, "snapshot must include runtime_roles_sha"
    # registered_checks should contain the FULL check list, not just one entry
    checks = snap["registered_checks"]
    assert "check_author_fill_contamination" in checks, (
        "full check list must include check_author_fill_contamination"
    )
    assert "check_frame_validity_audit" in checks, (
        "full check list must include check_frame_validity_audit"
    )
    # Backward compat: check_hazard_coverage still present
    assert "check_hazard_coverage" in checks
