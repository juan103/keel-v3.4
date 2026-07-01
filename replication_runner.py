"""replication_runner.py -- execution-trace machinery for F1 Control 3 (Phase 3.5a).

Anti-fabrication leg of the self-bottoming argument: every F1 cell verdict is
bound to an auditable execution trace, and an independent replicate() re-executes
each cell from its pinned inputs and asserts byte-identical reproduction.

A fabricated (true,false,false,false) tuple that never ran the pipeline cannot
reproduce the intermediate traces -- the tree_hash and check identity are
content-addressed on the REAL result tree and the REAL check source, so any
trace not produced by actual execution will differ from the re-run.

Public API
----------
run_cell(scenario, tree_kind, check_fn, work_dir) -> dict
    Run the real pipeline for one F1 cell and return an execution-trace record.

replicate(traces, scenario, check_fns, work_dir) -> list[str]
    Re-execute each cell from pinned inputs; return problems (empty == reproduced).

_pipeline(scenario, agent, check_fn, work_dir) -> (result_tree, transcript, manifest, caught)
    The SINGLE shared pipeline (Phase 3.5b, Finding A): build fixture -> project
    -> drive agent against the PROJECTED tree -> run the named check.  Both
    run_cell (this module) and adversarial_exercise.run_scenario call it, so the
    controls bind the SAME projected artifact the headline cell binds.  Before
    this unification, run_cell drove the agent against the RAW fixture (no
    projection), so its tree_hash could diverge from run_scenario's whenever the
    fixture carried exclude-set content.

_check_id(check_fn) -> str
    Stable, deterministic identity string for a check callable.
    Exported (underscore prefix = internal by convention) for use by Task 6 and tests.

_tree_hash(tree) -> str
    SHA-256 over sorted (rel_posix, file-sha256) pairs -- walk-order independent.
    Exported for diagnostics and Task 6 integration.

Determinism guarantees
----------------------
- tree_hash: sha256 over sorted (rel_posix, file-sha256) pairs.
  Sorting by relpath eliminates directory-walk order nondeterminism on all OS.
- check identity: stable name + sha256[:16] of check source file (if available).
  Content-addressed, so stable across process restarts while source is unchanged.
- Trace JSON is canonical (json.dumps, sort_keys=True) -- byte-identical across
  Python versions and platforms given identical content.
- No timestamps, random, uuid, or other nondeterministic values in any trace field.
- Result dirs use stable names (clear+recreate); no timestamp suffixes.

ASCII-only strings throughout.  Stdlib only.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
from pathlib import Path
from typing import Callable

import projection
from agent_driver import ScriptedAgent


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _file_sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of a file's binary content."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_hash(tree: Path) -> str:
    """SHA-256 over sorted (rel_posix, file-sha256) pairs -- walk-order independent.

    Algorithm:
      1. Walk the tree with os.walk; for each file compute (rel_posix, sha256).
      2. Sort entries by rel_posix (eliminates OS-dependent walk order).
      3. Encode as canonical JSON and sha256 the result.

    The output is a 64-character lowercase hex string.
    """
    tree = Path(tree)
    entries: list = []
    for dirpath_str, _dirnames, filenames in os.walk(tree):
        dirpath = Path(dirpath_str)
        for fn in filenames:
            abs_path = dirpath / fn
            rel = abs_path.relative_to(tree).as_posix()
            entries.append([rel, _file_sha256(abs_path)])
    entries.sort(key=lambda x: x[0])
    # Canonical JSON: a sorted list of [relpath, sha256] pairs.
    canonical = json.dumps(entries)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _check_id(check_fn: Callable) -> str:
    """Return a stable, deterministic identity string for a check callable.

    Format: "<name>:<src_hash_16>" where:
      name         -- check_fn._cell_id if set, else "<module>.<qualname>".
      src_hash_16  -- first 16 hex chars of sha256(source_file_bytes),
                      or 'nosrc' if the source file is not resolvable.

    Stability across process restarts: the id is content-addressed on the
    source file, so it is stable while the check source is unchanged.
    This allows check_fns dicts to be reconstructed in a fresh process and
    still match trace["check"] values from a prior run.
    """
    name = getattr(check_fn, "_cell_id", None)
    if name is None:
        mod = getattr(check_fn, "__module__", "") or ""
        qual = (
            getattr(check_fn, "__qualname__", "")
            or getattr(check_fn, "__name__", "unknown")
        )
        name = f"{mod}.{qual}" if mod else qual

    try:
        src_path = inspect.getfile(check_fn)
        with open(src_path, "rb") as fh:
            src_hash = hashlib.sha256(fh.read()).hexdigest()[:16]
    except (TypeError, OSError):
        src_hash = "nosrc"

    return f"{name}:{src_hash}"


def _mutator_for(scenario, tree_kind: str) -> Callable:
    """Return the mutator callable for the given tree_kind.

    tree_kind -> mutator
    --------------------
    "escape"  -> scenario.mutator       (scripted escape: plants the hazard)
    "clean"   -> scenario.clean_mutator (no-op: leaves tree content-identical)
    "noisy"   -> scenario.noisy_mutator (benign delta: changes tree, no escape)
    """
    if tree_kind == "escape":
        return scenario.mutator
    if tree_kind == "clean":
        return scenario.clean_mutator
    if tree_kind == "noisy":
        return scenario.noisy_mutator
    raise ValueError(
        f"Unknown tree_kind: {tree_kind!r}. Expected 'escape', 'clean', or 'noisy'."
    )


# ---------------------------------------------------------------------------
# Shared pipeline (Phase 3.5b -- Finding A: one project->drive->check path)
# ---------------------------------------------------------------------------

def _pipeline(
    scenario,
    agent,
    check_fn: Callable,
    work_dir: Path,
) -> "tuple[Path, dict, dict, bool]":
    """Build fixture -> project -> drive agent -> named check (the ONE pipeline).

    Both run_cell and adversarial_exercise.run_scenario route through here, so
    every cell (headline AND control) binds the SAME projected artifact.  The
    agent is driven against the PROJECTED tree, never the raw fixture.

    Steps
    -----
    1. Build the clean fixture under work_dir/fixture/ (stable dir; clear+recreate).
    2. Rule-derived projection -> work_dir/projected/ (manifest is the projection
       evidence; exclude-set content is removed here).
    3. Drive `agent` against the PROJECTED tree -> result_tree, transcript.
    4. Run check_fn against the resulting tree -> caught (bool).  The check runs
       regardless of any detector (anti-circularity is enforced by the caller).

    Args
    ----
    scenario : Scenario instance (carries build_fixture + task).
    agent    : an AgentDriver; its .run(projected_tree, task, work) returns
               (result_tree, transcript).  The mutator inside a ScriptedAgent
               selects escape/clean/noisy.
    check_fn : callable (tree: Path) -> bool.  Passed in; never hard-coded.
    work_dir : caller-owned scratch dir (created if absent).

    Returns
    -------
    (result_tree, transcript, manifest, caught)
      result_tree : Path to the (projected, then agent-mutated) result tree.
      transcript  : dict from the agent driver.
      manifest    : dict from projection.project (projected_hashes / keep_set /
                    exclude_set / ...).
      caught      : bool -- check_fn's verdict on result_tree.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Build the clean fixture (stable dir; clear+recreate). ---
    fixture_dir = work_dir / "fixture"
    if fixture_dir.exists():
        shutil.rmtree(fixture_dir)
    fixture_dir.mkdir()
    scenario.build_fixture(fixture_dir)

    # --- 2. Rule-derived projection (manifest is evidence; exclude-set removed). ---
    # Phase 3.5c: the projection strips transformed oracle forms (__pycache__,
    # *.pyc, .git) by path-rule; a git-fixture scenario declares keep_overrides
    # so its PROJECT-STATE .git (built WITHOUT oracle content) survives.  A kept
    # path is still content-checked, so the override does not open an oracle hole.
    projected = work_dir / "projected"
    if projected.exists():
        shutil.rmtree(projected)
    keep_overrides = list(getattr(scenario, "keep_overrides", ()) or ())
    manifest = projection.project(
        fixture_dir, projected, keep_globs=["**"], keep_overrides=keep_overrides
    )

    # --- 3. Drive the agent against the PROJECTED tree (never the raw fixture). ---
    agent_work = work_dir / "agent_work"
    agent_work.mkdir(parents=True, exist_ok=True)
    result_tree, transcript = agent.run(projected, scenario.task, agent_work)

    # --- 4. Named check against the resulting tree. ---
    caught = bool(check_fn(result_tree))

    return result_tree, transcript, manifest, caught


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_cell(
    scenario,
    tree_kind: str,
    check_fn: Callable,
    work_dir: Path,
) -> dict:
    """Run the real pipeline for one F1 cell and return an execution-trace record.

    Pipeline (Phase 3.5b: the SHARED _pipeline -- project -> drive -> check)
    -----------------------------------------------------------------------
    1. Build the clean fixture under work_dir/fixture/ (clear+recreate).
    2. Rule-derived projection -> work_dir/projected/ (exclude-set content removed).
    3. Apply the mutator for tree_kind via ScriptedAgent, driven against the
       PROJECTED tree (NOT the raw fixture -- this is the Finding A fix).
    4. Run check_fn against the resulting tree -> verdict (bool).
    5. Return a canonical trace dict; tree_hash is over the PROJECTED result tree.

    check_fn is a PARAMETER so Task 6 can pass the intact named_check OR a
    weakened variant -- the check is never hard-coded here.

    Result-dir naming
    -----------------
    All dirs under work_dir use stable names (clear+recreate); no timestamps.
      work_dir/fixture/    -- clean fixture built by scenario.build_fixture.
      work_dir/projected/  -- rule-derived projection of the fixture.
      work_dir/agent_work/ -- ScriptedAgent work dir; "result" sub-dir is the
                              resulting tree (ScriptedAgent.run semantics).

    Args
    ----
    scenario  : Scenario instance (from scenario_spec.Scenario).
    tree_kind : "escape", "clean", or "noisy".
    check_fn  : callable (tree: Path) -> bool.  Not hard-coded; passed by caller.
    work_dir  : caller-owned scratch directory (created if absent).

    Returns
    -------
    dict with keys: cell, tree_hash, check, verdict, contract_hash.
      cell          : tree_kind (str)
      tree_hash     : sha256 over sorted (rel_posix, file-sha256) of the PROJECTED
                      resulting tree
      check         : stable identity string for check_fn (_check_id)
      verdict       : bool -- True iff check_fn detected the escape class
      contract_hash : "n/a" (Phase 3.5a placeholder; wired in Phase 3.5b/Task 6)
    """
    # Select the mutator for tree_kind, wrap in a ScriptedAgent, and run the
    # ONE shared pipeline (project -> drive against projected -> check).
    mutator = _mutator_for(scenario, tree_kind)
    agent = ScriptedAgent(mutator)
    result_tree, _transcript, _manifest, verdict = _pipeline(
        scenario, agent, check_fn, work_dir
    )

    # Canonical trace dict (tree_hash is over the PROJECTED result tree).
    trace: dict = {
        "cell": tree_kind,
        "tree_hash": _tree_hash(result_tree),
        "check": _check_id(check_fn),
        "verdict": verdict,
        "contract_hash": "n/a",
    }
    return trace


def replicate(
    traces: list,
    scenario,
    check_fns: dict,
    work_dir: Path,
) -> list:
    """Re-execute each cell from pinned inputs; assert byte-identical reproduction.

    For each trace, resolves the check_fn from check_fns[trace["check"]], re-runs
    run_cell with the same (tree_kind, check_fn), then compares the produced trace
    against the recorded one using canonical JSON (json.dumps, sort_keys=True).

    The byte-identical assertion is the anti-fabrication control: a trace that was
    not produced by actual pipeline execution (e.g. hand-crafted verdicts) will
    not reproduce byte-identically because the tree_hash and check id are
    content-addressed on real execution artifacts.

    Args
    ----
    traces    : list of trace dicts previously produced by run_cell.
    scenario  : Scenario instance used to produce the traces.
    check_fns : dict mapping check identity str -> check_fn callable.
                Keys must match the "check" field values in traces.
    work_dir  : caller-owned scratch directory; one sub-dir per trace.

    Returns
    -------
    list of problem strings (empty list == all traces reproduced byte-identically).
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    problems: list = []
    for i, trace in enumerate(traces):
        check_id_val = trace.get("check", "")
        check_fn = check_fns.get(check_id_val)
        if check_fn is None:
            problems.append(
                f"trace[{i}] (cell={trace.get('cell')!r}): "
                f"no check_fn registered for check id {check_id_val!r}"
            )
            continue

        sub_work = work_dir / f"rep_{i}"
        produced = run_cell(scenario, trace["cell"], check_fn, sub_work)

        expected_json = json.dumps(trace, sort_keys=True)
        produced_json = json.dumps(produced, sort_keys=True)
        if expected_json != produced_json:
            problems.append(
                f"trace[{i}] (cell={trace.get('cell')!r}): "
                f"byte-identical reproduction failed.\n"
                f"  expected: {expected_json}\n"
                f"  produced: {produced_json}"
            )

    return problems
