"""KEEL v3.4 commitment-lock (Phase 0: snapshot tool; guard check is Phase 3 unwired)."""
from __future__ import annotations
import hashlib, json, re, subprocess, tomllib
from pathlib import Path
from hazard_coverage import parse_matrix


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _section(text: str, name: str) -> str:
    m = re.search(rf"^##\s+{re.escape(name)}.*?(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(0) if m else ""


def _sha_file(path: Path) -> "str | None":
    """Return sha256 hex digest of file bytes, or None if the file is absent."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_preflight_checks(pf_text: str) -> list[str]:
    """Extract check function names from the checks=[...] list in preflight.py source.

    Uses a single regex pass over the list body only, so stray occurrences of
    check_* elsewhere in the file are not captured.
    """
    m = re.search(r"checks\s*=\s*\[(.*?)\]", pf_text, re.S)
    if not m:
        return []
    return re.findall(r"\bcheck_\w+\b", m.group(1))


# ---------------------------------------------------------------------------
# keel-lock-override ADR detection
# ---------------------------------------------------------------------------

_LOCK_OVERRIDE_RE = re.compile(
    r"^```keel-lock-override[ \t]*\r?\n(.*?)^```[ \t]*\r?$",
    re.DOTALL | re.MULTILINE,
)


def _find_lock_override_adrs(repo_root: Path) -> list[dict]:
    """Return parsed keel-lock-override blocks from accepted ADRs under decisions/."""
    decisions = repo_root / "decisions"
    if not decisions.is_dir():
        return []
    overrides: list[dict] = []
    for md in sorted(decisions.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # Only accepted ADRs carry authority.
        if not re.search(r"\*\*Status:\*\*\s*accepted", text, re.I):
            continue
        for m in _LOCK_OVERRIDE_RE.finditer(text):
            try:
                block = tomllib.loads(m.group(1))
            except Exception:
                continue
            if block.get("lock_override") is True:
                overrides.append(block)
    return overrides


def _authorized_keys(overrides: list[dict]) -> set[str]:
    result: set[str] = set()
    for ov in overrides:
        for k in (ov.get("authorized_keys") or []):
            result.add(str(k))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def snapshot_lock(repo_root: Path) -> dict:
    """Compute the current locked surface and return it as a serialisable dict.

    Broadened in Phase 3 (Task 3) to add preflight_sha, registered_checks
    (full list), attest_keys_sha, runtime_roles_sha, harness_contract_sha.
    """
    goals = (repo_root / "goals" / "GOALS.md").read_text(encoding="utf-8")
    sections = {
        n: hashlib.sha256(_section(goals, n).encode("utf-8")).hexdigest()
        for n in ("Falsifier", "Commitments")
    }
    rc_rows = [
        {
            "hazard_id": r.hazard_id,
            "refusal_critical": r.refusal_critical,
            "falsifier_layer": r.falsifier_layer,
            "roadmap_defense_distance": r.roadmap_defense_distance,
            "exercise_scenario": r.exercise_scenario,
        }
        for r in parse_matrix(repo_root)
        if r.refusal_critical and r.status != "accepted-risk"
    ]
    pf_path = repo_root / "preflight.py"
    pf_bytes = pf_path.read_bytes()
    preflight_sha = hashlib.sha256(pf_bytes).hexdigest()
    registered = _parse_preflight_checks(pf_bytes.decode("utf-8"))

    return {
        "goals_sections": sections,
        "refusal_critical_rows": rc_rows,
        "registered_checks": registered,
        "preflight_sha": preflight_sha,
        "attest_keys_sha": _sha_file(repo_root / "goals" / ".attest-keys.json"),
        "runtime_roles_sha": _sha_file(repo_root / "goals" / ".runtime-roles.json"),
        "harness_contract_sha": _sha_file(repo_root / "goals" / ".harness-contract.json"),
    }


def current_surface(repo_root: Path) -> dict:
    """Alias of snapshot_lock: return the live locked surface for repo_root."""
    return snapshot_lock(repo_root)


def diff_surface(snapshot: dict, current: dict) -> list[str]:
    """Return a list of key paths where snapshot and current diverge.

    Key path format:
      goals_sections.<SectionName>
      refusal_critical_rows.<hazard_id>
      registered_checks
      preflight_sha
      attest_keys_sha
      runtime_roles_sha
      harness_contract_sha
    """
    diverged: list[str] = []

    # goals_sections — compare each section hash independently
    snap_sects = snapshot.get("goals_sections") or {}
    curr_sects = current.get("goals_sections") or {}
    for sect in ("Falsifier", "Commitments"):
        if snap_sects.get(sect) != curr_sects.get(sect):
            diverged.append(f"goals_sections.{sect}")

    # refusal_critical_rows — compare by hazard_id; any field change counts
    snap_rows = {r["hazard_id"]: r for r in (snapshot.get("refusal_critical_rows") or [])}
    curr_rows = {r["hazard_id"]: r for r in (current.get("refusal_critical_rows") or [])}
    for hid in sorted(set(snap_rows) | set(curr_rows)):
        if snap_rows.get(hid) != curr_rows.get(hid):
            diverged.append(f"refusal_critical_rows.{hid}")

    # registered_checks — compare as sorted sets so insertion order doesn't matter
    sv = sorted(snapshot.get("registered_checks") or [])
    cv = sorted(current.get("registered_checks") or [])
    if sv != cv:
        diverged.append("registered_checks")

    # scalar sha fields
    for key in ("preflight_sha", "attest_keys_sha", "runtime_roles_sha", "harness_contract_sha"):
        if snapshot.get(key) != current.get(key):
            diverged.append(key)

    return diverged


def _adjudicate(diverged: list[str], overrides: list[dict], suffix: str = "") -> list[str]:
    """Apply GP-5 + override logic to diverged key paths; return problems.

    This is the SINGLE source of truth for the refusal-critical-vs-noncritical +
    lock-override adjudication.  Both the snapshot-vs-current path
    (check_commitment_lock_impl) and the head-vs-merge-base path
    (merge_base_divergence) call it so GP-5 semantics can never drift between
    them.  `suffix` is appended to each message for caller context
    (e.g. " vs merge base").
    """
    authorized = _authorized_keys(overrides)
    problems: list[str] = []
    for key in diverged:
        if key.startswith("refusal_critical_rows."):
            # GP-5: refusal-critical divergence NEVER auto-trusted in v3.4.
            # No out-of-band adjudication channel exists; lock_override ADRs
            # cannot exempt refusal-critical rows.
            problems.append(f"refusal-critical divergence{suffix}: {key}")
        elif key in authorized:
            pass  # non-critical element explicitly authorized by accepted ADR
        else:
            problems.append(f"locked surface diverged{suffix}: {key}")
    return problems


def check_commitment_lock_impl(repo_root: Path) -> list[str]:
    """Session-mode commitment-lock check (NOT yet wired into preflight -- Task 6).

    Returns a list of problem strings.  Empty list means the locked surface
    matches the committed snapshot.

    Lock-override ADRs (accepted decisions/*.md with a keel-lock-override
    block containing lock_override = true) can authorize non-critical
    divergences.  Refusal-critical divergences always fail (GP-5).
    """
    lock_path = repo_root / "goals" / ".commitment-lock.json"
    if not lock_path.exists():
        return ["lock snapshot missing"]
    snapshot = json.loads(lock_path.read_text(encoding="utf-8"))
    current = current_surface(repo_root)
    diverged = diff_surface(snapshot, current)
    if not diverged:
        return []
    overrides = _find_lock_override_adrs(repo_root)
    return _adjudicate(diverged, overrides)


def merge_base_divergence(repo_root: Path, base_ref: str) -> list[str]:
    """Head-vs-merge-base commitment-lock check (the un-tamperable runner path).

    Reads the locked surface snapshot as it existed at base_ref via
    `git show <base_ref>:goals/.commitment-lock.json`, then compares to
    the current head's live surface.  A file absent at base is treated as
    a divergence requiring adjudication.

    Same GP-5 + override logic as check_commitment_lock_impl.
    """
    root = Path(repo_root)
    lock_relpath = "goals/.commitment-lock.json"
    result = subprocess.run(
        ["git", "show", f"{base_ref}:{lock_relpath}"],
        cwd=root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return [f"lock snapshot absent at merge base ({base_ref})"]
    try:
        snapshot = json.loads(result.stdout)
    except json.JSONDecodeError:
        return [f"lock snapshot at merge base is malformed ({base_ref})"]
    current = current_surface(root)
    diverged = diff_surface(snapshot, current)
    if not diverged:
        return []
    overrides = _find_lock_override_adrs(root)
    # Reuse _adjudicate (single source of truth for GP-5 + override logic);
    # the suffix only adds merge-base context to each message.
    return _adjudicate(diverged, overrides, suffix=" vs merge base")
