"""ax-vacuous: Control-1 weakening helpers for the F1 differential-observability gate.

Provides the three check_fns the F1 truth table + admissibility controls need:
  intact         -- named_check.run (the genuine class check; wraps the REAL
                    log_integrity.detect_first_outcome_log_tampering).
  surgical_weak  -- named_check_weak.run: identical to intact EXCEPT the
                    class-predicate anchor _green_without_red is neutralized
                    (returns False); the _entry_dropped clause is UNTOUCHED.
  global_disable -- always-False (a NEGATIVE control: admissibility must REJECT it
                    because it breaks the dropped-entry-caught (non-predicate)
                    retained witness).

Also exposes the executable admissibility helper for Control-1 leg (a):
  ast_changed_functions(intact_path, weak_path) -> set[str]
    For an admissible surgical weakening this set must be exactly the anchor.

ASCII-only.  Stdlib only.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent

INTACT_SOURCE = _HERE / "named_check.py"
WEAK_SOURCE = _HERE / "named_check_weak.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_intact_mod = _load("ax_vacuous_named_check_intact", INTACT_SOURCE)
_weak_mod = _load("ax_vacuous_named_check_weak", WEAK_SOURCE)

# The intact class check and its surgically weakened twin.
intact = _intact_mod.run
surgical_weak = _weak_mod.run


def global_disable(tree) -> bool:
    """NEGATIVE control: a global function-disable that always returns False.

    Not a surgical weakening: it removes EVERY clause (the vacuous-green anchor AND
    _entry_dropped), so it breaks the dropped-entry-caught (non-predicate) retained
    witness.  Control-1 admissibility must REJECT it.
    """
    return False


def _top_level_funcs(src_path) -> dict:
    """Map {name: ast.FunctionDef} for every top-level function in a source file."""
    tree = ast.parse(Path(src_path).read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def ast_changed_functions(intact_path=INTACT_SOURCE, weak_path=WEAK_SOURCE) -> set:
    """Return the set of top-level functions that differ in AST between two modules.

    For an admissible surgical weakening this set must be exactly the anchor.
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
