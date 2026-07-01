"""Tests for frame_validity binding shape and check_frame_validity_audit.

Phase 3 M2 -- Task 1.  TDD: write all tests first, watch them fail for the
right reason (missing check / unknown type), then implement.
"""
import sys
from pathlib import Path

# Ensure keel_v3.4/ is importable regardless of how pytest is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
import binding
import preflight
import attest

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Schema tests (binding.py)
# ---------------------------------------------------------------------------

def test_frame_validity_schema_accepts_complete_block():
    """validate_block returns [] for a fully-specified frame_validity block."""
    block = {
        "type": "frame_validity",
        "id": "fv.primary",
        "inferential_claim": "The model generalizes from training to test distribution.",
        "machinery_requirements": "Independent i.i.d. split; no leakage.",
        "audit_artifact": "goals/phase_3/frame-audit.md",
        "author_verdict": "VALID",
        "dispositions": ["requirement 1 met", "requirement 2 met"],
    }
    assert binding.validate_block(block) == []


def test_frame_validity_schema_rejects_missing_field():
    """Dropping author_verdict yields a missing-required-field error."""
    block = {
        "type": "frame_validity",
        "id": "fv.primary",
        "inferential_claim": "The model generalizes.",
        "machinery_requirements": "Independent i.i.d. split.",
        "audit_artifact": "goals/phase_3/frame-audit.md",
        # author_verdict intentionally omitted
        "dispositions": ["requirement 1 met"],
    }
    errors = binding.validate_block(block)
    assert any("author_verdict" in e for e in errors), (
        "expected an error mentioning 'author_verdict', got: " + repr(errors)
    )


# ---------------------------------------------------------------------------
# Helper: write a minimal ADR with a frame_validity keel-binding block
# ---------------------------------------------------------------------------

def _make_frame_adr(
    decisions_dir: Path,
    audit_artifact: str,
    author_verdict: str,
    dispositions: list,
) -> Path:
    """Write decisions_dir/0099-test-fv.md with a frame_validity block."""
    disp_toml = "[" + ", ".join(f'"{d}"' for d in dispositions) + "]"
    # Escape double-quotes inside verdict (should not appear in test data, but be safe)
    safe_verdict = author_verdict.replace('"', '\\"')
    block_toml = (
        'type = "frame_validity"\n'
        'id = "fv.primary"\n'
        'inferential_claim = "The model generalizes."\n'
        'machinery_requirements = "Independent i.i.d. split."\n'
        f'audit_artifact = "{audit_artifact}"\n'
        f'author_verdict = "{safe_verdict}"\n'
        f'dispositions = {disp_toml}\n'
    )
    content = (
        "# ADR-0099 Test Frame Validity\n\n"
        "```keel-binding\n"
        f"{block_toml}"
        "```\n"
    )
    adr_path = decisions_dir / "0099-test-fv.md"
    adr_path.write_text(content, encoding="utf-8")
    return adr_path


# ---------------------------------------------------------------------------
# Preflight check tests (check_frame_validity_audit)
# ---------------------------------------------------------------------------

def test_check_passes_when_no_frame_block(tmp_path, monkeypatch):
    """check_frame_validity_audit skips cleanly (no raise) when no frame_validity
    block exists -- mirrors check_falsifier_consistency skip behavior."""
    (tmp_path / "decisions").mkdir()
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    # Must not raise
    preflight.check_frame_validity_audit()


def test_check_fails_missing_artifact(tmp_path, monkeypatch):
    """check_frame_validity_audit raises AssertionError when audit_artifact is absent."""
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    _make_frame_adr(
        decisions,
        "goals/phase_3/frame-audit.md",  # file does NOT exist in tmp_path
        "VALID",
        ["item 1"],
    )
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_frame_validity_audit()


def test_check_fails_null_verdict(tmp_path, monkeypatch):
    """check_frame_validity_audit raises when author_verdict is the empty string."""
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    artifact = tmp_path / "goals" / "phase_3" / "frame-audit.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("audit content", encoding="utf-8")
    _make_frame_adr(decisions, "goals/phase_3/frame-audit.md", "", ["item 1"])
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_frame_validity_audit()


def test_check_fails_empty_dispositions(tmp_path, monkeypatch):
    """check_frame_validity_audit raises when dispositions list is empty."""
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    artifact = tmp_path / "goals" / "phase_3" / "frame-audit.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("audit content", encoding="utf-8")
    _make_frame_adr(decisions, "goals/phase_3/frame-audit.md", "VALID", [])
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_frame_validity_audit()


def test_check_passes_complete_frame(tmp_path, monkeypatch):
    """check_frame_validity_audit does not raise when artifact exists, verdict is
    non-empty, and dispositions is non-empty."""
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    artifact = tmp_path / "goals" / "phase_3" / "frame-audit.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("audit content", encoding="utf-8")
    _make_frame_adr(
        decisions,
        "goals/phase_3/frame-audit.md",
        "VALID",
        ["requirement 1 met", "requirement 2 met"],
    )
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    # Must not raise
    preflight.check_frame_validity_audit()


# ---------------------------------------------------------------------------
# F5b: content-binding proof (attest module)
# ---------------------------------------------------------------------------

def test_attested_verdict_semantic_mutation_invalidates():
    """F5b: make_token binds value_sha256; mutating the verdict string changes
    value_sha256 and causes verify_token to return value-changed-since-attestation.
    Proves the 2a attestation is content-bound, not presence-bound."""
    SEC = "00ff" * 8
    REG = {"keys": [{"key_id": "author", "status": "registered"}]}
    TS = "2026-06-28T00:00:00Z"

    v1 = "VALID -- all machinery requirements met"
    v2 = "VALID -- most machinery requirements met"  # semantically mutated

    sha1 = attest.value_sha256(v1)
    sha2 = attest.value_sha256(v2)
    assert sha1 != sha2, (
        "value_sha256 must differ for distinct strings; got the same hash"
    )

    tok = attest.make_token(
        SEC, "frame-audit.md", "author_verdict", v1, "author", TS, "abc123"
    )

    errs, _ = attest.verify_token(
        tok,
        expected_artifact="frame-audit.md",
        expected_field="author_verdict",
        current_value=v2,   # mutated value -- should fail value-binding
        registry=REG,
        secret_or_none=SEC,
        is_ancestor=lambda _ts: True,
    )
    assert errs == ["value-changed-since-attestation"], (
        f"expected value-binding error, got: {errs}"
    )
