# Preferred Paradigm

New in KEEL v3.2. This file declares the project's preferred programming
paradigm so that style-level forks (object-oriented vs functional vs
procedural vs mixed) are decided once, explicitly, at project start —
instead of drifting session by session with whatever the agent defaults to.

---

## Paradigm

Procedural Python with prose contracts. All kit checks and analysis functions are plain module-level functions — no classes unless a third-party API demands one. Functions return plain data (lists of strings for violations, dicts for structured results, dataclasses for typed rows). Prose contracts live in CLAUDE.md and ADRs; the executable contracts live in preflight.py and tests/kit/. No framework dependencies: stdlib only for all check and utility code; pytest and hypothesis are the only test-time dependencies.

## Conventions that follow

- Every check is a module-level function that accepts `repo_root: Path` and returns either `None` (raises `AssertionError` on failure, for preflight) or `list[str]` (returns violations, for composable callers).
- Helper functions are pure (no side effects, no file writes) and return plain Python types. The one explicit exception is the generation step in `commitment_lock.py` Step 7, which writes a file — but that call is isolated to the generation one-liner, not baked into any library function.
- Data rows use `@dataclass` for type clarity (e.g., `Row` in `hazard_coverage.py`); behavior-rich classes are not used.
- No global mutable state. Module-level constants (e.g., `_EXPECTED_COLS`, `_ROW`) are read-only.
- Tests are plain pytest functions with no fixtures beyond `tmp_path`; property-based tests use Hypothesis per ADR-0001.
- When a check must import another module, the import is local (inside the function body) to keep startup cost low and to make circular-import risks visible.

## Exceptions

- `preflight.py` is imperative at the boundary: it runs checks, prints results, and calls `sys.exit`. This is the intentional imperative shell. The check functions it calls remain pure.
- Test utilities (conftest.py) may use pytest fixtures and session-scoped setup where the framework requires it.
- The template files (GOALS.md, PARADIGM.md) and ADRs are prose artifacts, not code — the paradigm declaration applies to Python source files only.
