"""BUG-001 reproduction: check_frame_validity_audit accepts a placeholder verdict.

The production frame-validity check (preflight.check_frame_validity_audit) tests author_verdict
for NON-EMPTINESS, not for being a valid adjudication. A non-adjudicated placeholder
(author_verdict="PENDING", dispositions=["PENDING"]) therefore evades it: the frame is
substantively unverified yet passes the gate. Surfaced by the Phase-4 live exercise
(ax-frame-validity); see docs/superpowers/keel-v3.4-phase4-F7-finding.md sec 3b.

This is the bug-shaped twin of CLAUDE.md sec 3 test-first: the reproduction exists before the fix.
The fix is a refusal-critical check change + a commitment_lock locked-surface edit + a
verdict-vocabulary FORK (positive-whitelist vs placeholder-blocklist), so it awaits owner
ratification. Until then this reproduction is marked xfail(strict): it documents the gap
executably and will turn xpass -- forcing this marker to be removed and the assertion kept -- the
moment the check is hardened.

ASCII-only. Stdlib + pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_KIT_ROOT = str(Path(__file__).resolve().parents[1])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import preflight  # noqa: E402

_BLOCK = '''# Placeholder-verdict binding ADR (BUG-001 reproduction)

**Status:** accepted

## Frame Validity

```keel-binding
type = "frame_validity"
id = "bug-001-frame"
inferential_claim = "the audit verifies the frame"
machinery_requirements = "n/a"
audit_artifact = "audit/frame_validity_audit.json"
author_verdict = "PENDING"
dispositions = ["PENDING"]
```
'''


def _build_placeholder_tree(root: Path) -> None:
    (root / "decisions").mkdir(parents=True, exist_ok=True)
    (root / "audit").mkdir(parents=True, exist_ok=True)
    (root / "decisions" / "0010-keel-binding.md").write_text(_BLOCK, encoding="utf-8")
    (root / "audit" / "frame_validity_audit.json").write_text('{"verdict": "PENDING"}', encoding="utf-8")


# check_frame_validity_audit follows the preflight pattern: it ASSERTS (raises AssertionError)
# when problems exist and returns cleanly when none. So "flagged" == "raises".


@pytest.mark.xfail(
    strict=True,
    reason="BUG-001: production check accepts a placeholder verdict; fix awaits owner-ratified "
    "verdict-vocabulary ADR + commitment_lock re-snapshot (see keel-v3.4-phase4-F7-finding.md 3b/7).",
)
def test_BUG_001_placeholder_verdict_is_flagged(tmp_path, monkeypatch):
    """A non-adjudicated placeholder verdict SHOULD be flagged as an unverified frame.

    Currently it is not (the check only tests non-emptiness), so the expected raise does not
    happen and this xfails until the hardening lands.
    """
    _build_placeholder_tree(tmp_path)
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_frame_validity_audit()


def test_BUG_001_empty_verdict_is_flagged_control(tmp_path, monkeypatch):
    """Control: the EXISTING check DOES catch a truly empty verdict / empty dispositions.

    Confirms the gap is specifically the placeholder case, not a wholesale failure -- so the
    xfail above is a precise completeness gap, not the check being broken.
    """
    block = _BLOCK.replace('author_verdict = "PENDING"', 'author_verdict = ""').replace(
        'dispositions = ["PENDING"]', "dispositions = []"
    )
    (tmp_path / "decisions").mkdir(parents=True, exist_ok=True)
    (tmp_path / "audit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "decisions" / "0010-keel-binding.md").write_text(block, encoding="utf-8")
    (tmp_path / "audit" / "frame_validity_audit.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_frame_validity_audit()
