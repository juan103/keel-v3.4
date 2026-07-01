"""
Tests for harness_ledger.py -- append-only .harness-ledger.jsonl

TDD: these tests are written BEFORE the implementation.
All four tests must be green after implementation.
"""

import json
import sys
from pathlib import Path

import pytest

# Allow running from keel_v3.4/ directory.
sys.path.insert(0, str(Path(__file__).parents[3]))

import harness_ledger


# ---------------------------------------------------------------------------
# test_append_is_additive
# Two appends => read returns 2 records, in order.
# ---------------------------------------------------------------------------

def test_append_is_additive(tmp_path):
    rec1 = harness_ledger.contract_hash_record("abc123")
    rec2 = harness_ledger.gate_run_record("PASS", 0.95)

    harness_ledger.append(tmp_path, rec1)
    harness_ledger.append(tmp_path, rec2)

    records = harness_ledger.read(tmp_path)
    assert len(records) == 2
    assert records[0]["kind"] == "contract_hash"
    assert records[1]["kind"] == "gate_run"


# ---------------------------------------------------------------------------
# test_records_are_valid_json_lines
# Each line in the ledger file parses as JSON; keys are sorted (canonical).
# ---------------------------------------------------------------------------

def test_records_are_valid_json_lines(tmp_path):
    harness_ledger.append(tmp_path, harness_ledger.contract_hash_record("deadbeef"))
    harness_ledger.append(tmp_path, harness_ledger.resnapshot_record("fixture edit"))

    ledger_path = tmp_path / "goals" / ".harness-ledger.jsonl"
    lines = ledger_path.read_text(encoding="ascii").splitlines()

    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)  # raises if not valid JSON
        assert isinstance(obj, dict)
        # Canonical: keys must be sorted (json.dumps sort_keys=True)
        assert line == json.dumps(obj, sort_keys=True)


# ---------------------------------------------------------------------------
# test_cut_event_roundtrips
# A cut_record appended then read back equals the original.
# ---------------------------------------------------------------------------

def test_cut_event_roundtrips(tmp_path):
    original = harness_ledger.cut_record(
        hazard="H-ADV-1",
        reason="detector missed two escape variants"
    )
    harness_ledger.append(tmp_path, original)

    records = harness_ledger.read(tmp_path)
    assert len(records) == 1
    assert records[0] == original
    assert records[0]["kind"] == "cut"
    assert records[0]["hazard"] == "H-ADV-1"
    assert records[0]["reason"] == "detector missed two escape variants"


# ---------------------------------------------------------------------------
# test_append_never_truncates
# Appending to an existing ledger preserves prior records.
# ---------------------------------------------------------------------------

def test_append_never_truncates(tmp_path):
    # Pre-seed the ledger with one record written directly.
    ledger_path = tmp_path / "goals" / ".harness-ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    prior = {"kind": "prior", "note": "already here"}
    ledger_path.write_text(json.dumps(prior, sort_keys=True) + "\n", encoding="ascii")

    # Now append via the module -- must NOT truncate.
    harness_ledger.append(tmp_path, harness_ledger.resnapshot_record("keyword set update"))

    records = harness_ledger.read(tmp_path)
    assert len(records) == 2
    assert records[0] == prior
    assert records[1]["kind"] == "resnapshot"
