import json, subprocess, sys
from pathlib import Path
import pytest
import preflight
ROOT = Path(__file__).resolve().parents[2]

def test_check_hooks_installed_passes_on_build_tree():
    preflight.check_hooks_installed()  # .claude/settings.json present + wired

def test_missing_settings_fails_under_strict(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    monkeypatch.setattr(preflight, "STRICT", True)
    with pytest.raises(AssertionError):
        preflight.check_hooks_installed()

def test_hook_firing_smoke_compliance(tmp_path):
    # execution_time evidence: the SessionStart command actually runs and emits the block.
    r = subprocess.run([sys.executable, "preflight.py", "--compliance"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0
    assert "COMPLIANCE" in r.stdout
