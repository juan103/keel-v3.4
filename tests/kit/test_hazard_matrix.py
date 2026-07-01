from pathlib import Path
import pytest
from hazard_coverage import parse_matrix

ROOT = Path(__file__).resolve().parents[2]

def test_matrix_has_all_15_rows():
    rows = parse_matrix(ROOT)
    ids = {r.hazard_id for r in rows}
    assert len(rows) == 15
    assert "hz-runtime-role-unannotated" in ids
    assert "hz-external-validation-monoculture" in ids

def test_residual_rows_are_accepted_risk():
    rows = {r.hazard_id: r for r in parse_matrix(ROOT)}
    assert rows["hz-external-validation-monoculture"].status == "accepted-risk"
    assert rows["hz-substantive-judgment-residue"].substantive_residue != "n/a"

def test_audit_rows_start_pending():
    rows = {r.hazard_id: r for r in parse_matrix(ROOT)}
    # hz-runtime-role-unannotated was moved to conditional in Phase 2a (Task 6):
    # mechanism built, green deferred pending commitment-lock + owner attestation.
    assert rows["hz-runtime-role-unannotated"].status == "conditional"

def test_unknown_column_is_fail_closed(tmp_path):
    (tmp_path / "goals").mkdir()
    (tmp_path / "goals" / "hazard-coverage.md").write_text(
        "| hazard_id | bogus_col |\n|---|---|\n| hz-x | y |\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_matrix(tmp_path)
