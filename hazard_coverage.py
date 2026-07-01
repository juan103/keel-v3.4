"""KEEL v3.4 hazard-coverage spine (Phase 0: parser + audit pin)."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

_ROW = re.compile(r"^\|\s*(hz-[\w-]+)\s*\|\s*(true|false)\s*\|\s*(\w+)\s*\|\s*$")


def audit_v3_3_hazards(repo_root: Path) -> list[dict]:
    """Parse goals/audit-v3.3.md's hazard table into structured records."""
    _audit = repo_root / "goals" / "audit-v3.3.md"
    if not _audit.exists():
        raise FileNotFoundError(f"goals/audit-v3.3.md not found under {repo_root}")
    text = _audit.read_text(encoding="utf-8")
    out: list[dict] = []
    for line in text.splitlines():
        m = _ROW.match(line.strip())
        if m:
            out.append({"id": m.group(1),
                        "refusal_critical": m.group(2) == "true",
                        "severity": m.group(3)})
    return out


def _sha256(path: Path) -> str:
    # Hash is over raw bytes — consistent within a working tree but sensitive to CRLF translation across machines.
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_audit_pin(repo_root: Path) -> list[str]:
    """Fail-closed: file hash must match the pin; hazard set + criticality must match."""
    audit = repo_root / "goals" / "audit-v3.3.md"
    lock_path = repo_root / "goals" / ".audit-lock.json"
    violations: list[str] = []
    if not audit.exists():
        return ["goals/audit-v3.3.md is missing"]
    if not lock_path.exists():
        return ["goals/.audit-lock.json is missing"]
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if _sha256(audit) != lock.get("sha256"):
        violations.append("goals/audit-v3.3.md sha256 does not match the pin in .audit-lock.json")
    pinned = lock.get("hazards", {})
    parsed = {h["id"]: h for h in audit_v3_3_hazards(repo_root)}
    for hid, rec in pinned.items():
        if hid not in parsed:
            violations.append(f"pinned hazard {hid} is absent from audit-v3.3.md")
            continue
        if parsed[hid]["refusal_critical"] != rec["refusal_critical"]:
            violations.append(f"{hid}: refusal_critical differs from pin (silent downgrade)")
        if parsed[hid]["severity"] != rec["severity"]:
            violations.append(f"{hid}: severity differs from pin")
    for hid in parsed:
        if hid not in pinned:
            violations.append(f"audit-v3.3.md hazard {hid} is not in the pin")
    return violations


from dataclasses import dataclass

_EXPECTED_COLS = [
    "hazard_id", "audit_hazard_ref", "refusal_critical",
    "mitigating_check", "check_return_contract",
    "falsifier_strength", "falsifier_layer",
    "proving_test_negative", "proving_test_positive",
    "prevention_proving_test", "prevention_observation",
    "exercise_scenario", "wired_into", "gate_mode",
    "revalidation_interval_days", "status",
    "silent_path_defense_distance", "substantive_residue",
    "roadmap_defense_distance", "independence_basis", "notes",
]


@dataclass
class Row:
    hazard_id: str
    audit_hazard_ref: str
    refusal_critical: bool
    mitigating_check: str
    check_return_contract: str
    falsifier_strength: str
    falsifier_layer: str
    proving_test_negative: str
    proving_test_positive: str
    prevention_proving_test: str
    prevention_observation: str
    exercise_scenario: str
    wired_into: str
    gate_mode: str
    revalidation_interval_days: "int | None"
    status: str
    silent_path_defense_distance: str
    substantive_residue: str
    roadmap_defense_distance: str
    independence_basis: str
    notes: str


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_matrix(repo_root: Path) -> list[Row]:
    text = (repo_root / "goals" / "hazard-coverage.md").read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip().startswith("|")]
    if not lines:
        raise ValueError("hazard-coverage.md: no table found")
    header = _split_row(lines[0])
    if header != _EXPECTED_COLS:
        raise ValueError(f"hazard-coverage.md: columns {header} != expected {_EXPECTED_COLS}")
    rows: list[Row] = []
    for ln in lines[2:]:  # skip header + separator
        cells = _split_row(ln)
        if len(cells) != len(_EXPECTED_COLS):
            raise ValueError(f"hazard-coverage.md: row has {len(cells)} cells, expected {len(_EXPECTED_COLS)}: {ln}")
        d = dict(zip(_EXPECTED_COLS, cells))
        interval = d["revalidation_interval_days"].strip()
        rows.append(Row(
            hazard_id=d["hazard_id"], audit_hazard_ref=d["audit_hazard_ref"],
            refusal_critical=d["refusal_critical"] == "true",
            mitigating_check=d["mitigating_check"],
            check_return_contract=d["check_return_contract"],
            falsifier_strength=d["falsifier_strength"],
            falsifier_layer=d["falsifier_layer"], proving_test_negative=d["proving_test_negative"],
            proving_test_positive=d["proving_test_positive"],
            prevention_proving_test=d["prevention_proving_test"],
            prevention_observation=d["prevention_observation"],
            exercise_scenario=d["exercise_scenario"],
            wired_into=d["wired_into"],
            gate_mode=d["gate_mode"],
            revalidation_interval_days=int(interval) if interval else None,
            status=d["status"], silent_path_defense_distance=d["silent_path_defense_distance"],
            substantive_residue=d["substantive_residue"],
            roadmap_defense_distance=d["roadmap_defense_distance"],
            independence_basis=d["independence_basis"], notes=d["notes"]))
    return rows


def check_hazard_coverage(repo_root: Path) -> list[str]:
    """The falsifier spine. Phase 0: audit pin + no-orphan/no-downgrade against the pinned source.
    (Green-row assertions — proving-test bite, wiring, freshness, live-exercise — land in later phases.)"""
    violations = list(verify_audit_pin(repo_root))
    pinned = {h["id"]: h for h in audit_v3_3_hazards(repo_root)}
    rows = {r.hazard_id: r for r in parse_matrix(repo_root)}
    # Every pinned (v3.3) hazard must appear as a row with matching criticality.
    for hid, rec in pinned.items():
        if hid not in rows:
            violations.append(f"pinned hazard {hid} has no row in hazard-coverage.md")
            continue
        r = rows[hid]
        if r.refusal_critical != rec["refusal_critical"]:
            violations.append(f"{hid}: matrix refusal_critical differs from pin (silent downgrade)")
        if r.audit_hazard_ref != hid:
            violations.append(f"{hid}: audit_hazard_ref '{r.audit_hazard_ref}' does not match its hazard_id")
    # A matrix row claiming an audit_hazard_ref not in the pin is an orphan (residuals use 'n/a').
    for hid, r in rows.items():
        if r.audit_hazard_ref not in ("n/a",) and r.audit_hazard_ref not in pinned:
            violations.append(f"matrix row {hid}: audit_hazard_ref '{r.audit_hazard_ref}' is not in the pinned audit")
    base_path = repo_root / "goals" / ".pending-baseline.json"
    baseline = set()
    if base_path.exists():
        baseline = set(json.loads(base_path.read_text(encoding="utf-8")).get("pending_refusal_critical", []))
    for hid, r in rows.items():
        if not r.refusal_critical:
            continue
        if r.status == "accepted-risk":
            continue  # permitted permanent residual state
        if r.status == "pending" and hid not in baseline:
            violations.append(f"{hid}: refusal-critical row is pending (RED) but not on the Phase-0 pending baseline")
        if r.status == "green" and (
            r.mitigating_check == "pending"
            or r.proving_test_negative == "pending"
            or r.proving_test_positive == "pending"
        ):
            violations.append(
                f"{hid}: refusal-critical row is green but has no wired falsifier "
                f"(mitigating_check/proving tests still pending) — not permitted until the green-row assertions land"
            )
        if r.status not in ("pending", "green", "accepted-risk", "conditional"):
            violations.append(f"{hid}: unknown status '{r.status}'")
    import green_rows
    for hid, r in rows.items():
        if r.status == "green":
            violations += green_rows.validate_green_row(repo_root, r)
    return violations


def render_row_summary(row) -> str:
    """Human-facing one-line summary of a Row.

    Display rule: surfaces silent_path_defense_distance (the executably-verified
    achieved barrier count), NEVER roadmap_defense_distance (the aspirational
    target). Callers must not substitute roadmap_defense_distance for the
    headline distance figure."""
    return (
        f"{row.hazard_id}: status={row.status} "
        f"distance={row.silent_path_defense_distance} "
        f"layer={row.falsifier_layer}/{row.falsifier_strength} "
        f"critical={row.refusal_critical}"
    )
