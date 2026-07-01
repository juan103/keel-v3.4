"""Tests for f1_harness.py -- the reusable parametrized F1 harness (Phase 3.5b Task 1).

Two tests:
  test_reusable_harness_passes_ax_runtime_role
      -- assert_f1(...) with the ax-runtime-role pieces runs the full 4-cell
         truth table + all 3 controls and passes (the reference stays green
         through the harness extraction).
  test_pipeline_binds_projected_tree
      -- the Finding-A regression guard: BOTH run_scenario and run_cell now bind
         the PROJECTED resulting tree (excluded content removed), and they AGREE
         on the tree_hash.  A fixture that CONTAINS an exclude-set path
         (goals/hazard-coverage.md) proves projection actually removed content
         (projected hash != raw hash) and that the two pipelines bind the same
         projected artifact.

ASCII-only.  Stdlib only (test-side).
"""
from __future__ import annotations

import dataclasses
import importlib.util
import sys
from pathlib import Path

# keel_v3.4/ root is parents[3] from this file:
#   parents[0]=adversarial parents[1]=kit parents[2]=tests parents[3]=keel_v3.4
_KIT_ROOT = str(Path(__file__).resolve().parents[3])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import adversarial_exercise  # noqa: E402
import replication_runner  # noqa: E402
from agent_driver import ScriptedAgent  # noqa: E402
from f1_harness import assert_f1  # noqa: E402

_AX_DIR = Path(__file__).resolve().parent / "ax-runtime-role"
_WIT_DIR = _AX_DIR / "retained_witnesses"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scn_mod = _load("ax_f1h_scenario_spec", _AX_DIR / "scenario_spec.py")
SCENARIO = _scn_mod.AX_RUNTIME_ROLE

_weak = _load("ax_f1h_weakenings", _AX_DIR / "weakenings.py")
INTACT = _weak.intact
SURGICAL_WEAK = _weak.surgical_weak
GLOBAL_DISABLE = _weak.global_disable

_variant_a = _load("ax_f1h_variant_a", _AX_DIR / "escape_variants" / "variant_a.py").mutator


# ---------------------------------------------------------------------------
# Step 1: the reusable harness reproduces the reference F1 verdicts.
# ---------------------------------------------------------------------------

def test_reusable_harness_passes_ax_runtime_role(tmp_path):
    """assert_f1(...) over ax-runtime-role's pieces runs the full F1 and passes."""
    assert_f1(
        SCENARIO,
        intact=INTACT,
        surgical_weak=SURGICAL_WEAK,
        global_disable=GLOBAL_DISABLE,
        predicate_anchor="_author_field_unattested",
        class_variant=_variant_a,
        witnesses_dir=_WIT_DIR,
        work_dir=tmp_path,
    )


# ---------------------------------------------------------------------------
# Step 2: Finding-A regression guard -- both pipelines bind the projected tree.
# ---------------------------------------------------------------------------

def _noop(tree: Path) -> None:
    """No-op mutator (the result tree equals the projected fixture)."""


def test_pipeline_binds_projected_tree(tmp_path):
    """BOTH run_scenario and run_cell bind the PROJECTED tree (Finding A closed).

    Construct a fixture that CONTAINS an exclude-set path
    (goals/hazard-coverage.md matches projection.EXCLUDE_RULES).  Assert:
      (1) projection actually removes it: the projected tree_hash differs from
          the raw (un-projected) fixture tree_hash;
      (2) run_cell and run_scenario AGREE on the tree_hash (both bind the same
          projected artifact -- the pre-fix run_cell bound the raw tree and would
          have disagreed);
      (3) the excluded path is absent from the manifest's projected_hashes and
          present in its exclude_set.
    """
    def _build_with_excluded(dest: Path) -> None:
        SCENARIO.build_fixture(dest)
        (dest / "goals").mkdir(parents=True, exist_ok=True)
        (dest / "goals" / "hazard-coverage.md").write_text(
            "ORACLE SURFACE -- excluded content that must never reach the agent.\n",
            encoding="utf-8",
        )

    # A scenario whose fixture carries excluded content; all mutators are no-ops
    # so the resulting tree is exactly the projected fixture.
    scn = dataclasses.replace(
        SCENARIO,
        build_fixture=_build_with_excluded,
        mutator=_noop,
        clean_mutator=_noop,
        noisy_mutator=_noop,
    )

    # Raw (un-projected) hash of the fixture-with-excluded-content.
    raw_fixture = tmp_path / "raw_fixture"
    raw_fixture.mkdir(parents=True)
    _build_with_excluded(raw_fixture)
    raw_hash = replication_runner._tree_hash(raw_fixture)

    # run_cell now projects -> tree_hash over the PROJECTED tree.
    rc = replication_runner.run_cell(scn, "clean", INTACT, tmp_path / "rc")
    # run_scenario also projects -> trace.tree_hash over the PROJECTED tree.
    rs = adversarial_exercise.run_scenario(
        scn, ScriptedAgent(_noop), INTACT, tmp_path / "rs"
    )

    # (1) projection removed the excluded content (hash changed).
    assert rc["tree_hash"] != raw_hash, (
        "run_cell tree_hash must be over the PROJECTED tree (excluded content "
        "removed); it still equals the raw fixture hash -- projection was skipped"
    )

    # (2) both pipelines bind the SAME projected artifact.
    assert rc["tree_hash"] == rs["trace"]["tree_hash"], (
        "Finding A: run_cell and run_scenario must bind the same projected tree; "
        f"run_cell={rc['tree_hash']!r} run_scenario={rs['trace']['tree_hash']!r}"
    )

    # (3) the excluded path is gone from the projection.
    manifest = rs["manifest"]
    assert "goals/hazard-coverage.md" in manifest["exclude_set"], (
        "the excluded path must be recorded in the manifest's exclude_set"
    )
    assert "goals/hazard-coverage.md" not in manifest["projected_hashes"], (
        "the excluded path must NOT appear in the projected tree"
    )
