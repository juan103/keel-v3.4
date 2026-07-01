import json
import shutil
from pathlib import Path
import pytest
from hazard_coverage import audit_v3_3_hazards, verify_audit_pin

ROOT = Path(__file__).resolve().parents[2]  # keel_v3.4/

def test_parser_finds_all_13_hazards():
    haz = audit_v3_3_hazards(ROOT)
    ids = {h["id"] for h in haz}
    assert len(haz) == 13
    assert "hz-runtime-role-unannotated" in ids
    assert next(h for h in haz if h["id"] == "hz-bug-outside-lifecycle")["refusal_critical"] is False
    assert next(h for h in haz if h["id"] == "hz-adr-silent-edit")["refusal_critical"] is True

def test_pin_passes_when_consistent():
    assert verify_audit_pin(ROOT) == []

def test_pin_fails_on_silent_downgrade(tmp_path, monkeypatch):
    # Copy audit + lock, flip a criticality in the lock, expect a violation.
    (tmp_path / "goals").mkdir()
    shutil.copy(ROOT / "goals" / "audit-v3.3.md", tmp_path / "goals" / "audit-v3.3.md")
    lock = json.loads((ROOT / "goals" / ".audit-lock.json").read_text(encoding="utf-8"))
    lock["hazards"]["hz-adr-silent-edit"]["refusal_critical"] = False
    (tmp_path / "goals" / ".audit-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    violations = verify_audit_pin(tmp_path)
    assert any("hz-adr-silent-edit" in v for v in violations)


def test_pin_fails_on_content_change(tmp_path):
    # Copy audit + lock unchanged, then append a non-row line to audit bytes.
    # The 13-hazard set is UNCHANGED but the sha256 must differ.
    (tmp_path / "goals").mkdir()
    shutil.copy(ROOT / "goals" / "audit-v3.3.md", tmp_path / "goals" / "audit-v3.3.md")
    shutil.copy(ROOT / "goals" / ".audit-lock.json", tmp_path / "goals" / ".audit-lock.json")
    audit_copy = tmp_path / "goals" / "audit-v3.3.md"
    with audit_copy.open("a", encoding="utf-8") as f:
        f.write("\n<!-- note -->")
    violations = verify_audit_pin(tmp_path)
    assert any("sha256" in v for v in violations)


def test_pin_fails_on_missing_audit(tmp_path):
    # Empty goals/ — no audit file at all.
    (tmp_path / "goals").mkdir()
    violations = verify_audit_pin(tmp_path)
    assert any("audit-v3.3.md" in v for v in violations)


def test_pin_fails_on_missing_lock(tmp_path):
    # Only audit present, no lock file.
    (tmp_path / "goals").mkdir()
    shutil.copy(ROOT / "goals" / "audit-v3.3.md", tmp_path / "goals" / "audit-v3.3.md")
    violations = verify_audit_pin(tmp_path)
    assert any(".audit-lock.json" in v for v in violations)
