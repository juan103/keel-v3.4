"""Tests for commitment_lock guard functions: check_commitment_lock_impl + merge_base_divergence.

TDD: tests written BEFORE implementation.  Task 3 / Phase 3 M1 (unwired).
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

import pytest
import attest

from commitment_lock import (
    snapshot_lock,
    current_surface,
    diff_surface,
    check_commitment_lock_impl,
    merge_base_divergence,
)

# ---------------------------------------------------------------------------
# Synthetic kit helpers
# ---------------------------------------------------------------------------

_MATRIX_HEADER = (
    "| hazard_id | audit_hazard_ref | refusal_critical | mitigating_check | "
    "check_return_contract | falsifier_strength | falsifier_layer | "
    "proving_test_negative | proving_test_positive | prevention_proving_test | "
    "prevention_observation | exercise_scenario | wired_into | gate_mode | "
    "revalidation_interval_days | status | silent_path_defense_distance | "
    "substantive_residue | roadmap_defense_distance | independence_basis | notes |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
)


def _mk_row(hazard_id: str, refusal_critical: bool = False,
            falsifier_layer: str = "post_hoc", status: str = "green") -> str:
    rc = "true" if refusal_critical else "false"
    return (
        f"| {hazard_id} | n/a | {rc} | mock.check | findings_list | full | "
        f"{falsifier_layer} | n/a | n/a | n/a | n/a | n/a | ci | n/a | 7 | "
        f"{status} | 1 | n/a | 1 | n/a | test |\n"
    )


def _mk_goals(falsifier: str = "Original falsifier text.",
               commitments: str = "Original commitments text.") -> str:
    return f"## Falsifier\n\n{falsifier}\n\n## Commitments\n\n{commitments}\n"


def _mk_preflight(*check_names: str) -> str:
    defs = "\n".join(f"def {n}(): pass" for n in check_names)
    lst = ",\n    ".join(check_names)
    return f"{defs}\n\nchecks = [\n    {lst},\n]\n"


def _mk_lock_override_adr(adr_path: Path, authorized_keys: list[str]) -> None:
    """Write an accepted ADR with a keel-lock-override block."""
    keys_toml = ", ".join(f'"{k}"' for k in authorized_keys)
    adr_path.write_text(
        "# ADR-9999: test override\n\n"
        "**Status:** accepted\n\n"
        "## Decision\n\n"
        "Override granted for testing.\n\n"
        "```keel-lock-override\n"
        "lock_override = true\n"
        f"authorized_keys = [{keys_toml}]\n"
        "```\n",
        encoding="utf-8",
    )


def _build_kit(root: Path, *,
               goals_falsifier: str = "Original falsifier.",
               goals_commitments: str = "Original commitments.",
               check_names: tuple = ("check_example",),
               preflight_src: str | None = None,
               matrix_rows: list[str] | None = None,
               attest_content: str | None = None,
               runtime_roles_content: str | None = None) -> Path:
    """Build a minimal synthetic kit under root."""
    (root / "goals").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(exist_ok=True)
    (root / "decisions").mkdir(exist_ok=True)

    (root / "goals" / "GOALS.md").write_text(
        _mk_goals(goals_falsifier, goals_commitments), encoding="utf-8"
    )
    if attest_content is None:
        attest_content = '{"version": 1, "keys": [], "events": []}'
    (root / "goals" / ".attest-keys.json").write_text(attest_content, encoding="utf-8")

    if runtime_roles_content is None:
        runtime_roles_content = '{"version": 1, "fields": []}'
    (root / "goals" / ".runtime-roles.json").write_text(runtime_roles_content, encoding="utf-8")

    if preflight_src is None:
        preflight_src = _mk_preflight(*check_names)
    (root / "preflight.py").write_text(preflight_src, encoding="utf-8")

    rows = matrix_rows or []
    (root / "goals" / "hazard-coverage.md").write_text(
        "# fixture\n\n" + _MATRIX_HEADER + "".join(rows), encoding="utf-8"
    )
    return root


def _write_snapshot(root: Path) -> dict:
    """Call snapshot_lock, write it to goals/.commitment-lock.json, return it."""
    snap = snapshot_lock(root)
    (root / "goals" / ".commitment-lock.json").write_text(
        json.dumps(snap, indent=2), encoding="utf-8"
    )
    return snap


# ---------------------------------------------------------------------------
# Test: intact surface passes
# ---------------------------------------------------------------------------

def test_intact_surface_passes(tmp_path):
    root = _build_kit(tmp_path / "kit")
    _write_snapshot(root)
    assert check_commitment_lock_impl(root) == []


# ---------------------------------------------------------------------------
# Test: missing snapshot
# ---------------------------------------------------------------------------

def test_missing_snapshot_returns_problem(tmp_path):
    root = _build_kit(tmp_path / "kit")
    # No .commitment-lock.json written
    result = check_commitment_lock_impl(root)
    assert result == ["lock snapshot missing"]


# ---------------------------------------------------------------------------
# F1: naive softening of each locked element fails
# ---------------------------------------------------------------------------

def test_naive_softening_each_locked_element_fails(tmp_path):
    # ---- (a) mutate GOALS.md Falsifier section ----
    root_a = _build_kit(tmp_path / "kit_a")
    _write_snapshot(root_a)
    (root_a / "goals" / "GOALS.md").write_text(
        _mk_goals("SOFTENED falsifier.", "Original commitments."), encoding="utf-8"
    )
    assert check_commitment_lock_impl(root_a) != [], "Falsifier mutation should fail"

    # ---- (b) mutate refusal-critical row's falsifier_layer ----
    rc_row = _mk_row("hz-rc-synth", refusal_critical=True, falsifier_layer="post_hoc")
    root_b = _build_kit(tmp_path / "kit_b", matrix_rows=[rc_row])
    _write_snapshot(root_b)
    # Change falsifier_layer in the matrix
    matrix_new = _MATRIX_HEADER + _mk_row("hz-rc-synth", refusal_critical=True,
                                          falsifier_layer="partial")
    (root_b / "goals" / "hazard-coverage.md").write_text(
        "# fixture\n\n" + matrix_new, encoding="utf-8"
    )
    result_b = check_commitment_lock_impl(root_b)
    assert result_b != [], "Refusal-critical row mutation should fail"

    # ---- (c) drop a registered check name from preflight.py ----
    root_c = _build_kit(tmp_path / "kit_c",
                        check_names=("check_alpha", "check_beta"))
    _write_snapshot(root_c)
    # Drop check_beta
    (root_c / "preflight.py").write_text(
        _mk_preflight("check_alpha"), encoding="utf-8"
    )
    assert check_commitment_lock_impl(root_c) != [], "Dropping a check should fail"

    # ---- (d) mutate .attest-keys.json content ----
    root_d = _build_kit(tmp_path / "kit_d")
    _write_snapshot(root_d)
    (root_d / "goals" / ".attest-keys.json").write_text(
        '{"version": 1, "keys": ["CHANGED"], "events": []}', encoding="utf-8"
    )
    assert check_commitment_lock_impl(root_d) != [], "attest-keys mutation should fail"


# ---------------------------------------------------------------------------
# F6: stubbed checker body caught via preflight_sha
# ---------------------------------------------------------------------------

def test_stubbed_checker_body_is_caught(tmp_path):
    original_pf = (
        "def check_example():\n"
        "    # original body\n"
        "    return []\n"
        "\n"
        "checks = [\n"
        "    check_example,\n"
        "]\n"
    )
    root = _build_kit(tmp_path / "kit", preflight_src=original_pf)
    _write_snapshot(root)

    # Mutate body of check_example while keeping its name in the checks list
    stubbed_pf = (
        "def check_example():\n"
        "    # STUBBED: always passes\n"
        "    pass\n"
        "\n"
        "checks = [\n"
        "    check_example,\n"
        "]\n"
    )
    (root / "preflight.py").write_text(stubbed_pf, encoding="utf-8")

    result = check_commitment_lock_impl(root)
    assert result != [], "Stubbed check body should be caught via preflight_sha"


# ---------------------------------------------------------------------------
# F2b: forged lock_override on refusal-critical still fails (GP-5)
# ---------------------------------------------------------------------------

def test_forged_lock_override_on_refusal_critical_still_fails(tmp_path):
    rc_row = _mk_row("hz-rc-synth", refusal_critical=True, falsifier_layer="post_hoc")
    root = _build_kit(tmp_path / "kit", matrix_rows=[rc_row])
    _write_snapshot(root)

    # Soften the refusal-critical row
    (root / "goals" / "hazard-coverage.md").write_text(
        "# fixture\n\n" + _MATRIX_HEADER +
        _mk_row("hz-rc-synth", refusal_critical=True, falsifier_layer="partial"),
        encoding="utf-8",
    )

    # Add accepted lock_override ADR that purports to authorize this row
    _mk_lock_override_adr(
        root / "decisions" / "9999-override.md",
        authorized_keys=["refusal_critical_rows.hz-rc-synth"],
    )

    # GP-5: refusal-critical divergence ALWAYS fails, no auto-trust
    result = check_commitment_lock_impl(root)
    assert result != [], "Forged lock_override on refusal-critical must not auto-trust"


# ---------------------------------------------------------------------------
# Non-critical override permitted
# ---------------------------------------------------------------------------

def test_noncritical_override_permitted(tmp_path):
    root = _build_kit(tmp_path / "kit")
    _write_snapshot(root)

    # Change a non-critical element: .attest-keys.json
    (root / "goals" / ".attest-keys.json").write_text(
        '{"version": 1, "keys": ["NEW"], "events": []}', encoding="utf-8"
    )

    # Add accepted lock_override ADR authorizing attest_keys_sha
    _mk_lock_override_adr(
        root / "decisions" / "9998-override.md",
        authorized_keys=["attest_keys_sha"],
    )

    result = check_commitment_lock_impl(root)
    assert result == [], "Non-critical divergence with matching override ADR should pass"


# ---------------------------------------------------------------------------
# F2: merge_base catches snapshot rewrite
# ---------------------------------------------------------------------------

def test_merge_base_catches_snapshot_rewrite(tmp_path):
    """Prove that re-snapshotting on head bypasses check_commitment_lock_impl,
    but merge_base_divergence catches it against the base commit."""
    repo = tmp_path / "repo"
    repo.mkdir()

    _build_kit(repo)

    # Initialise git repo
    def git(*args):
        r = subprocess.run(
            ["git", "-c", "user.email=t@t.com", "-c", "user.name=T", *args],
            cwd=repo, capture_output=True, text=True,
        )
        assert r.returncode == 0, f"git {args} failed: {r.stderr}"
        return r.stdout.strip()

    git("init")
    git("add", ".")
    git("commit", "-m", "initial-state")

    # Snapshot base and commit
    _write_snapshot(repo)
    git("add", ".")
    git("commit", "-m", "base-snapshot")
    base = git("rev-parse", "HEAD")

    # --- Agent softens the locked surface AND re-snapshots to cover tracks ---
    (repo / "goals" / "GOALS.md").write_text(
        _mk_goals("SOFTENED falsifier.", "Original commitments."), encoding="utf-8"
    )
    # Re-snapshot: covers the bypass path in check_commitment_lock_impl
    _write_snapshot(repo)
    git("add", ".")
    git("commit", "-m", "head-softened-and-resnapshot")

    # In-repo check is fooled: snapshot matches current surface
    assert check_commitment_lock_impl(repo) == [], (
        "check_commitment_lock_impl must pass when snapshot matches current (bypass path)"
    )

    # External merge-base check is NOT fooled
    problems = merge_base_divergence(repo, base)
    assert problems != [], (
        "merge_base_divergence must detect the softening vs the merge-base snapshot"
    )


# ---------------------------------------------------------------------------
# F3: in-repo anchor rewrite passes agent-local (theater proof)
# ---------------------------------------------------------------------------

def test_in_repo_anchor_rewrite_passes_agentlocal(tmp_path):
    """Prove that rewriting both the locked surface AND the snapshot makes
    check_commitment_lock_impl return [] — in-repo anchoring is theater."""
    root = _build_kit(tmp_path / "kit")
    # Original snapshot
    _write_snapshot(root)

    # Agent rewrites the locked surface...
    (root / "goals" / "GOALS.md").write_text(
        _mk_goals("SOFTENED falsifier.", "Original commitments."), encoding="utf-8"
    )
    (root / "goals" / ".attest-keys.json").write_text(
        '{"version": 1, "keys": ["FORGED"], "events": []}', encoding="utf-8"
    )
    # ... and re-snapshots to cover tracks (theater: agent controls the anchor)
    _write_snapshot(root)

    # In-repo check is completely fooled
    result = check_commitment_lock_impl(root)
    assert result == [], (
        "In-repo re-snapshot must fool check_commitment_lock_impl "
        "(proves in-repo anchoring is theater)"
    )


# ---------------------------------------------------------------------------
# diff_surface unit tests
# ---------------------------------------------------------------------------

def test_diff_surface_no_divergence():
    snap = {"goals_sections": {"Falsifier": "abc", "Commitments": "def"},
            "refusal_critical_rows": [], "registered_checks": ["check_a"],
            "preflight_sha": "sha1", "attest_keys_sha": "sha2",
            "runtime_roles_sha": "sha3", "harness_contract_sha": None}
    assert diff_surface(snap, snap.copy()) == []


def test_diff_surface_detects_goals_section_change():
    snap = {"goals_sections": {"Falsifier": "aaa", "Commitments": "bbb"},
            "refusal_critical_rows": [], "registered_checks": [],
            "preflight_sha": "x", "attest_keys_sha": None,
            "runtime_roles_sha": None, "harness_contract_sha": None}
    curr = {**snap, "goals_sections": {"Falsifier": "ZZZ", "Commitments": "bbb"}}
    diverged = diff_surface(snap, curr)
    assert "goals_sections.Falsifier" in diverged
    assert "goals_sections.Commitments" not in diverged


def test_diff_surface_detects_rc_row_change():
    row = {"hazard_id": "hz-x", "refusal_critical": True,
           "falsifier_layer": "post_hoc", "roadmap_defense_distance": "1",
           "exercise_scenario": "n/a"}
    snap = {"goals_sections": {}, "refusal_critical_rows": [row],
            "registered_checks": [], "preflight_sha": "x",
            "attest_keys_sha": None, "runtime_roles_sha": None,
            "harness_contract_sha": None}
    new_row = {**row, "falsifier_layer": "partial"}
    curr = {**snap, "refusal_critical_rows": [new_row]}
    diverged = diff_surface(snap, curr)
    assert "refusal_critical_rows.hz-x" in diverged


def test_diff_surface_detects_check_dropped():
    snap = {"goals_sections": {}, "refusal_critical_rows": [],
            "registered_checks": ["check_a", "check_b"],
            "preflight_sha": "x", "attest_keys_sha": None,
            "runtime_roles_sha": None, "harness_contract_sha": None}
    curr = {**snap, "registered_checks": ["check_a"]}
    assert "registered_checks" in diff_surface(snap, curr)


# ---------------------------------------------------------------------------
# F4: consistency falsifier -- author-fill cannot adjudicate co-located forgery
# ---------------------------------------------------------------------------

def test_F4_authorfill_cannot_distinguish_colocated_forgery(tmp_path):
    """F4 consistency falsifier: author-fill CANNOT adjudicate a co-located-secret
    forgery, but commitment_lock structural divergence IS caught by
    check_commitment_lock_impl.

    This grounds Q1 (trio verdict): check_commitment_lock and
    check_author_fill_contamination share disposition=conditional but need
    DIFFERENT exit conditions:
      - commitment_lock  => merge-base/CI barrier suffices (structural diff caught)
      - author_fill      => owner attestation required (strictly more -- HMAC
                           verification cannot distinguish a co-located-secret
                           forger from the real owner)

    HALF 1 -- author-fill CANNOT adjudicate a co-located-secret forgery:
      A co-located agent holds a copy of the registered HMAC secret and mints a
      token over the CURRENT value of the field.  attest.verify_token returns NO
      errors -- the forged token is structurally indistinguishable from a genuine
      owner attestation.  Therefore, the author-fill verifier cannot adjudicate
      it; owner attestation (an out-of-band trust root) is the required exit
      condition.

    HALF 2 -- commitment_lock structural divergence IS caught:
      A structural change to the locked surface (mutating the Falsifier section)
      is detected by check_commitment_lock_impl.  This proves commitment_lock's
      exit condition (the merge-base/CI barrier) is weaker than what author-fill
      requires -- the two mechanisms are genuinely different even though both
      carry disposition=conditional.

    This is a characterization test (asserts current mechanism behavior).
    It is expected to PASS immediately -- it documents an existing property,
    not a goal yet to reach.
    """
    # ---- HALF 1: co-located-secret forger is indistinguishable -------------------

    # The HMAC secret is "co-located": both the real owner and the forger hold it.
    COLOC_SECRET = "cafeface" * 8   # 64 hex chars = 32 bytes
    ACTOR = "coloc-agent"

    # Registry treats the actor as fully registered (exactly as a real owner).
    registry = {
        "keys": [{"key_id": ACTOR, "status": "registered"}]
    }

    # The current protected value (what the verifier compares against).
    current_value = "This is the protected Falsifier content."

    # The co-located forger mints a token using its copy of the same secret.
    # From the verifier's perspective this is byte-for-byte identical to the
    # real owner's attestation: same key_id, same value hash, same valid HMAC.
    forged_token = attest.make_token(
        COLOC_SECRET,
        "goals/GOALS.md", "Falsifier",
        current_value,
        ACTOR,
        "2026-06-29T00:00:00Z",
        "abc123deadbeef",
    )

    errors, _advisories = attest.verify_token(
        forged_token,
        "goals/GOALS.md", "Falsifier",
        current_value,
        registry,
        COLOC_SECRET,       # forger holds the same secret -- HMAC step passes
        lambda ts: True,    # provenance passes (monkeypatched; not the focus)
    )

    # HALF 1 ASSERTION: no errors returned -- forgery is indistinguishable.
    # Author-fill's verifier alone cannot adjudicate this; it needs owner
    # attestation (a trust root external to the HMAC mechanism).
    assert errors == [], (
        "HALF 1 FAILED: co-located-secret forged token should verify with no "
        f"errors (indistinguishable from genuine attestation); got {errors!r}"
    )

    # ---- HALF 2: commitment_lock structural divergence IS caught -----------------

    root = _build_kit(tmp_path / "kit")
    _write_snapshot(root)

    # Mutate the Falsifier section -- a structural divergence in the locked surface.
    (root / "goals" / "GOALS.md").write_text(
        _mk_goals("SOFTENED falsifier.", "Original commitments."), encoding="utf-8"
    )

    problems = check_commitment_lock_impl(root)

    # HALF 2 ASSERTION: divergence IS detected -- commitment_lock's structural
    # diff provides a weaker (sufficient-for-its-purpose) exit condition that
    # does NOT require owner attestation.
    assert problems != [], (
        "HALF 2 FAILED: check_commitment_lock_impl must detect the Falsifier "
        "mutation; got empty problems list"
    )
