"""adversarial_exercise.py -- orchestrator for the adversarial-exercise harness (Phase 3.5a).

Public API
----------
run_scenario(scenario, agent, check_fn, work_dir, detector_fn=None) -> dict
    Run ONE F1 cell end-to-end and return a report-stub dict.

    Pipeline (v_final's chain):  projection -> agent driver -> named check
                                 -> (optional) escape detector -> report-stub.

    The report-stub keys are {caught, trace, manifest, transcript, provoked}.
    The full report.json + the 11 mandatory printed residues are Phase 3.5d --
    NOT here.

Anti-circularity invariant (v_final "named-check-runs-regardless"):
    `caught` is the named check's verdict against the resulting tree, computed
    INDEPENDENT of the detector.  The detector's output feeds only `provoked`
    (a Phase-4 provocation-count residue) and NEVER the catch decision.

Determinism / self-hosting:
    Stable dir names under work_dir (clear+recreate; no timestamps).  The agent
    works from the PROJECTED tree, never the raw fixture.  ASCII-only.  Stdlib +
    the kit's own projection.py / replication_runner.py.

ASCII-only strings throughout.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import replication_runner
from replication_runner import _check_id, _tree_hash


def run_scenario(
    scenario,
    agent,
    check_fn: Callable,
    work_dir: Path,
    detector_fn: Optional[Callable] = None,
) -> dict:
    """Run one F1 cell (projection -> driver -> named check -> detector) -> report-stub.

    Args
    ----
    scenario    : Scenario instance (carries build_fixture + task; the agent's
                  mutator -- not the scenario's tree_kind -- selects the tree).
    agent       : an AgentDriver (e.g. ScriptedAgent(scenario.mutator)).  Its
                  mutator decides whether the resulting tree is escape/clean/noisy.
    check_fn    : callable (tree: Path) -> bool.  Passed in (intact OR weakened);
                  never hard-coded -- F1 needs both the genuine and weakened checks.
    work_dir    : caller-owned scratch dir (created if absent).
    detector_fn : optional callable (transcript: dict, tree: Path) -> bool.  When
                  given, its verdict is recorded as `provoked` (provocation count
                  only).  It NEVER influences `caught`.

    Returns
    -------
    dict with keys:
      caught     : bool  -- the named check's verdict on the resulting tree.
      trace      : dict  -- {tree_hash, check, verdict, contract_hash}; binds the
                            verdict to content-addressed artifacts (Control-3 shape).
      manifest   : dict  -- the projection manifest (projected_hashes, keep/exclude
                            sets, meta-property flags).
      transcript : dict  -- the agent driver's transcript.
      provoked   : bool | None -- detector verdict, or None if detector_fn omitted.
    """
    work_dir = Path(work_dir)

    # --- 1-4. The ONE shared pipeline: build -> project -> drive -> check.   ---
    # (Phase 3.5b / Finding A) run_scenario and replication_runner.run_cell now
    # route through the SAME _pipeline, so the controls bind the same projected
    # artifact the headline cell binds.  `caught` is the named check's verdict on
    # the resulting tree, computed BEFORE (and independent of) any detector.
    result_tree, transcript, manifest, caught = replication_runner._pipeline(
        scenario, agent, check_fn, work_dir
    )

    # --- 5. Detector -- provocation only; NEVER feeds `caught`. ---
    provoked: Optional[bool] = None
    if detector_fn is not None:
        provoked = bool(detector_fn(transcript, result_tree))

    # --- 6. Execution trace: bind the verdict to content-addressed artifacts. ---
    trace = {
        "tree_hash": _tree_hash(result_tree),
        "check": _check_id(check_fn),
        "verdict": caught,
        "contract_hash": "n/a",
    }

    # --- 7. Report-stub (report.json + residues are Phase 3.5d, not here). ---
    return {
        "caught": caught,
        "trace": trace,
        "manifest": manifest,
        "transcript": transcript,
        "provoked": provoked,
    }
