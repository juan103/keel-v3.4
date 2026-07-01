"""ax-runtime-role: tests for named_check.py (class invariant) and supporting files.

Phase 3.5a Task 4 -- TDD test suite.

Tests
-----
1. test_named_check_catches_escape     -- SCENARIO.mutator -> run() True
2. test_named_check_clean              -- clean fixture    -> run() False
3. test_named_check_catches_both_variants -- variant_a and variant_b -> both True
4. test_detector_zero_shared_imports   -- no non-stdlib name in both modules
5. test_predicate_anchor_exists        -- anchor in class_predicate.json names real function
6. test_retained_witnesses             -- verdicts.json expected == actual for all witnesses

ASCII-only. Stdlib only (test-side).
"""
from __future__ import annotations

import ast
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_AX_DIR = Path(__file__).resolve().parent / "ax-runtime-role"
_KIT_ROOT = Path(__file__).resolve().parents[3]

if str(_KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(_KIT_ROOT))


# ---------------------------------------------------------------------------
# Module loader helper (hyphens in path require importlib)
# ---------------------------------------------------------------------------

def _load_module(name: str, path: Path):
    """Load a Python module from a file path (handles hyphens in directory names)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Lazy module references (loaded on first access by each test)
# ---------------------------------------------------------------------------

def _named_check():
    return _load_module("named_check", _AX_DIR / "named_check.py")


def _escape_detector():
    return _load_module("escape_detector", _AX_DIR / "escape_detector.py")


def _variant_a():
    return _load_module("variant_a", _AX_DIR / "escape_variants" / "variant_a.py")


def _variant_b():
    return _load_module("variant_b", _AX_DIR / "escape_variants" / "variant_b.py")


def _load_scenario():
    """Load the reference AX_RUNTIME_ROLE scenario."""
    return _load_module(
        "ax_scenario_spec",
        _AX_DIR / "scenario_spec.py",
    ).AX_RUNTIME_ROLE


# ---------------------------------------------------------------------------
# Test 1: named_check catches the reference escape
# ---------------------------------------------------------------------------

def test_named_check_catches_escape(tmp_path):
    """SCENARIO.mutator applied to a clean fixture -> run() returns True."""
    scenario = _load_scenario()
    nc = _named_check()

    dest = tmp_path / "tree"
    dest.mkdir()
    scenario.build_fixture(dest)
    scenario.mutator(dest)

    result = nc.run(dest)
    assert result is True, f"named_check.run() expected True (escape caught), got {result!r}"


# ---------------------------------------------------------------------------
# Test 2: named_check passes on clean fixture
# ---------------------------------------------------------------------------

def test_named_check_clean(tmp_path):
    """Clean fixture with no mutator -> run() returns False."""
    scenario = _load_scenario()
    nc = _named_check()

    dest = tmp_path / "tree"
    dest.mkdir()
    scenario.build_fixture(dest)

    result = nc.run(dest)
    assert result is False, f"named_check.run() expected False (clean), got {result!r}"


# ---------------------------------------------------------------------------
# Test 3: named_check catches both escape variants
# ---------------------------------------------------------------------------

def test_named_check_catches_both_variants(tmp_path):
    """variant_a and variant_b mutators both produce True from run()."""
    scenario = _load_scenario()
    nc = _named_check()
    va = _variant_a()
    vb = _variant_b()

    # variant_a
    tree_a = tmp_path / "tree_a"
    tree_a.mkdir()
    scenario.build_fixture(tree_a)
    va.mutator(tree_a)
    result_a = nc.run(tree_a)
    assert result_a is True, f"variant_a: expected True, got {result_a!r}"

    # variant_b
    tree_b = tmp_path / "tree_b"
    tree_b.mkdir()
    scenario.build_fixture(tree_b)
    vb.mutator(tree_b)
    result_b = nc.run(tree_b)
    assert result_b is True, f"variant_b: expected True, got {result_b!r}"


# ---------------------------------------------------------------------------
# Test 4: escape_detector has zero shared non-stdlib imports with named_check
# ---------------------------------------------------------------------------

def _top_level_import_names(source_path: Path) -> set:
    """Return the set of top-level module names imported in a Python file."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                # 'import foo.bar' -> top-level name is 'foo'
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def test_detector_zero_shared_imports():
    """No non-stdlib name appears in both named_check.py and escape_detector.py."""
    stdlib_names = getattr(sys, "stdlib_module_names", None)
    assert stdlib_names is not None, (
        "sys.stdlib_module_names not available (requires Python 3.10+)"
    )

    nc_path = _AX_DIR / "named_check.py"
    ed_path = _AX_DIR / "escape_detector.py"

    nc_imports = _top_level_import_names(nc_path)
    ed_imports = _top_level_import_names(ed_path)

    nc_nonstdlib = nc_imports - set(stdlib_names)
    ed_nonstdlib = ed_imports - set(stdlib_names)

    shared_nonstdlib = nc_nonstdlib & ed_nonstdlib
    assert not shared_nonstdlib, (
        f"Shared non-stdlib imports between named_check and escape_detector: "
        f"{shared_nonstdlib!r}. "
        f"named_check non-stdlib: {nc_nonstdlib!r}, "
        f"escape_detector non-stdlib: {ed_nonstdlib!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: class_predicate.json anchor names a real top-level function
# ---------------------------------------------------------------------------

def test_predicate_anchor_exists():
    """class_predicate.json 'anchor' field names a real top-level function in named_check.py."""
    pred_path = _AX_DIR / "class_predicate.json"
    assert pred_path.exists(), f"class_predicate.json not found: {pred_path}"

    pred = json.loads(pred_path.read_text(encoding="utf-8"))
    assert "anchor" in pred, f"class_predicate.json missing 'anchor' field: {pred}"
    anchor = pred["anchor"]

    nc_path = _AX_DIR / "named_check.py"
    nc_tree = ast.parse(nc_path.read_text(encoding="utf-8"))

    top_level_func_names = {
        node.name
        for node in nc_tree.body
        if isinstance(node, ast.FunctionDef)
    }
    assert anchor in top_level_func_names, (
        f"anchor {anchor!r} is not a top-level function in named_check.py. "
        f"Top-level functions found: {sorted(top_level_func_names)!r}"
    )


# ---------------------------------------------------------------------------
# Test 6: retained witnesses match expected verdicts
# ---------------------------------------------------------------------------

def test_retained_witnesses():
    """verdicts.json expected verdict matches actual named_check.run() output for each witness."""
    witnesses_dir = _AX_DIR / "retained_witnesses"
    verdicts_path = witnesses_dir / "verdicts.json"
    assert verdicts_path.exists(), f"verdicts.json not found: {verdicts_path}"

    verdicts = json.loads(verdicts_path.read_text(encoding="utf-8"))
    nc = _named_check()

    failures = []
    for witness_name, entry in verdicts.items():
        expected = entry["expected_verdict"]
        witness_tree = witnesses_dir / witness_name
        assert witness_tree.exists(), (
            f"Witness tree not found: {witness_tree}. "
            f"Entry: {entry!r}"
        )
        actual = nc.run(witness_tree)
        if actual != expected:
            failures.append(
                f"{witness_name}: expected {expected!r}, got {actual!r} "
                f"(clause={entry.get('clause')!r}, note={entry.get('note')!r})"
            )

    assert not failures, "Witness verdict mismatches:\n  " + "\n  ".join(failures)
