"""Tests for pilot_phase binding shape, pilot.py, and check_pilot_phase.

Phase 3 M3 -- Task 2.  TDD: write all tests first, watch them fail for the
right reason (missing module / unknown type), then implement.

ASCII-only strings throughout.
"""
import json
import sys
from pathlib import Path

# Ensure keel_v3.4/ is importable regardless of how pytest is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
import binding
import preflight

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Schema tests (binding.py)
# ---------------------------------------------------------------------------

def test_pilot_schema_accepts_complete_block():
    """validate_block returns [] for a fully-specified pilot_phase block."""
    block = {
        "type": "pilot_phase",
        "id": "falsifier.kit-external-validation",
        "gate_thresholds": {"deadline": "2026-12-31", "eligible_count": 1},
        "eligibility": "a real non-self-authored KEEL project",
        "dispositions": ["pilot_pass", "pilot_fail_falsifier", "pilot_fail_unused", "extend"],
    }
    assert binding.validate_block(block) == []


def test_pilot_schema_rejects_missing_gate_thresholds():
    """Dropping gate_thresholds yields a missing-required-field error."""
    block = {
        "type": "pilot_phase",
        "id": "falsifier.kit-external-validation",
        # gate_thresholds intentionally omitted
        "eligibility": "a real non-self-authored KEEL project",
        "dispositions": ["pilot_pass"],
    }
    errors = binding.validate_block(block)
    assert any("gate_thresholds" in e for e in errors), (
        "expected an error mentioning 'gate_thresholds', got: " + repr(errors)
    )


# ---------------------------------------------------------------------------
# pilot.py: classify() and check_pilot_record()
# ---------------------------------------------------------------------------

def test_pilot_pending_is_the_shiptime_state():
    """classify(record=None, block) returns 'pilot_pending' -- no run yet."""
    import pilot
    block = {
        "type": "pilot_phase",
        "id": "falsifier.kit-external-validation",
        "gate_thresholds": {"deadline": "2026-12-31", "eligible_count": 1},
        "eligibility": "test",
        "dispositions": ["pilot_pass"],
    }
    result = pilot.classify(None, block)
    assert result == "pilot_pending", (
        f"expected 'pilot_pending' when no run record, got {result!r}"
    )


def test_missing_run_record_fails_closed(tmp_path):
    """check_pilot_record with no record file returns a non-empty problem list."""
    import pilot
    block = {
        "type": "pilot_phase",
        "id": "test.pilot",
        "gate_thresholds": {"deadline": "2026-12-31", "eligible_count": 1},
        "eligibility": "test",
        "dispositions": ["pilot_pass"],
    }
    # tmp_path has no goals/pilot-records/ directory at all
    problems = pilot.check_pilot_record(tmp_path, block)
    assert problems, (
        f"expected non-empty problems when record absent (fail closed), got: {problems}"
    )


def test_stale_run_record_fails_closed(tmp_path):
    """A record whose deadline has passed without a terminal disposition returns non-empty."""
    import pilot
    block = {
        "type": "pilot_phase",
        "id": "test.stale",
        "gate_thresholds": {"deadline": "2020-01-01", "eligible_count": 1},
        "eligibility": "test",
        "dispositions": ["pilot_pass"],
    }
    record = {"disposition": "pilot_pending", "eligible_count": 0}
    records_dir = tmp_path / "goals" / "pilot-records"
    records_dir.mkdir(parents=True)
    (records_dir / "test-stale.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    problems = pilot.check_pilot_record(tmp_path, block)
    assert problems, (
        f"expected non-empty problems for stale record (deadline 2020-01-01 passed), "
        f"got: {problems}"
    )


def test_disposition_enum_validated(tmp_path):
    """A record with a disposition outside the known enum returns a problem."""
    import pilot
    block = {
        "type": "pilot_phase",
        "id": "test.enum",
        "gate_thresholds": {"deadline": "2026-12-31", "eligible_count": 1},
        "eligibility": "test",
        "dispositions": ["pilot_pass"],
    }
    record = {"disposition": "unknown_disposition_xyz", "eligible_count": 0}
    records_dir = tmp_path / "goals" / "pilot-records"
    records_dir.mkdir(parents=True)
    (records_dir / "test-enum.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    problems = pilot.check_pilot_record(tmp_path, block)
    assert any("disposition" in p or "unknown" in p for p in problems), (
        f"expected a disposition-enum error, got: {problems}"
    )


# ---------------------------------------------------------------------------
# preflight.check_pilot_phase() integration
# ---------------------------------------------------------------------------

def test_check_pilot_phase_skips_when_no_block(tmp_path, monkeypatch):
    """check_pilot_phase skips cleanly (no raise) when no pilot_phase block exists."""
    (tmp_path / "decisions").mkdir()
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    # Must not raise
    preflight.check_pilot_phase()


def test_check_pilot_phase_passes_when_pilot_pending_no_record(tmp_path, monkeypatch):
    """check_pilot_phase passes when block is pilot_pending and no run record exists."""
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    adr = decisions / "0099-test-pilot.md"
    adr.write_text(
        "# Test pilot ADR\n"
        "```keel-binding\n"
        'type = "pilot_phase"\n'
        'id = "test.ok"\n'
        'gate_thresholds = { deadline = "2026-12-31", eligible_count = 1 }\n'
        'eligibility = "test eligibility"\n'
        'dispositions = ["pilot_pass"]\n'
        'status = "pilot_pending"\n'
        "```\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    # No run record file -> should pass silently
    preflight.check_pilot_phase()


def test_check_pilot_phase_raises_on_wrong_status(tmp_path, monkeypatch):
    """check_pilot_phase raises when a block has a non-pilot_pending status."""
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    adr = decisions / "0099-test-pilot.md"
    adr.write_text(
        "# Test pilot ADR\n"
        "```keel-binding\n"
        'type = "pilot_phase"\n'
        'id = "test.wrong"\n'
        'gate_thresholds = { deadline = "2026-12-31", eligible_count = 1 }\n'
        'eligibility = "test eligibility"\n'
        'dispositions = ["pilot_pass"]\n'
        'status = "pilot_pass"\n'  # claiming pass without a valid run record
        "```\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_pilot_phase()


def test_check_pilot_phase_raises_on_malformed_record(tmp_path, monkeypatch):
    """check_pilot_phase raises when a pilot_pending block has a malformed run record."""
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    adr = decisions / "0099-test-pilot.md"
    adr.write_text(
        "# Test pilot ADR\n"
        "```keel-binding\n"
        'type = "pilot_phase"\n'
        'id = "test.malformed"\n'
        'gate_thresholds = { deadline = "2026-12-31", eligible_count = 1 }\n'
        'eligibility = "test eligibility"\n'
        'dispositions = ["pilot_pass"]\n'
        'status = "pilot_pending"\n'
        "```\n",
        encoding="utf-8",
    )
    # Create a malformed run record file
    records_dir = tmp_path / "goals" / "pilot-records"
    records_dir.mkdir(parents=True)
    (records_dir / "test-malformed.json").write_text(
        "not valid json {{{", encoding="utf-8"
    )
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_pilot_phase()
