"""pilot.py -- pilot_phase gate evaluation (KEEL v3.4, Phase 3, Task 2).

Reads pilot run records and evaluates whether a pilot_phase gate has fired.
At ship time, no run record exists; the binding status is pilot_pending.
This module fail-closes when any present run record is absent, stale, or malformed.

ASCII-only strings throughout.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

# Valid pilot disposition strings.
DISPOSITIONS: frozenset[str] = frozenset({
    "pilot_pass",
    "pilot_fail_falsifier",
    "pilot_fail_unused",
    "extend",
    "pilot_pending",
})


def record_path(repo_root: Path, block: dict) -> Path:
    """Derive the conventional run-record file path from the block id.

    Convention: goals/pilot-records/<normalized-id>.json, where
    normalized-id replaces '/' and '.' with '-'.
    """
    block_id = block.get("id", "unknown").replace("/", "-").replace(".", "-")
    return repo_root / "goals" / "pilot-records" / (block_id + ".json")


def classify(record: "dict | None", block: dict) -> str:
    """Return the pilot disposition given a run record (or None if absent).

    None  -> pilot_pending (ship-time: no run yet, cannot claim pilot_pass).
    Present record -> validated against gate_thresholds before honoring pilot_pass;
    if thresholds not met, maps to the honest disposition.
    """
    if record is None:
        return "pilot_pending"
    disposition = record.get("disposition", "")
    if disposition not in DISPOSITIONS:
        return "pilot_pending"   # unknown disposition -> conservatively pending
    if disposition == "pilot_pass":
        # Validate against gate_thresholds before honoring pilot_pass.
        thresholds = block.get("gate_thresholds", {})
        deadline_str = thresholds.get("deadline", "")
        threshold_count = thresholds.get("eligible_count", 1)
        if deadline_str:
            try:
                deadline = date.fromisoformat(deadline_str)
                if date.today() > deadline:
                    # Deadline passed -- cannot silently pilot_pass without re-evaluation.
                    return "pilot_fail_falsifier"
            except ValueError:
                return "pilot_pending"   # malformed deadline
        record_count = record.get("eligible_count", 0)
        if record_count < threshold_count:
            return "pilot_pending"   # eligible count not met
    return disposition


def check_pilot_record(repo_root: Path, block: dict) -> list[str]:
    """Validate a pilot run record. Returns list of problems; empty -> valid.

    Fail-closed: if the record file is absent, malformed, stale, or carries
    an unknown disposition, returns a non-empty problem list.  The caller
    (check_pilot_phase in preflight.py) only invokes this when the record
    file is already known to exist; however, this function itself also
    reports absence so it can be called directly in tests.
    """
    problems: list[str] = []
    rp = record_path(repo_root, block)

    if not rp.exists():
        problems.append(f"pilot record absent (fail closed): {rp}")
        return problems

    try:
        record = json.loads(rp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        problems.append(f"pilot record malformed ({rp}): {e}")
        return problems

    if not isinstance(record, dict):
        problems.append(
            f"pilot record must be a JSON object, got {type(record).__name__} ({rp})"
        )
        return problems

    # Validate disposition.
    disposition = record.get("disposition", "")
    if not disposition:
        problems.append(f"pilot record missing 'disposition' field ({rp})")
        return problems
    if disposition not in DISPOSITIONS:
        problems.append(
            f"pilot record has unknown disposition {disposition!r} "
            f"(expected one of {sorted(DISPOSITIONS)}) ({rp})"
        )
        return problems

    # Stale-deadline check: if deadline passed and disposition is non-terminal,
    # the record is stale and a fresh evaluation is required.
    thresholds = block.get("gate_thresholds", {})
    deadline_str = thresholds.get("deadline", "")
    if deadline_str:
        try:
            deadline = date.fromisoformat(deadline_str)
        except ValueError:
            problems.append(
                f"gate_thresholds.deadline is not a valid ISO date: {deadline_str!r}"
            )
            return problems
        today = date.today()
        _terminal = frozenset({"pilot_pass", "pilot_fail_falsifier", "pilot_fail_unused"})
        if today > deadline and disposition not in _terminal:
            problems.append(
                f"pilot deadline {deadline_str} has passed but disposition is "
                f"{disposition!r} (non-terminal); a fresh evaluation is required"
            )

    # Eligible-count check for pilot_pass claims.
    threshold_count = thresholds.get("eligible_count", 1)
    record_count = record.get("eligible_count", 0)
    if disposition == "pilot_pass" and record_count < threshold_count:
        problems.append(
            f"pilot record claims pilot_pass but eligible_count {record_count} < "
            f"gate threshold {threshold_count}"
        )

    return problems
