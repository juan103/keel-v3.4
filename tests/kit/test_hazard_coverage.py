import shutil
from pathlib import Path
import pytest
from hazard_coverage import check_hazard_coverage

ROOT = Path(__file__).resolve().parents[2]

def _clone(tmp_path):
    dst = tmp_path / "kit"
    shutil.copytree(ROOT / "goals", dst / "goals")
    return dst

def test_every_pinned_hazard_has_a_row():
    # Real full kit (not a goals-only clone): with green rows present, the
    # green-row engine runs during check_hazard_coverage and needs the whole kit.
    assert check_hazard_coverage(ROOT) == []  # the real matrix covers all pinned hazards

def test_missing_pinned_hazard_fails(tmp_path):
    kit = _clone(tmp_path)
    mtx = kit / "goals" / "hazard-coverage.md"
    lines = mtx.read_text(encoding="utf-8").splitlines()
    kept = [ln for ln in lines if "hz-orientation-cost" not in ln]
    mtx.write_text("\n".join(kept) + "\n", encoding="utf-8")
    violations = check_hazard_coverage(kit)
    assert any("hz-orientation-cost" in v for v in violations)

def test_criticality_downgrade_in_matrix_fails(tmp_path):
    kit = _clone(tmp_path)
    mtx = kit / "goals" / "hazard-coverage.md"
    txt = mtx.read_text(encoding="utf-8").replace(
        "| hz-adr-silent-edit | hz-adr-silent-edit | true |",
        "| hz-adr-silent-edit | hz-adr-silent-edit | false |")
    mtx.write_text(txt, encoding="utf-8")
    violations = check_hazard_coverage(kit)
    assert any("hz-adr-silent-edit" in v and "refusal_critical" in v for v in violations)

def test_offbaseline_pending_refusal_critical_fails(tmp_path):
    kit = _clone(tmp_path)
    base = kit / "goals" / ".pending-baseline.json"
    import json
    b = json.loads(base.read_text(encoding="utf-8"))
    b["pending_refusal_critical"].remove("hz-vacuous-test")
    base.write_text(json.dumps(b), encoding="utf-8")
    violations = check_hazard_coverage(kit)
    assert any("hz-vacuous-test" in v and "baseline" in v for v in violations)

def test_accepted_risk_row_is_not_required_green(tmp_path):
    kit = _clone(tmp_path)
    # residual rows are accepted-risk and must NOT produce a red-state violation
    violations = check_hazard_coverage(kit)
    assert not any("hz-external-validation-monoculture" in v and "baseline" in v for v in violations)

def test_phase0_green_without_falsifier_fails(tmp_path):
    kit = _clone(tmp_path)
    mtx = kit / "goals" / "hazard-coverage.md"
    # Flip hz-vacuous-test status from pending to green, leaving mitigating_check/proving tests as pending
    txt = mtx.read_text(encoding="utf-8")
    # The row columns: hazard_id | audit_hazard_ref | refusal_critical | mitigating_check | ... | status | ...
    # Replace only the status cell (12th col, value "pending") for hz-vacuous-test
    # The full row pattern to target the status column specifically
    txt = txt.replace(
        "| hz-vacuous-test | hz-vacuous-test | true | pending | n/a | pending | pending | pending | pending | n/a | n/a | ax-vacuous | pending | n/a |  | pending |",
        "| hz-vacuous-test | hz-vacuous-test | true | pending | n/a | pending | pending | pending | pending | n/a | n/a | ax-vacuous | pending | n/a |  | green |",
    )
    mtx.write_text(txt, encoding="utf-8")
    violations = check_hazard_coverage(kit)
    assert any("hz-vacuous-test" in v and "green" in v for v in violations)

def test_conditional_refusal_critical_valid_not_green_engine(tmp_path):
    """A conditional refusal-critical row on the pending baseline is valid (no
    violation) and does NOT trigger the green-row engine.

    Modifies hz-vacuous-test (refusal-critical, on baseline, mitigating_check=pending)
    to status=conditional.  If conditional triggered the green-row engine, the
    'green but no wired falsifier' check would fire -- it must NOT.
    """
    kit = _clone(tmp_path)
    mtx = kit / "goals" / "hazard-coverage.md"
    new_lines = []
    for ln in mtx.read_text(encoding="utf-8").splitlines():
        if ln.strip().startswith("| hz-vacuous-test |"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) == 21:
                cells[15] = "conditional"  # status column (0-indexed)
                ln = "| " + " | ".join(cells) + " |"
        new_lines.append(ln)
    mtx.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    violations = check_hazard_coverage(kit)
    vac = [v for v in violations if "hz-vacuous-test" in v]
    assert vac == [], f"unexpected violations for conditional row: {vac}"


def test_real_matrix_no_refusal_critical_green():
    # Load-bearing invariant: NO refusal-critical hazard row is green (the 0-of-7
    # headline). All green rows are non-critical detectors. cov is clean. This does
    # NOT pin the exact non-critical green set (which grows as phases land).
    from hazard_coverage import parse_matrix, check_hazard_coverage
    rows = parse_matrix(ROOT)
    greens = [r for r in rows if r.status == "green"]
    assert greens, "expected some non-critical detector rows to be green"
    crit_green = [r.hazard_id for r in greens if r.refusal_critical]
    assert not crit_green, f"refusal-critical row(s) green -- headline must stay 0 of 7: {crit_green}"
    assert check_hazard_coverage(ROOT) == []
