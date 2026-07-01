import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import preflight
import pytest

def _kit(tmp_path, version_file=None, claudemd="**KEEL kit version: 3.4**\n"):
    if version_file is not None:
        (tmp_path / "VERSION").write_text(version_file, encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(claudemd, encoding="utf-8")
    return tmp_path

def test_missing_version_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "ROOT", _kit(tmp_path, version_file=None))
    with pytest.raises(AssertionError):
        preflight.check_kit_version_declared()

def test_placeholder_version_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "ROOT", _kit(tmp_path, version_file="[version]\n"))
    with pytest.raises(AssertionError):
        preflight.check_kit_version_declared()

def test_mismatched_version_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "ROOT", _kit(tmp_path, version_file="9.9\n"))
    with pytest.raises(AssertionError):
        preflight.check_kit_version_declared()

def test_tbd_version_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "ROOT", _kit(tmp_path, version_file="tbd\n"))
    with pytest.raises(AssertionError):
        preflight.check_kit_version_declared()

def test_valid_version_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "ROOT", _kit(tmp_path, version_file="3.4\n"))
    preflight.check_kit_version_declared()  # no raise
