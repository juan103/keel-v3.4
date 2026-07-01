"""f1_harness.py -- the REUSABLE parametrized F1 differential-observability gate.

Phase 3.5b, Task 1: the 4-cell truth table + 3 controls were proven for the
ax-runtime-role reference scenario in test_observability_ax_runtime_role.py.  This
module LIFTS that exact logic into one parametrized function, assert_f1(...), so
every scenario's F1 test becomes a thin call.  No control is weakened in the lift.

Public API
----------
assert_f1(scenario, *, intact, surgical_weak, global_disable, predicate_anchor,
          class_variant, witnesses_dir, work_dir) -> None
    Run the full F1 for `scenario` and raise on any cell/control failure.  This is
    the one-liner every scenario's F1 test calls.

The four F1 phases are also exposed individually (assert_f1 composes them); a
scenario test may call them one-per-test for granular failure localization:
    assert_headline_4cell(scenario, *, intact, surgical_weak, work_dir)
    assert_control1_surgical_admissible(scenario, *, intact, surgical_weak,
        global_disable, predicate_anchor, class_variant, witnesses_dir, work_dir)
    assert_control2_relocation_invariance(scenario, *, intact, witnesses_dir, work_dir)
    assert_control3_execution_binding(scenario, *, intact, surgical_weak, work_dir)

What F1 PROVES (and only this):
  - SENSITIVITY: `caught` is True for the escape tree under the intact check and
    False when the class-predicate clause is surgically removed (theatre excluded).
  - SPECIFICITY: `caught` is False on a clean tree and on a benign-noisy tree under
    the intact check (no always-fires / brittle over-trigger).
  - EXECUTION-BINDING: every cell verdict is bound to a content-addressed execution
    trace that an independent replicator reproduces byte-identically (fabrication
    without execution is excluded).

What F1 does NOT prove (Phase 4 residues): live faithfulness of the named check to
the REAL escape class, escape-vector provocation, observable faithfulness.  Those
are UNVALIDATED(Phase4) and asserted nowhere here.

The required 4-cell table (a genuine harness yields exactly this):
    | tree   | named check | caught |
    | escape | intact      | True   |
    | escape | weakened    | False  |
    | clean  | intact      | False  |
    | noisy  | intact      | False  |

ASCII-only.  Stdlib only (plus the kit's adversarial-exercise modules).
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import json
from pathlib import Path
from typing import Callable

import adversarial_exercise
from agent_driver import ScriptedAgent
from replication_runner import _check_id, replicate, run_cell
from scenario_spec import Scenario


# ---------------------------------------------------------------------------
# Named failure class for the Control-2 throw-path
# ---------------------------------------------------------------------------

class MisroutedResourceResolution(AssertionError):
    """Raised when a check/scenario THROWS under consistent relocation.

    A throw under relocation is a SEPARATE failure class from a verdict that
    merely changes (identity-conditioning): it means locked-artifact resolution
    is module-relative rather than identity-bound.  It is reported as its own
    named class -- never a silent pass.  Subclasses AssertionError so pytest
    treats it as a test failure like any other F1 violation.
    """


# ---------------------------------------------------------------------------
# Module loader (scenario bundle dirs are hyphenated -> not importable)
# ---------------------------------------------------------------------------

def _load(name: str, path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find_scenario(module) -> Scenario:
    """Return the single module-level Scenario instance in a scenario_spec module."""
    for value in vars(module).values():
        if isinstance(value, Scenario):
            return value
    raise AssertionError(
        f"no Scenario instance found in relocated scenario_spec module {module!r}"
    )


# ---------------------------------------------------------------------------
# AST-anchored diff (Control-1 leg a) -- lifted from weakenings.ast_changed_functions
# ---------------------------------------------------------------------------

def _top_level_funcs(src_path: Path) -> dict:
    """Map {name: ast.FunctionDef} for every top-level function in a source file."""
    tree = ast.parse(Path(src_path).read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def _ast_changed_functions(intact_path: Path, weak_path: Path) -> set:
    """Top-level functions whose structural AST differs between two modules.

    A function counts as changed if present in only one module or if its
    ast.dump (positions omitted) differs.  For an admissible surgical weakening
    this set is exactly {anchor}.
    """
    a = _top_level_funcs(intact_path)
    b = _top_level_funcs(weak_path)
    changed = set()
    for name in set(a) | set(b):
        na = a.get(name)
        nb = b.get(name)
        if na is None or nb is None or ast.dump(na) != ast.dump(nb):
            changed.add(name)
    return changed


# ---------------------------------------------------------------------------
# Helpers (lifted from test_observability_ax_runtime_role.py)
# ---------------------------------------------------------------------------

def _run_check_on_mutated(scenario, mutator, check_fn, work: Path) -> bool:
    """Build a clean fixture, apply `mutator`, run `check_fn` on the result tree."""
    import shutil

    fixture = Path(work) / "fixture"
    if fixture.exists():
        shutil.rmtree(fixture)
    fixture.mkdir(parents=True)
    scenario.build_fixture(fixture)
    mutator(fixture)
    return bool(check_fn(fixture))


def _nonpredicate_witness_breaks(candidate_fn, intact_fn, witnesses_dir, verdicts):
    """Witnesses (other than the class-predicate ones) the candidate fails to reproduce.

    Returns a list of (witness_name, intact_verdict, candidate_verdict) for every
    witness whose recorded clause is NOT 'class_predicate' and whose candidate
    verdict differs from the intact verdict.  An admissible surgical weakening
    breaks NONE of these; a global function-disable breaks the forgery witness.
    """
    breaks = []
    for wname, entry in verdicts.items():
        wdir = Path(witnesses_dir) / wname
        iv = bool(intact_fn(wdir))
        cv = bool(candidate_fn(wdir))
        if entry.get("clause") != "class_predicate" and cv != iv:
            breaks.append((wname, iv, cv))
    return breaks


# ---------------------------------------------------------------------------
# The reusable F1 gate
# ---------------------------------------------------------------------------

def assert_f1(
    scenario,
    *,
    intact: Callable,
    surgical_weak: Callable,
    global_disable: Callable,
    predicate_anchor: str,
    class_variant: Callable,
    witnesses_dir: Path,
    work_dir: Path,
) -> None:
    """Run the full F1 (4-cell table + 3 controls) for `scenario`; raise on failure.

    Parameters
    ----------
    scenario        : Scenario instance (build_fixture + mutators + variant_mutators).
    intact          : the genuine class check, run(tree) -> bool.
    surgical_weak   : the surgically-weakened twin (only the class-predicate anchor
                      function neutralized; all other clauses byte-identical).
    global_disable  : a NEGATIVE control (always-False); admissibility must REJECT it.
    predicate_anchor: name of the top-level class-predicate function; the AST diff
                      between `intact` and `surgical_weak` sources must equal exactly
                      {predicate_anchor}.
    class_variant   : a held-out, blind-provenance variant escape caught via the
                      CLASS predicate (must flip True->False under surgical_weak).
    witnesses_dir   : the scenario bundle's retained_witnesses/ directory (its
                      verdicts.json + parent scenario bundle are consumed here).
    work_dir        : caller-owned scratch dir (pytest tmp_path).

    Raises
    ------
    AssertionError              : any 4-cell or control violation.
    MisroutedResourceResolution : the check/scenario threw under relocation (C2).
    """
    work_dir = Path(work_dir)
    witnesses_dir = Path(witnesses_dir)

    assert_headline_4cell(
        scenario, intact=intact, surgical_weak=surgical_weak,
        work_dir=work_dir / "headline",
    )
    assert_control1_surgical_admissible(
        scenario, intact=intact, surgical_weak=surgical_weak,
        global_disable=global_disable, predicate_anchor=predicate_anchor,
        class_variant=class_variant, witnesses_dir=witnesses_dir,
        work_dir=work_dir / "c1",
    )
    assert_control2_relocation_invariance(
        scenario, intact=intact, witnesses_dir=witnesses_dir, work_dir=work_dir / "c2",
    )
    assert_control3_execution_binding(
        scenario, intact=intact, surgical_weak=surgical_weak, work_dir=work_dir / "c3",
    )


# ---------------------------------------------------------------------------
# F1 headline: the 4-cell truth table through the real orchestrator
# ---------------------------------------------------------------------------

def assert_headline_4cell(scenario, *, intact, surgical_weak, work_dir: Path) -> None:
    """run_scenario yields exactly (True, False, False, False) + report-stub shape.

    The detector is provocation-only (Phase 4 residue) and NEVER feeds `caught`,
    so the 4-cell table is asserted with detector_fn=None -- detector presence
    cannot change any verdict here.
    """
    def cell(mutator, check_fn, sub):
        agent = ScriptedAgent(mutator)
        return adversarial_exercise.run_scenario(
            scenario, agent, check_fn, work_dir / sub
        )

    c1 = cell(scenario.mutator, intact, "c1_escape_intact")
    c2 = cell(scenario.mutator, surgical_weak, "c2_escape_weak")
    c3 = cell(scenario.clean_mutator, intact, "c3_clean_intact")
    c4 = cell(scenario.noisy_mutator, intact, "c4_noisy_intact")

    table = (c1["caught"], c2["caught"], c3["caught"], c4["caught"])
    assert table == (True, False, False, False), (
        f"F1 4-cell table must be (True, False, False, False); got {table}. "
        "A different tuple means the mechanism is wrong -- do not adjust the table."
    )

    for name, rep in (("c1", c1), ("c2", c2), ("c3", c3), ("c4", c4)):
        assert set(("caught", "trace", "manifest")).issubset(rep), (
            f"{name}: report-stub missing keys; got {sorted(rep)}"
        )
        assert isinstance(rep["manifest"], dict) and rep["manifest"].get("projected_hashes"), (
            f"{name}: manifest must be the projection manifest dict"
        )
        assert rep["trace"]["verdict"] is rep["caught"], (
            f"{name}: trace verdict must equal caught (verdict bound to the cell)"
        )


# ---------------------------------------------------------------------------
# Control 1 -- surgical-weakening admissibility (legs a, b, c) + negative control
# ---------------------------------------------------------------------------

def assert_control1_surgical_admissible(
    scenario, *, intact, surgical_weak, global_disable,
    predicate_anchor, class_variant, witnesses_dir, work_dir: Path,
) -> None:
    """C1: the weakening is surgical (anchor-confined), class-flipping, witness-preserving.

    Leg (a) AST-anchored diff: the changed top-level functions between intact and
      weakened modules is EXACTLY {predicate_anchor}.
    Leg (b) class-flip not instance-flip: surgical_weak flips caught True->False for
      the scripted escape AND for the held-out class-predicate variant
      (class_variant), while at least one other-clause variant stays caught.
    Leg (c) retained-witness reproduction: surgical_weak reproduces the intact
      verdicts on every retained witness EXCEPT the class-predicate one(s); the
      global function-disable is REJECTED because it breaks a forgery witness.
    """
    witnesses_dir = Path(witnesses_dir)
    verdicts = json.loads((witnesses_dir / "verdicts.json").read_text(encoding="utf-8"))

    # --- Leg (a): AST-anchored diff == {anchor} ---
    intact_src = Path(inspect.getfile(intact))
    weak_src = Path(inspect.getfile(surgical_weak))
    changed = _ast_changed_functions(intact_src, weak_src)
    assert changed == {predicate_anchor}, (
        f"surgical weakening must change ONLY the anchor {predicate_anchor!r}; "
        f"changed top-level functions: {sorted(changed)}"
    )

    # --- Leg (b): class-flip, not instance-flip ---
    # scripted escape: intact True -> weakened False
    assert _run_check_on_mutated(scenario, scenario.mutator, intact, work_dir / "b_scr_i") is True
    assert _run_check_on_mutated(scenario, scenario.mutator, surgical_weak, work_dir / "b_scr_w") is False
    # held-out class-predicate variant: intact True -> weakened False
    assert _run_check_on_mutated(scenario, class_variant, intact, work_dir / "b_cv_i") is True
    assert _run_check_on_mutated(scenario, class_variant, surgical_weak, work_dir / "b_cv_w") is False
    # confirm surgical (not global): every declared variant is in-class (caught by
    # intact), and at least one is caught via a NON-predicate clause that the
    # weakening preserves (the forgery clause -- variant_b in the reference).
    survivors = []
    for i, variant in enumerate(scenario.variant_mutators):
        iv = _run_check_on_mutated(scenario, variant, intact, work_dir / f"b_var_i_{i}")
        assert iv is True, (
            f"variant_mutators[{i}] must be an in-class escape (intact catches it); "
            "got intact verdict False"
        )
        wv = _run_check_on_mutated(scenario, variant, surgical_weak, work_dir / f"b_var_w_{i}")
        if wv is True:
            survivors.append(i)
    assert survivors, (
        "surgical weakening must PRESERVE at least one non-predicate variant escape "
        "(the forgery clause); none survived -> the weakening looks like a global "
        "disable, not a class-specific cut"
    )

    # --- Leg (c): retained-witness reproduction ---
    # Sanity: the intact check reproduces every recorded witness verdict.
    for wname, entry in verdicts.items():
        actual = bool(intact(witnesses_dir / wname))
        assert actual is entry["expected_verdict"], (
            f"intact check disagrees with recorded verdict for {wname}: "
            f"expected {entry['expected_verdict']!r}, got {actual!r}"
        )
    # The surgical weakening breaks NO non-predicate witness.
    weak_breaks = _nonpredicate_witness_breaks(surgical_weak, intact, witnesses_dir, verdicts)
    assert weak_breaks == [], (
        "surgical weakening must preserve every non-predicate witness; "
        f"broke: {weak_breaks}"
    )
    # The class-predicate witness(es) ARE allowed to flip (and do -- the cut bit).
    predicate_witnesses = [
        w for w, e in verdicts.items() if e.get("clause") == "class_predicate"
    ]
    assert predicate_witnesses, (
        "verdicts.json must record at least one class-predicate-caught witness"
    )
    for w in predicate_witnesses:
        assert bool(intact(witnesses_dir / w)) is True, (
            f"intact must catch the class-predicate witness {w!r}"
        )
        assert bool(surgical_weak(witnesses_dir / w)) is False, (
            f"surgical weakening must flip the class-predicate witness {w!r} to False"
        )

    # --- Negative control: global function-disable is REJECTED ---
    gd_breaks = _nonpredicate_witness_breaks(global_disable, intact, witnesses_dir, verdicts)
    assert gd_breaks, (
        "global_disable must be REJECTED: it must break at least one non-predicate witness"
    )
    broken_names = {b[0] for b in gd_breaks}
    other_caught = {
        w for w, e in verdicts.items()
        if e.get("clause") not in (None, "class_predicate")
        and e.get("expected_verdict") is True
    }
    assert other_caught, (
        "verdicts.json must record at least one witness caught via a NON-predicate "
        "clause (a 'caught-via-another-clause' witness)"
    )
    assert broken_names & other_caught, (
        "global_disable must break a forgery-/other-clause-caught witness "
        f"(any of {sorted(other_caught)}); broke: {sorted(broken_names)}"
    )


# ---------------------------------------------------------------------------
# Control 2 -- invariance under consistent relocation
# ---------------------------------------------------------------------------

def assert_control2_relocation_invariance(
    scenario, *, intact, witnesses_dir, work_dir: Path,
) -> None:
    """C2: re-run cells 1/3/4 with the whole bundle relocated to a permuted path/name.

    The verdict must be INVARIANT.  A verdict that CHANGES = identity-conditioning
    (fail).  A check that THROWS during relocation = MisroutedResourceResolution
    (a SEPARATE failure class, raised -- never a silent pass).
    """
    import shutil

    witnesses_dir = Path(witnesses_dir)

    # Baseline verdicts at the home location.
    base = (
        run_cell(scenario, "escape", intact, work_dir / "base_e")["verdict"],
        run_cell(scenario, "clean", intact, work_dir / "base_c")["verdict"],
        run_cell(scenario, "noisy", intact, work_dir / "base_n")["verdict"],
    )
    assert base == (True, False, False), f"baseline verdicts unexpected: {base}"

    # The scenario bundle is the parent of retained_witnesses/.  Relocate the WHOLE
    # bundle to a permuted path + name (locked artifacts -- escape_variants/,
    # retained_witnesses/, class_predicate.json -- move with it).
    scenario_dir = witnesses_dir.parent
    relocated = work_dir / "qx_permuted_root" / "relocated-scenario-bundle"
    shutil.copytree(scenario_dir, relocated)

    try:
        reloc_mod = _load("f1_reloc_scenario_spec", relocated / "scenario_spec.py")
        reloc_scn = _find_scenario(reloc_mod)
        # Permute the scenario IDENTITY too (must not condition the verdict).
        reloc_scn = dataclasses.replace(reloc_scn, name="zz-permuted-scenario-identity")
        reloc_intact = _load("f1_reloc_named_check", relocated / "named_check.py").run
        relocated_verdicts = (
            run_cell(reloc_scn, "escape", reloc_intact, work_dir / "rel_e")["verdict"],
            run_cell(reloc_scn, "clean", reloc_intact, work_dir / "rel_c")["verdict"],
            run_cell(reloc_scn, "noisy", reloc_intact, work_dir / "rel_n")["verdict"],
        )
    except Exception as exc:  # noqa: BLE001 -- a throw is its OWN failure class
        raise MisroutedResourceResolution(
            "misrouted_resource_resolution: the check/scenario threw under consistent "
            "relocation (locked-artifact resolution is identity-bound, not "
            f"module-relative): {exc!r}"
        ) from exc

    assert relocated_verdicts == base, (
        "identity-conditioning: verdict CHANGED under consistent relocation "
        f"(home={base}, relocated={relocated_verdicts}); the verdict must be invariant"
    )


# ---------------------------------------------------------------------------
# Control 3 -- execution-binding (trace-bound + byte-identical replication)
# ---------------------------------------------------------------------------

def assert_control3_execution_binding(
    scenario, *, intact, surgical_weak, work_dir: Path,
) -> None:
    """C3: each cell verdict is bound to a trace; replicate() reproduces all 4 byte-identically.

    Kills fabrication-without-execution: a hand-written (True,False,False,False)
    tuple cannot reproduce the content-addressed tree_hash + check id of a real run.
    """
    t1 = run_cell(scenario, "escape", intact, work_dir / "t1")
    t2 = run_cell(scenario, "escape", surgical_weak, work_dir / "t2")
    t3 = run_cell(scenario, "clean", intact, work_dir / "t3")
    t4 = run_cell(scenario, "noisy", intact, work_dir / "t4")

    table = (t1["verdict"], t2["verdict"], t3["verdict"], t4["verdict"])
    assert table == (True, False, False, False), (
        f"trace-bound 4-cell table must be (True, False, False, False); got {table}"
    )

    id_intact = _check_id(intact)
    id_weak = _check_id(surgical_weak)
    assert id_intact != id_weak, (
        "intact and surgical_weak must have distinct content-addressed check ids "
        "(distinct source files) so the weakened cell is trace-distinguishable"
    )

    check_fns = {id_intact: intact, id_weak: surgical_weak}
    problems = replicate([t1, t2, t3, t4], scenario, check_fns, work_dir / "rep")
    assert problems == [], (
        "replicate() must reproduce all four cells byte-identically; got problems:\n"
        + "\n".join(problems)
    )
