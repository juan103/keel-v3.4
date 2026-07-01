"""
Coverage check: every requirement in goals/phase_*/REQUIREMENTS.md must
have at least one test marked with that requirement ID, and every
@pytest.mark.requirement("R-X.Y") in tests/ must point to a real requirement.

Default mode (no flag): orphan markers FAIL, untested requirements WARN only.
This matches the per-requirement test-first cycle in CLAUDE.md §3 -- at any
moment during phase work, requirements R-N.K+1 through R-N.last are drafted
but not yet test-covered.

Strict mode (--strict): untested requirements FAIL too. Run at phase
ratification, when every R-N.X is expected to have a test.

Strict-named-tests mode (--strict-named-tests, v3.1): scan REQUIREMENTS.md
prose for sub-clause-named test stubs of the form `test_R_N_X_<descriptor>`,
and FAIL if any named test is not defined in tests/test_phase_N.py. A single
requirement may name multiple sub-clause tests; --strict (marker presence)
alone counts each requirement as "covered" if any marker for it exists, so
sub-clause coverage drift slips past ratification. --strict-named-tests
closes that gap.

Strict-red-green mode (--strict-red-green, v3.3): a marker proves a test
EXISTS, not that test-first happened or that the test can fail -- a vacuous
`assert True` carrying the right marker passes --strict. The kit's
tests/conftest.py records the FIRST observed outcome of every
requirement-marked test (and every test_BUG_NNN_* reproduction) in
tests/.first-outcome-log.json. This flag FAILS any such test whose first
recorded outcome was a PASS (no red run ever observed -- CLAUDE.md §3 step 3
/ §11 step 2 was skipped) or which has no recorded run at all. Combine all
three at ratification:

    python check_coverage.py --strict --strict-named-tests --strict-red-green

Run with: python check_coverage.py                          # default (permissive)
          python check_coverage.py --strict                 # untested-req fail
          python check_coverage.py --strict-named-tests     # named-test fail
          python check_coverage.py --strict-red-green       # red-run evidence fail
          python check_coverage.py --strict --strict-named-tests --strict-red-green  # ratification
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent

REQ_PATTERN = re.compile(r"^### (R-\d+\.\d+)", re.MULTILINE)
MARK_PATTERN = re.compile(r'@pytest\.mark\.requirement\("(R-\d+\.\d+)"\)')

# v3.1: sub-clause-named test references in REQUIREMENTS.md prose.
# Convention: `test_R_<phase>_<index>_<descriptor>` where <descriptor> is one
# or more lowercase ASCII word chars / underscores. The pattern matches both
# bare references (`test_R_2_9_quorum_loss_terminates_inconclusive`) and
# fenced/inline-code references (`` `test_R_2_9_...` ``).
NAMED_TEST_PATTERN = re.compile(r"\btest_R_(\d+)_(\d+)_([a-z][a-z0-9_]*)\b")
# v3.1: definition pattern in test files. Same shape as above, must start a
# function definition (`def test_R_N_X_descriptor`).
NAMED_TEST_DEF_PATTERN = re.compile(
    r"^\s*def\s+(test_R_\d+_\d+_[a-z][a-z0-9_]*)\s*\(", re.MULTILINE
)

# v3.3: bug-reproduction test definitions (CLAUDE.md §11 step 2) — these are
# subject to the red-run evidence check too: no fix before a failing
# reproduction means the reproduction's first outcome must be a failure.
BUG_TEST_DEF_PATTERN = re.compile(
    r"^\s*def\s+(test_BUG_\d+_\w+)\s*\(", re.MULTILINE
)

# v3.3: where the conftest first-outcome recorder writes its evidence.
FIRST_OUTCOME_LOG = ROOT / "tests" / ".first-outcome-log.json"


def find_requirements():
    """Scan goals/phase_*/REQUIREMENTS.md for requirement IDs."""
    reqs = set()
    for req_file in ROOT.glob("goals/phase_*/REQUIREMENTS.md"):
        text = req_file.read_text(encoding="utf-8")
        for match in REQ_PATTERN.finditer(text):
            reqs.add(match.group(1))
    return reqs


def find_test_markers():
    """Scan tests/ for @pytest.mark.requirement markers."""
    marks = set()
    for test_file in ROOT.glob("tests/test_*.py"):
        text = test_file.read_text(encoding="utf-8")
        for match in MARK_PATTERN.finditer(text):
            marks.add(match.group(1))
    return marks


def find_named_test_references():
    """v3.1: scan REQUIREMENTS.md prose for `test_R_N_X_<descriptor>` names.

    Returns a set of full test-function names (e.g.
    {"test_R_2_9_convergence_terminates", "test_R_2_9_prompt_injection_aborts"}).
    """
    names: set[str] = set()
    for req_file in ROOT.glob("goals/phase_*/REQUIREMENTS.md"):
        text = req_file.read_text(encoding="utf-8")
        for match in NAMED_TEST_PATTERN.finditer(text):
            phase, idx, descriptor = match.group(1), match.group(2), match.group(3)
            names.add(f"test_R_{phase}_{idx}_{descriptor}")
    return names


def find_named_test_definitions():
    """v3.1: scan tests/ for `def test_R_N_X_<descriptor>(...)` definitions."""
    defs: set[str] = set()
    for test_file in ROOT.glob("tests/test_*.py"):
        text = test_file.read_text(encoding="utf-8")
        for match in NAMED_TEST_DEF_PATTERN.finditer(text):
            defs.add(match.group(1))
    return defs


def find_tracked_test_functions():
    """v3.3: every test function subject to the red-run evidence check:
    functions carrying a @pytest.mark.requirement decorator, plus
    test_BUG_NNN_* reproductions. Returns a set of (file_rel_posix, name).

    Static scan, deliberately simple: a requirement decorator is attributed
    to the next `def test_*` after it in the same file.
    """
    tracked: set[tuple[str, str]] = set()
    for test_file in ROOT.glob("tests/test_*.py"):
        text = test_file.read_text(encoding="utf-8")
        rel = test_file.relative_to(ROOT).as_posix()
        for match in MARK_PATTERN.finditer(text):
            after = text[match.end():]
            dm = re.search(r"^\s*def\s+(test_\w+)\s*\(", after, re.MULTILINE)
            if dm:
                tracked.add((rel, dm.group(1)))
        for match in BUG_TEST_DEF_PATTERN.finditer(text):
            tracked.add((rel, match.group(1)))
    return tracked


def load_first_outcomes():
    """v3.3: load tests/.first-outcome-log.json. Missing/corrupt -> {}."""
    try:
        data = json.loads(FIRST_OUTCOME_LOG.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def check_red_green(tracked, log):
    """v3.3: return failure messages for tracked tests with no red-run
    evidence. A test passes the check if ANY of its recorded nodeids
    (parametrized variants share the function) has first == "failed".
    """
    failures: list[str] = []
    for rel, name in sorted(tracked):
        prefix = f"{rel}::{name}"
        entries = [
            entry for nodeid, entry in log.items()
            if nodeid == prefix or nodeid.startswith(prefix + "[")
        ]
        if not entries:
            failures.append(
                f"{prefix}: no recorded run in {FIRST_OUTCOME_LOG.name} "
                f"(run pytest so the conftest recorder can log its first outcome)"
            )
        elif not any(e.get("first") == "failed" for e in entries):
            # ASCII-only advisory string (v3.1 convention): this prints to a
            # possibly cp1252-bound console.
            failures.append(
                f"{prefix}: first recorded outcome was a PASS -- no red run "
                f"ever observed. Test-first (CLAUDE.md section 3 step 3 / "
                f"section 11 step 2) was skipped, or the test cannot fail. "
                f"If the red run genuinely happened before the recorder "
                f"existed, say so at ratification; do not edit the log."
            )
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Promote untested requirements from warning to failure (ratification mode).",
    )
    parser.add_argument(
        "--strict-named-tests",
        action="store_true",
        help=(
            "v3.1: fail if REQUIREMENTS.md names a sub-clause test "
            "(test_R_N_X_<descriptor>) that is not defined in tests/."
        ),
    )
    parser.add_argument(
        "--strict-red-green",
        action="store_true",
        help=(
            "v3.3: fail if any requirement-marked test (or test_BUG_NNN_* "
            "reproduction) has no recorded failing first run in "
            "tests/.first-outcome-log.json."
        ),
    )
    args = parser.parse_args()

    requirements = find_requirements()
    test_markers = find_test_markers()

    untested = requirements - test_markers
    orphan_tests = test_markers - requirements

    print(f"Requirements found: {len(requirements)}")
    print(f"Test markers found: {len(test_markers)}")

    failed = False

    if untested:
        label = "[FAIL]" if args.strict else "[WARN]"
        print(f"\n{label} Requirements with no test:")
        for r in sorted(untested):
            print(f"  - {r}")
        if args.strict:
            failed = True

    if orphan_tests:
        # Orphan markers are typos and ALWAYS fail, in either mode.
        print(f"\n[FAIL] Test markers pointing to nonexistent requirements:")
        for r in sorted(orphan_tests):
            print(f"  - {r}")
        failed = True

    # v3.1: sub-clause-named-test cross-check.
    if args.strict_named_tests:
        named_refs = find_named_test_references()
        named_defs = find_named_test_definitions()
        print(f"Named-test refs in REQUIREMENTS.md: {len(named_refs)}")
        print(f"Named-test defs in tests/: {len(named_defs)}")
        missing_defs = named_refs - named_defs
        if missing_defs:
            print(f"\n[FAIL] Named tests referenced in REQUIREMENTS.md but not defined:")
            for n in sorted(missing_defs):
                print(f"  - {n}")
            failed = True

    # v3.3: red-run evidence cross-check.
    if args.strict_red_green:
        tracked = find_tracked_test_functions()
        log = load_first_outcomes()
        print(f"Tracked tests (requirement-marked + BUG reproductions): {len(tracked)}")
        print(f"First-outcome log entries: {len(log)}")
        red_green_failures = check_red_green(tracked, log)
        if red_green_failures:
            print(f"\n[FAIL] Tests without red-run evidence:")
            for f in red_green_failures:
                print(f"  - {f}")
            failed = True

    if failed:
        sys.exit(1)
    else:
        if untested:
            print("\n[OK] No orphan markers. (Untested requirements warned but not failed; use --strict for ratification.)")
        elif args.strict_named_tests or args.strict_red_green:
            print("\n[OK] All strict checks passed.")
        else:
            print("\n[OK] All requirements have tests, no orphan markers.")


if __name__ == "__main__":
    main()
