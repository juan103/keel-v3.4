"""Tests for Scenario framework + ax-runtime-role reference instance (Phase 3.5a Task 3).

Four tests (TDD Step 1 -- written before implementation):
  test_fixture_builds         -- build_fixture writes expected structure; named check passes clean.
  test_mutator_creates_escape -- mutator -> real check_author_fill_contamination raises no-token.
  test_noisy_mutator_benign   -- noisy_mutator changes tree but does NOT create escape; check passes.
  test_task_is_check_blind    -- task dict text contains no forbidden terms.
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

# keel_v3.4/ root is parents[3] from this file's location.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest          # noqa: E402
import preflight       # noqa: E402
import attest          # noqa: E402
from scenario_spec import Scenario  # noqa: E402

# ---------------------------------------------------------------------------
# Load ax-runtime-role scenario instance via importlib (dir name has hyphens)
# ---------------------------------------------------------------------------

_AX_DIR = Path(__file__).resolve().parent / "ax-runtime-role"
_ax_spec = importlib.util.spec_from_file_location(
    "ax_runtime_role_scenario_spec",
    _AX_DIR / "scenario_spec.py",
)
_ax_mod = importlib.util.module_from_spec(_ax_spec)
_ax_spec.loader.exec_module(_ax_mod)

SCENARIO: Scenario = _ax_mod.AX_RUNTIME_ROLE

# ---------------------------------------------------------------------------
# Helper: run check_author_fill_contamination against an arbitrary fixture tree
# ---------------------------------------------------------------------------


def _run_check(tree: Path, monkeypatch) -> None:
    """Point preflight.ROOT at tree and run check_author_fill_contamination."""
    monkeypatch.setattr(preflight, "ROOT", tree)
    monkeypatch.setattr(attest, "_is_ancestor", lambda root, ts: True)
    preflight.check_author_fill_contamination()


# ---------------------------------------------------------------------------
# test_fixture_builds
# ---------------------------------------------------------------------------


def test_fixture_builds(tmp_path, monkeypatch):
    """build_fixture writes the expected structure; the named check passes clean
    (the author field is absent/empty in the baseline, so no escape is present)."""
    dest = tmp_path / "fixture"
    dest.mkdir()
    SCENARIO.build_fixture(dest)

    # Structural: sidecar and key registry must exist.
    assert (dest / "goals" / ".runtime-roles.json").exists(), \
        "build_fixture must write goals/.runtime-roles.json"
    assert (dest / "goals" / ".attest-keys.json").exists(), \
        "build_fixture must write goals/.attest-keys.json"

    # Sidecar must declare at least one role=author field.
    sidecar = json.loads(
        (dest / "goals" / ".runtime-roles.json").read_text(encoding="utf-8")
    )
    author_fields = [f for f in sidecar.get("fields", []) if f.get("role") == "author"]
    assert author_fields, "sidecar must declare at least one role=author field"

    # The artifact referenced by the sidecar must exist.
    for fspec in author_fields:
        art_path = dest / fspec["artifact"]
        assert art_path.exists(), (
            f"sidecar artifact {fspec['artifact']!r} must exist in the fixture tree"
        )

    # Named check must PASS on the clean baseline.
    _run_check(dest, monkeypatch)


# ---------------------------------------------------------------------------
# test_mutator_creates_escape
# ---------------------------------------------------------------------------


def test_mutator_creates_escape(tmp_path, monkeypatch):
    """mutator sets the author-fill field to a non-empty value with no attestation
    token; the real check_author_fill_contamination must detect the escape (no-token)."""
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    SCENARIO.build_fixture(fixture)

    # Copy to a work tree so the fixture is preserved.
    work = tmp_path / "work"
    shutil.copytree(fixture, work)

    # Apply the escape mutator.
    SCENARIO.mutator(work)

    # Real check must flag the escape.
    monkeypatch.setattr(preflight, "ROOT", work)
    monkeypatch.setattr(attest, "_is_ancestor", lambda root, ts: True)
    with pytest.raises(AssertionError) as exc_info:
        preflight.check_author_fill_contamination()
    assert "no-token" in str(exc_info.value), (
        f"expected 'no-token' in error after escape mutator; got: {exc_info.value!r}"
    )


# ---------------------------------------------------------------------------
# test_noisy_mutator_benign
# ---------------------------------------------------------------------------


def test_noisy_mutator_benign(tmp_path, monkeypatch):
    """noisy_mutator changes the tree (benign deltas) but does NOT create the
    escape; the real check must still pass after it runs."""
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    SCENARIO.build_fixture(fixture)

    work = tmp_path / "work"
    shutil.copytree(fixture, work)

    SCENARIO.noisy_mutator(work)

    # Noisy mutator must have changed SOMETHING (it is not a pure no-op).
    fixture_files = {
        str(p.relative_to(fixture)): p.read_text(encoding="utf-8")
        for p in fixture.rglob("*") if p.is_file()
    }
    work_files = {
        str(p.relative_to(work)): p.read_text(encoding="utf-8")
        for p in work.rglob("*") if p.is_file()
    }
    assert fixture_files != work_files, (
        "noisy_mutator must change the tree (it should differ from the clean fixture)"
    )

    # Named check must still PASS (no escape created).
    _run_check(work, monkeypatch)


# ---------------------------------------------------------------------------
# test_task_is_check_blind
# ---------------------------------------------------------------------------

# Terms forbidden from appearing in the task text (case-insensitive).
_FORBIDDEN = {
    "attest",
    "token",
    "runtime_role",
    "escape",
    "check_author_fill_contamination",
}


def test_task_is_check_blind():
    """task dict text must not contain any forbidden term (check-blind requirement).

    The task text is the serialized JSON of the task dict, lowercased.
    Forbidden terms: 'attest', 'token', 'runtime_role', 'escape',
    'check_author_fill_contamination'.
    """
    task_text = json.dumps(SCENARIO.task).lower()
    violations = [term for term in sorted(_FORBIDDEN) if term in task_text]
    assert not violations, (
        f"task text must not contain forbidden terms; found: {violations}\n"
        f"task = {SCENARIO.task!r}"
    )
