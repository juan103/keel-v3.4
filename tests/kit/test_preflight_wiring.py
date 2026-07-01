import pytest
from pathlib import Path
from hazard_coverage import check_hazard_coverage
import preflight
ROOT = Path(__file__).resolve().parents[2]

def test_preflight_registers_hazard_coverage():
    src = (ROOT / "preflight.py").read_text(encoding="utf-8")
    assert "check_hazard_coverage" in src

def test_commitment_lock_registered():
    """check_commitment_lock must be wired into the checks=[...] list and callable."""
    src = (ROOT / "preflight.py").read_text(encoding="utf-8")
    assert "check_commitment_lock" in src
    assert callable(preflight.check_commitment_lock)

def test_check_hazard_coverage_passes_on_baseline_tree():
    assert check_hazard_coverage(ROOT) == []

def test_violation_makes_preflight_check_raise(monkeypatch):
    monkeypatch.setattr(preflight, "_check_hazard_coverage", lambda _root: ["synthetic violation"])
    with pytest.raises(AssertionError):
        preflight.check_hazard_coverage()

def test_missing_artifact_fails_cleanly(monkeypatch):
    def _raise(_root):
        raise FileNotFoundError("x")
    monkeypatch.setattr(preflight, "_check_hazard_coverage", _raise)
    with pytest.raises(AssertionError):
        preflight.check_hazard_coverage()
