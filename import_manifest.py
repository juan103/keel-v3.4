"""import_manifest.py -- transitive import-disjointness manifest (Phase 3.5c).

Walks the AST import graph of a module over the transitive closure, collecting
non-stdlib, non-local-kit module names (the external dependency surface).
Used to assert that each scenario's named_check and escape_detector share ZERO
non-stdlib imports over the full transitive closure.

NARROW import-hygiene: this check is NECESSARY but NOT SUFFICIENT for
correlation-freedom.  A shared stdlib interpretation (e.g. both modules parse
the same JSON file and agree on what 'detected' means) is a NAMED RESIDUE --
not caught here.  The disjointness guarantee covers only external non-stdlib
library code paths.

oracle_leakage_scope residue (named, not closed):
  Shared stdlib usage (json, re, pathlib, etc.) is not detectable by this
  manifest.  Two modules can still share interpretive assumptions through
  stdlib alone.  This is a known, intentional gap.

ASCII-only.  Stdlib only (ast, pathlib, sys).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _top_level(name: str) -> str:
    """Return the top-level package name ('foo.bar.baz' -> 'foo')."""
    return name.split(".")[0]


def _resolve_local(name: str, module_dir: Path, kit_root: Path) -> "Path | None":
    """Return the Path to the local .py entry for name, or None if not local.

    Searches (in order): kit_root/<top>.py, kit_root/<top>/__init__.py,
                         module_dir/<top>.py, module_dir/<top>/__init__.py.
    Uses only the top-level package name so 'foo.bar' resolves via 'foo'.
    """
    top = _top_level(name)
    for base in (kit_root, module_dir):
        candidate = base / f"{top}.py"
        if candidate.is_file():
            return candidate
        pkg_init = base / top / "__init__.py"
        if pkg_init.is_file():
            return pkg_init
    return None


def _parse_direct_imports(module_path: Path) -> "list[str]":
    """Return absolute module names directly imported in module_path (AST scan).

    Includes: 'import foo', 'import foo.bar', 'from foo import bar'.
    Excludes: relative imports (level > 0), malformed/unparseable source.
    Returns [] on any error.
    """
    try:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(module_path))
    except (OSError, SyntaxError):
        return []

    names: "list[str]" = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # level > 0 is a relative import -- no absolute module name to collect
            if node.level == 0 and node.module:
                names.append(node.module)
    return names


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transitive_nonstdlib_imports(
    module_path: Path,
    kit_root: Path,
    _visited: "set[Path] | None" = None,
) -> "set[str]":
    """Return the non-stdlib external dependency surface over the transitive closure.

    Recursively walks the import graph starting from module_path:
    - stdlib names (sys.stdlib_module_names): excluded from the result.
    - local kit modules (resolve to a .py under kit_root or the module's own
      directory): recursed into; their non-stdlib deps flow up to the caller.
    - all other names: added to the result set (the external surface).

    A visited-set (keyed by resolved Path) avoids infinite loops on circular
    imports.

    Returns a set of top-level non-stdlib module names reachable from
    module_path by any combination of local-kit hops.
    """
    if _visited is None:
        _visited = set()

    module_path = module_path.resolve()
    if module_path in _visited:
        return set()
    _visited.add(module_path)

    module_dir = module_path.parent
    result: "set[str]" = set()

    for name in _parse_direct_imports(module_path):
        top = _top_level(name)

        # 1. Stdlib -- not part of the external surface
        if top in sys.stdlib_module_names:
            continue

        # 2. Local kit module -- recurse; kit name itself is not in the surface
        local_path = _resolve_local(name, module_dir, kit_root)
        if local_path is not None:
            result |= transitive_nonstdlib_imports(local_path, kit_root, _visited)
            continue

        # 3. External non-stdlib -- add top-level name to the surface
        result.add(top)

    return result


def assert_disjoint(
    named_check_path: Path,
    detector_path: Path,
    kit_root: Path,
) -> "list[str]":
    """Return problem strings if the two transitive non-stdlib closures intersect.

    Returns [] iff the closures are disjoint -- no shared external non-stdlib
    library code path between named_check and escape_detector.

    A non-empty return is a genuine finding.  Do NOT loosen the check to
    silence it; investigate and fix the shared import instead.
    """
    nc_deps = transitive_nonstdlib_imports(named_check_path, kit_root)
    det_deps = transitive_nonstdlib_imports(detector_path, kit_root)
    shared = nc_deps & det_deps
    if not shared:
        return []
    nc_name = named_check_path.name
    det_name = detector_path.name
    return [
        f"shared non-stdlib import {name!r} in both {nc_name} and {det_name}"
        for name in sorted(shared)
    ]


def flag_dynamic(module_path: Path) -> "list[str]":
    """Return flagged dynamic-evading import/call uses in module_path (single file).

    Flags the following because they evade the static manifest:
    - 'import importlib' / 'from importlib import ...'
    - 'import subprocess' / 'from subprocess import ...'
    - '__import__(...)' calls

    subprocess is stdlib but can execute arbitrary external code, so it is
    flagged here even though it does not appear in the non-stdlib closure.

    NOT transitive -- scans only the given module_path, not its imports.
    """
    try:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(module_path))
    except (OSError, SyntaxError):
        return []

    problems: "list[str]" = []
    _FLAGGED = {"importlib", "subprocess"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = _top_level(alias.name)
                if top in _FLAGGED:
                    problems.append(
                        f"line {node.lineno}: dynamic-evading import {alias.name!r}"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = _top_level(node.module)
                if top in _FLAGGED:
                    problems.append(
                        f"line {node.lineno}: dynamic-evading import {node.module!r}"
                    )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                problems.append(
                    f"line {node.lineno}: dynamic-evading call __import__()"
                )

    return problems
