import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "protect_adrs.py"


def _run_hook(payload: dict) -> str:
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout


def test_hook_asks_on_accepted_adr(tmp_path):
    adr = tmp_path / "decisions" / "0002-x.md"
    adr.parent.mkdir(parents=True)
    adr.write_text("# ADR-0002\n\n**Status:** accepted\n", encoding="utf-8")
    out = _run_hook({"tool_input": {"file_path": str(adr)}, "cwd": str(tmp_path)})
    assert "permissionDecision" in out and "ask" in out


def test_hook_silent_on_new_adr(tmp_path):
    (tmp_path / "decisions").mkdir(parents=True)
    target = tmp_path / "decisions" / "0009-new.md"  # does not exist yet
    out = _run_hook({"tool_input": {"file_path": str(target)}, "cwd": str(tmp_path)})
    assert out.strip() == ""


# ---------------------------------------------------------------------------
# F-0: should_block predicate falsifier (recorded as value, not a green row)
# ---------------------------------------------------------------------------

import importlib.util

_spec = importlib.util.spec_from_file_location("protect_adrs", HOOK)
protect_adrs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protect_adrs)
should_block = protect_adrs.should_block


def _adr(tmp_path, name, status):
    p = tmp_path / "decisions" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# {name}\n\n**Status:** {status}\n", encoding="utf-8")
    return p


def test_f0_blocks_edit_to_accepted_adr(tmp_path):
    adr = _adr(tmp_path, "0002-x.md", "accepted")
    assert should_block({"file_path": str(adr)}, str(tmp_path)) is True


def test_f0_blocks_downgrade_target(tmp_path):
    # In 1c-B should_block keys on the file's ON-DISK status, so a downgrade edit to an
    # accepted ADR is blocked like any edit to it. The status-TRANSITION taxonomy
    # (distinguishing downgrade from a plain edit) is Phase 1c-C (ADR-0003 / trio F-0).
    # accepted ADR on disk; an agent editing it (even to downgrade) must be blocked.
    adr = _adr(tmp_path, "0002-x.md", "accepted")
    assert should_block({"file_path": str(adr)}, str(tmp_path)) is True


def test_f0_allows_draft_adr(tmp_path):
    adr = _adr(tmp_path, "0005-draft.md", "proposed")
    assert should_block({"file_path": str(adr)}, str(tmp_path)) is False


def test_f0_allows_non_adr_file(tmp_path):
    other = tmp_path / "README.md"
    other.write_text("hi", encoding="utf-8")
    assert should_block({"file_path": str(other)}, str(tmp_path)) is False


def test_f0_allows_template(tmp_path):
    tpl = _adr(tmp_path, "0000-template.md", "accepted")
    assert should_block({"file_path": str(tpl)}, str(tmp_path)) is False


def test_f0_allows_new_nonexistent_adr(tmp_path):
    (tmp_path / "decisions").mkdir(parents=True)
    target = tmp_path / "decisions" / "0009-new.md"
    assert should_block({"file_path": str(target)}, str(tmp_path)) is False


def test_f0_empty_tool_input(tmp_path):
    assert should_block({}, str(tmp_path)) is False


def test_f0_neuter_bite_is_real(tmp_path, monkeypatch):
    # Genuine neuter-bite: patch the REAL module symbol to the falsy_bool neutral
    # payload (return False) and show the accepted-ADR positive now reads False
    # (disabled); restore and it reads True. The positive depends on the predicate.
    adr = _adr(tmp_path, "0002-x.md", "accepted")
    monkeypatch.setattr(protect_adrs, "should_block", lambda ti, pd: False)
    assert protect_adrs.should_block({"file_path": str(adr)}, str(tmp_path)) is False
    monkeypatch.undo()
    assert protect_adrs.should_block({"file_path": str(adr)}, str(tmp_path)) is True
