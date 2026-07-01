"""pytest configuration + first-outcome recorder (v3.3).

The recorder gives CLAUDE.md §3 step 3 ("write the test first, watch it
fail") mechanical evidence. Every requirement-marked test and every
test_BUG_NNN_* reproduction has its FIRST observed call-phase outcome
written once to tests/.first-outcome-log.json. At ratification,
`check_coverage.py --strict-red-green` fails any tracked test whose first
recorded outcome was a pass: either test-first was skipped, or the test
cannot fail — both are §3 violations the marker-presence checks can't see.

Properties:
- An outcome is recorded only ONCE per nodeid (the first run). Later runs
  never overwrite it — the log is evidence, not state.
- Skipped tests are not recorded (a skip is neither red nor green).
- Setup/collection errors are not recorded ("fails for the right reason"
  means a call-phase failure, not a broken import).
- COMMIT THIS FILE. The log is part of the project record, like snapshots.
  Editing it by hand defeats its purpose; if an entry is genuinely wrong
  (e.g., the red run predates the recorder), say so at ratification.
"""

import json
import subprocess
from pathlib import Path

_LOG_PATH = Path(__file__).parent / ".first-outcome-log.json"

_tracked_nodeids = set()
_log = None
_dirty = False


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requirement(req_id): link this test to a requirement ID (e.g., R-2.3)",
    )


def _load_log():
    global _log
    if _log is None:
        try:
            data = json.loads(_LOG_PATH.read_text(encoding="utf-8"))
            _log = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            _log = {}
    return _log


def _git_head():
    """Short HEAD hash for evidence context; None outside a git repo."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("requirement") or item.name.startswith("test_BUG_"):
            _tracked_nodeids.add(item.nodeid)


def pytest_runtest_logreport(report):
    global _dirty
    if report.when != "call":
        return
    if report.nodeid not in _tracked_nodeids:
        return
    if report.skipped:
        return
    log = _load_log()
    if report.nodeid in log:
        return
    log[report.nodeid] = {
        "first": "failed" if report.failed else "passed",
        "head": _git_head(),
    }
    _dirty = True


def pytest_sessionfinish(session, exitstatus):
    if _dirty and _log is not None:
        _LOG_PATH.write_text(
            json.dumps(dict(sorted(_log.items())), indent=2) + "\n",
            encoding="utf-8",
        )
