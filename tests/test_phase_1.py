"""
Tests for Phase 1. Each test verifies one numbered requirement from
goals/phase_1/REQUIREMENTS.md.

This file ships empty by design — see R-1.5 in the v3-build project. At
Gate 0 (before any phase requirements have been written), an active test
file with NotImplementedError stubs would fail pytest and block the
pre-commit hook. The kit must let Gate 0 commits succeed.

When you start Phase 1, copy a pattern skeleton from tests/PATTERNS.md
into this file, decorate with @pytest.mark.requirement("R-1.X"), and
follow the test-first work cycle in CLAUDE.md §3.

Three test patterns are documented in tests/PATTERNS.md:

1. Example-based — for deterministic requirements with known expected output.
2. Property-based (Hypothesis) — for "for any valid input, this invariant holds".
3. Snapshot-based — for non-deterministic outputs you want regression-protected.

See decisions/0001-non-deterministic-testing.md for when to use which.
"""
