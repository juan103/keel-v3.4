"""
harness_ledger.py -- append-only harness ledger for KEEL v3.4 Phase 3.5c.

Records every harness contract hash, gate run + outcome, re-snapshot reason,
and CUT event so that exploratory tuning (garden-of-forking-paths) is visible
to replication.

Ledger file: <repo_root>/goals/.harness-ledger.jsonl

APPEND-ONLY invariant: the file is always opened in append mode ("a").
It is NEVER opened with "w", "w+", or any mode that truncates.

Honest bound -- ledger_integrity_scope:
  Append-only in-repo is NOT tamper-proof against history rewrite (git
  reset --hard, force-push, or rebase that drops commits).  The ledger
  provides audit visibility for honest sessions; it does not prevent a
  determined adversary who controls the git history.  This residue is named
  and acknowledged; closing it would require an external, time-stamped
  notarisation service which is out of scope for this phase.

Stdlib only.  ASCII-only output (json.dumps produces ASCII-safe output by
default when ensure_ascii=True, which is the default).
"""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_LEDGER_REL = "goals/.harness-ledger.jsonl"


def _ledger_path(repo_root: Path) -> Path:
    return repo_root / _LEDGER_REL


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def append(repo_root: Path, record: dict) -> None:
    """Append ONE canonical JSON line to the ledger.

    Creates the file (and parent directory) if absent.
    NEVER overwrites or truncates -- opened in append mode ("a") only.
    """
    path = _ledger_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True)  # canonical; ASCII-safe by default
    with open(path, "a", encoding="ascii") as fh:
        fh.write(line + "\n")


def read(repo_root: Path) -> list:
    """Return all records from the ledger (empty list if the file is absent)."""
    path = _ledger_path(repo_root)
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="ascii").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Typed record builders
# Each returns a plain dict with a "kind" field + the payload fields.
# Callers may add extra fields; sort_keys in append() ensures canonical order.
# ---------------------------------------------------------------------------

def contract_hash_record(hash_value: str) -> dict:
    """Record a harness contract hash (gates the locked surface)."""
    return {
        "hash": hash_value,
        "kind": "contract_hash",
    }


def gate_run_record(outcome: str, coverage: float) -> dict:
    """Record a gate run result (outcome: PASS/FAIL/INCONCLUSIVE, coverage fraction)."""
    return {
        "coverage": coverage,
        "kind": "gate_run",
        "outcome": outcome,
    }


def resnapshot_record(reason: str) -> dict:
    """Record a re-snapshot event with a human-readable reason.

    Reasons include: predicate edit, keyword set update, provisional-definition
    change, fixture edit, or any other change that invalidates a prior snapshot.
    """
    return {
        "kind": "resnapshot",
        "reason": reason,
    }


def cut_record(hazard: str, reason: str) -> dict:
    """Record a CUT event (a scenario removed from the eligible set).

    hazard: the hazard identifier (e.g. "H-ADV-1").
    reason: why it was cut (e.g. "detector missed two escape variants").
    """
    return {
        "hazard": hazard,
        "kind": "cut",
        "reason": reason,
    }
