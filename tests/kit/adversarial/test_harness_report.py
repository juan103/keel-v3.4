"""test_harness_report.py -- the report + the 11 mandatory printed residues (Phase 3.5d Task 2).

Verifies:
  - all 11 mandatory residue fields are present + non-empty in build_report;
  - emit() REFUSES to write a report missing/emptying a residue (gate FAILURE);
  - the report pins the live contract hash + the 7/8 coverage;
  - assert_gate_3_5 passes on the real repo and fails when a residue is dropped.

ASCII-only. Stdlib only (test-side).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# keel_v3.4/ root is parents[3]: [0]=adversarial [1]=kit [2]=tests [3]=keel_v3.4
_KIT_ROOT = str(Path(__file__).resolve().parents[3])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import harness_report as hr  # noqa: E402
import harness_contract as hc  # noqa: E402

_ROOT = Path(_KIT_ROOT)


def test_all_11_residues_present_nonempty():
    report = hr.build_report(_ROOT)
    residues = report["residues"]
    assert len(hr.RESIDUE_FIELDS) == 11, "expected exactly 11 mandatory residue fields"
    for f in hr.RESIDUE_FIELDS:
        assert f in residues, "residue missing from report: {}".format(f)
        assert str(residues[f]).strip(), "residue empty in report: {}".format(f)


def test_missing_residue_fails(tmp_path, monkeypatch):
    """emit() must RAISE if a mandatory residue is missing (detect-don't-pretend in print)."""
    good = hr.build_report(_ROOT)

    def _drop_a_residue(repo_root):
        r = dict(good)
        r["residues"] = {k: v for k, v in good["residues"].items()
                         if k != "observable_faithfulness"}
        return r

    monkeypatch.setattr(hr, "build_report", _drop_a_residue)
    with pytest.raises(AssertionError):
        hr.emit(_ROOT, tmp_path / "report.json")


def test_empty_residue_fails(tmp_path, monkeypatch):
    good = hr.build_report(_ROOT)

    def _empty_a_residue(repo_root):
        r = dict(good)
        r["residues"] = dict(good["residues"])
        r["residues"]["gate_execution_audit"] = "   "  # whitespace == empty
        return r

    monkeypatch.setattr(hr, "build_report", _empty_a_residue)
    with pytest.raises(AssertionError):
        hr.emit(_ROOT, tmp_path / "report.json")


def test_report_pins_contract_hash():
    report = hr.build_report(_ROOT)
    assert report["contract_hash"] == hc.contract_hash(_ROOT)
    assert report["contract_hash"], "contract_hash must be non-empty (contract present)"


def test_gate_coverage_in_report():
    report = hr.build_report(_ROOT)
    cov = report["gate_coverage"]
    assert cov["eligible"] == 7 and cov["total"] == 8
    assert any("reachability" in str(c).lower() for c in cov["cuts"])


def test_emit_writes_valid_report(tmp_path):
    out = tmp_path / "report.json"
    hr.emit(_ROOT, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert set(loaded["residues"].keys()) == set(hr.RESIDUE_FIELDS.keys())


def test_assert_gate_3_5_passes():
    # The real repo satisfies the in-boundary Gate-3.5 conjunction.
    hr.assert_gate_3_5(_ROOT)


def test_assert_gate_3_5_fails_on_missing_residue(monkeypatch):
    good = hr.build_report(_ROOT)

    def _drop(repo_root):
        r = dict(good)
        r["residues"] = {k: v for k, v in good["residues"].items()
                         if k != "ledger_integrity_scope"}
        return r

    monkeypatch.setattr(hr, "build_report", _drop)
    with pytest.raises(AssertionError):
        hr.assert_gate_3_5(_ROOT)
