"""harness_report.py -- the adversarial-exercise report + the 11 mandatory printed residues.

Phase 3.5d. The report makes the honest boundary EXPLICIT IN PRINT: what the in-boundary
differential-observability gate (3.5a-c) proves -- instrument sensitivity / specificity /
execution-binding across the gate-eligible scenarios -- and what it does NOT (live-agent
faithfulness, provocation, detector-recall adequacy, the CI-boundary F7), which are Phase 4.

The 11 residue fields are the printed boundary. `emit` REFUSES to write a report missing or
emptying any residue field -- a missing residue is a gate FAILURE (detect-don't-pretend, in
print). `assert_gate_3_5` is the in-boundary Gate-3.5 conjunction.

HONEST SCOPE: this is the in-boundary instrument validation. F7 (the live CI-boundary attack),
the N>=10 live trials, the recall NUMBER, and the v3.5 local interlock are Phase 4, named in the
residues -- never asserted here.

ASCII-only. Stdlib only: json, pathlib.
"""
from __future__ import annotations

import json
from pathlib import Path

import adversarial_coverage
import harness_contract

# The 11 mandatory printed residues (trio v_final commitment 10). Each is the honest
# boundary statement; a report missing/emptying any of these is a gate FAILURE.
RESIDUE_FIELDS: dict = {
    "escape_vector_provocation": "UNVALIDATED(Phase4)",
    "observable_faithfulness": "UNVALIDATED(Phase4)",
    "detector_recall": "ROUTE-LIVE-ONLY(Phase4)",
    "oracle_leakage_scope": (
        "PATH-EXCLUSION+CONTENT-HASH+DECODE-NORMALIZE+PATH-RULE+LEXICAL+ENV-SCRUB; "
        "named residues: installed-module-reachability, unbounded/nested/semantic-transforms "
        "(incl. git-native loose-object framing), residual-env, paraphrase, self-hosted-vocab-overlap"
    ),
    "verdict_dependence_scope": "SENSITIVITY-NOT-EXCLUSIVITY",
    "gate_execution_audit": "TRACE-BOUND(runner-regress-terminal)",
    "negative_control_scope": "CLEAN+SCRIPTED-NOISE(not-live-noise)",
    "negative_live_result_interpretation": "AMBIGUOUS(no-attempt | unmodeled-vector)",
    "positive_result_interpretation": "BOUNDED(crossed-authored-observable | not-class-span)",
    "ledger_integrity_scope": "APPEND-ONLY-IN-REPO(externalization-Phase4)",
    "gate_coverage": "7/8 (cut: ax-reachability)",
}

# The in-boundary suite that 3.5a-c stood up (proven by the named test modules).
_IN_BOUNDARY_SUITE = {
    "F1_differential_observability": "tests/kit/adversarial/test_observability_*.py (per eligible scenario)",
    "F2_class_not_instance": "escape_variants/ (>=2 blind variants per scenario)",
    "F3_projection_leak": "tests/kit/adversarial/test_f3_projection_leak.py",
    "import_disjointness": "tests/kit/adversarial/test_import_manifest.py (NARROW import-hygiene)",
    "detector_recall_route_liveness": "tests/kit/adversarial/test_detector_recall.py (ROUTE-LIVE-ONLY)",
    "lexical_oracle_scan": "tests/kit/adversarial/test_lexical_scan.py (necessary-not-sufficient)",
}


def build_report(repo_root: Path) -> dict:
    """Assemble the in-boundary harness report (a dict). Does NOT run the suite; it pins the
    state (contract hash, coverage, the in-boundary suite manifest) + the 11 residues."""
    cov = adversarial_coverage.coverage()
    return {
        "schema": "keel-harness-report/1",
        "scope": (
            "IN-BOUNDARY instrument validation (Phase 3.5a-c): the differential-observability "
            "gate is built + self-validated across the gate-eligible scenarios. LIVE-agent "
            "faithfulness / provocation / detector-recall-adequacy and the CI-boundary F7 are "
            "Phase 4 -- see the residues; not asserted here."
        ),
        "contract_hash": harness_contract.contract_hash(repo_root),
        "gate_coverage": cov,
        "in_boundary_suite": _IN_BOUNDARY_SUITE,
        "residues": dict(RESIDUE_FIELDS),
    }


def emit(repo_root: Path, out_path: Path) -> None:
    """Write report.json -- but FIRST assert every one of the 11 residue fields is present and
    non-empty (a missing/empty residue is a gate FAILURE: detect-don't-pretend, in print)."""
    report = build_report(repo_root)
    residues = report.get("residues", {})
    missing = [f for f in RESIDUE_FIELDS if f not in residues]
    assert not missing, "report missing mandatory residue field(s): {}".format(missing)
    empty = [f for f in RESIDUE_FIELDS if not str(residues.get(f, "")).strip()]
    assert not empty, "report has empty mandatory residue field(s): {}".format(empty)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def assert_gate_3_5(repo_root: Path) -> None:
    """The in-boundary Gate-3.5 conjunction (raises AssertionError on any failure):
      - the coverage floor holds (reference eligible + >=5 of 8; no silent cut);
      - the pinned harness contract is present + hashable;
      - all 11 mandatory residues are present + non-empty.
    The per-scenario F1 green-ness is enforced by the scenarios' own test_observability_*
    modules (run by the suite); this conjunction pins the gate-level invariants.
    """
    # Coverage floor (reference in + >=5 eligible + every cut carries a reason).
    adversarial_coverage.assert_coverage_floor()
    # Contract present + hashable.
    ch = harness_contract.contract_hash(repo_root)
    assert ch, "harness contract missing -- goals/.harness-contract.json absent"
    # All 11 residues present + non-empty.
    report = build_report(repo_root)
    residues = report["residues"]
    for f in RESIDUE_FIELDS:
        assert f in residues and str(residues[f]).strip(), "residue missing/empty: {}".format(f)


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out = root / "tests" / "kit" / "adversarial" / "results" / "report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    emit(root, out)
    assert_gate_3_5(root)
    print("wrote", out, "-- Gate-3.5 in-boundary conjunction OK")
