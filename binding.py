"""
keel-binding TOML block extraction and falsifier consistency checking.

Spec: ../proposal_v3.md "v3.SPINE.A — §0 enriched: prose, binding-ADR text,
                        executable check, with mechanical drift detection"

A keel-binding block is a fenced TOML block in a decisions/*.md file:

    ```keel-binding
    type = "statistical_inference"  # or "behavioral"
    id = "falsifier.primary"
    statistic = "..."   # required for type = statistical_inference
    null = "..."        # required for type = statistical_inference
    alpha = 0.05        # required for type = statistical_inference
    p_value = "..."     # required for type = statistical_inference
    behavior = "..."    # required for type = behavioral
    test = "..."        # required for type = behavioral
    rejected = ["canonical_token", ...]      # optional, for cross-block consistency
    rejected_prose = ["surface form", ...]   # optional, for Layer 2 GOALS.md scan
    ```

The check has two layers:

  Layer 1 — structural metadata validation: TOML parses; type/id present;
            type-required fields present; rejected canonical tokens do not
            appear as active values (statistic / null / behavior) in any
            other block in the SAME ADR.

  Layer 2 — narrow GOALS.md prose scan: for any rejected_prose surface form,
            scan goals/GOALS.md ## Falsifier section as plain text
            (case-insensitive substring). Match → fail.

Per ADR-0006: TOML, parsed via stdlib tomllib (Python 3.11+).
Per ADR-0007: this is a presence-and-structure check, not a quality check.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

# Match the literal fenced opener at the start of a line. Allow trailing
# whitespace before the newline.
_FENCE_OPEN = re.compile(r"^```keel-binding[ \t]*$", re.MULTILINE)

# Match a full keel-binding block (opener + body + closing fence).
_FULL_BLOCK = re.compile(
    r"^```keel-binding[ \t]*\r?\n(.*?)^```[ \t]*\r?$",
    re.DOTALL | re.MULTILINE,
)

# Schema: which fields each `type` requires beyond `type` and `id`.
REQUIRED_FIELDS_BY_TYPE: dict[str, list[str]] = {
    "statistical_inference": ["statistic", "null", "alpha", "p_value"],
    "behavioral": ["behavior", "test"],
    "frame_validity": [
        "inferential_claim",
        "machinery_requirements",
        "audit_artifact",
        "author_verdict",
        "dispositions",
    ],
    "pilot_phase": ["gate_thresholds", "eligibility", "dispositions"],
}

# Which fields hold "active" canonical tokens — used for the rejected-token
# cross-block consistency check.
ACTIVE_FIELDS_BY_TYPE: dict[str, list[str]] = {
    "statistical_inference": ["statistic", "null"],
    "behavioral": ["behavior"],
    "frame_validity": [],
    "pilot_phase": [],
}

# Valid runtime_role enum values.
_RUNTIME_ROLES = frozenset({"author", "orchestrator", "subprocess"})


def extract_keel_binding_blocks(path: Path) -> list[dict]:
    """Find every fenced keel-binding TOML block in `path` and return parsed dicts.

    Raises ValueError on malformed TOML, naming the file path so the failure
    location is immediately findable.
    """
    text = path.read_text(encoding="utf-8")
    blocks: list[dict] = []
    for match in _FULL_BLOCK.finditer(text):
        body = match.group(1)
        try:
            block = tomllib.loads(body)
        except tomllib.TOMLDecodeError as e:
            line_in_file = text[: match.start()].count("\n") + 1
            raise ValueError(
                f"malformed keel-binding TOML at {path} (~line {line_in_file}): {e}"
            ) from e
        blocks.append(block)
    return blocks


def validate_block(block: dict) -> list[str]:
    """Layer 1 structural validation. Returns list of error messages; empty == valid."""
    errors: list[str] = []
    if "type" not in block:
        errors.append("missing required field: type")
        return errors
    block_type = block["type"]
    if block_type not in REQUIRED_FIELDS_BY_TYPE:
        errors.append(
            f"unknown type: {block_type!r} "
            f"(known types: {sorted(REQUIRED_FIELDS_BY_TYPE)})"
        )
        return errors
    if "id" not in block:
        errors.append("missing required field: id")
    for field in REQUIRED_FIELDS_BY_TYPE[block_type]:
        if field not in block:
            errors.append(
                f"missing required field for type={block_type!r}: {field}"
            )
    rr = block.get("runtime_role")
    if rr is not None and rr not in _RUNTIME_ROLES:
        errors.append(
            f"runtime_role '{rr}' not in {sorted(_RUNTIME_ROLES)}")
    return errors


def get_active_values(block: dict) -> set[str]:
    """Return the canonical tokens this block names as active.

    Used for the rejected-token cross-block consistency check.
    """
    block_type = block.get("type")
    if block_type not in ACTIVE_FIELDS_BY_TYPE:
        return set()
    return {
        block[field]
        for field in ACTIVE_FIELDS_BY_TYPE[block_type]
        if field in block and isinstance(block[field], str)
    }


def find_binding_adrs(repo_root: Path) -> list[Path]:
    """Find decisions/**/*.md files containing at least one keel-binding fence opener."""
    decisions = repo_root / "decisions"
    if not decisions.is_dir():
        return []
    result: list[Path] = []
    for md in decisions.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _FENCE_OPEN.search(text):
            result.append(md)
    return sorted(result)


def _extract_section(text: str, section_name: str) -> str | None:
    """Return the body of a `## <section_name>` section, or None if not present.

    The section ends at the next `## ` heading at the same level, or end of file.
    """
    pattern = (
        rf"^##[ \t]+{re.escape(section_name)}[ \t]*\r?\n(.*?)(?=^##[ \t]|\Z)"
    )
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else None


def check_falsifier_consistency(repo_root: Path) -> list[str]:
    """Run Layer 1 + Layer 2 falsifier consistency checks.

    Returns list of error messages. Empty list means OK. The caller (typically
    preflight.py) raises if the list is non-empty.

    Skip behavior: if no decisions/*.md contains a keel-binding block (i.e.,
    Dimension 1 == precheck), return [] immediately. This is the documented
    skip in proposal_v3.md and ADR-0002 (v3 must not break v2 projects that
    have no binding ADR).
    """
    errors: list[str] = []

    binding_adrs = find_binding_adrs(repo_root)
    if not binding_adrs:
        return []

    # Layer 1, part A: extract and validate each block.
    blocks_by_adr: dict[Path, list[dict]] = {}
    for adr in binding_adrs:
        try:
            blocks = extract_keel_binding_blocks(adr)
        except ValueError as e:
            errors.append(str(e))
            continue
        for block in blocks:
            block_errors = validate_block(block)
            for err in block_errors:
                errors.append(f"{adr}: {err}")
        blocks_by_adr[adr] = blocks

    # Layer 1, part B: rejected canonical tokens must not appear as active
    # values in any OTHER block in the SAME ADR.
    for adr, blocks in blocks_by_adr.items():
        for i, block in enumerate(blocks):
            rejected = set(block.get("rejected", []))
            if not rejected:
                continue
            for j, other in enumerate(blocks):
                if i == j:
                    continue
                active = get_active_values(other)
                clash = rejected & active
                if clash:
                    errors.append(
                        f"{adr}: block {block.get('id', '?')!r} rejects "
                        f"{sorted(clash)} but they are active in block "
                        f"{other.get('id', '?')!r}"
                    )

    # Layer 2: narrow GOALS.md prose scan against rejected_prose surface forms.
    goals = repo_root / "goals" / "GOALS.md"
    if goals.exists():
        try:
            goals_text = goals.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            goals_text = ""
        falsifier = _extract_section(goals_text, "Falsifier")
        if falsifier:
            falsifier_lower = falsifier.lower()
            for adr, blocks in blocks_by_adr.items():
                for block in blocks:
                    rejected_prose = block.get("rejected_prose", [])
                    for surface in rejected_prose:
                        if not isinstance(surface, str):
                            continue
                        if surface.lower() in falsifier_lower:
                            errors.append(
                                f"GOALS.md ## Falsifier contains rejected_prose "
                                f"surface {surface!r} (from block "
                                f"{block.get('id', '?')!r} in {adr})"
                            )

    return errors


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    errs = check_falsifier_consistency(root)
    if errs:
        for e in errs:
            print(f"[FAIL] {e}")
        sys.exit(1)
    print("[OK] falsifier consistency check passed")
