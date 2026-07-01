import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import runtime_roles as rr
import pytest

def _kit(tmp_path, md):
    (tmp_path / "goals").mkdir(parents=True)
    (tmp_path / "goals" / "GOALS.md").write_text(md, encoding="utf-8")
    return tmp_path

def test_section_extraction_basic(tmp_path):
    k = _kit(tmp_path, "# T\n\n## Falsifier\n\nThe claim dies if X.\n\n## Next\n\nignore\n")
    assert rr.extract_value(k, "goals/GOALS.md", "section:## Falsifier") == "The claim dies if X."

def test_section_crlf_and_trailing_ws_normalized(tmp_path):
    k = _kit(tmp_path, "## Falsifier  \r\nThe claim dies if X.   \r\n\r\n## Next\r\n")
    assert rr.extract_value(k, "goals/GOALS.md", "section:## Falsifier") == "The claim dies if X."

def test_section_fence_aware(tmp_path):
    k = _kit(tmp_path, "## Falsifier\n\n```\n## Not a heading\n```\nreal body\n\n## Next\n")
    val = rr.extract_value(k, "goals/GOALS.md", "section:## Falsifier")
    assert "## Not a heading" in val and "real body" in val

def test_duplicate_heading_is_ambiguous(tmp_path):
    k = _kit(tmp_path, "## Falsifier\na\n\n## Falsifier\nb\n")
    with pytest.raises(ValueError, match="ambiguous-locator"):
        rr.extract_value(k, "goals/GOALS.md", "section:## Falsifier")

def test_json_locator(tmp_path):
    (tmp_path / "goals").mkdir(parents=True)
    (tmp_path / "goals" / "x.json").write_text(json.dumps({"a": {"b": "v"}}), encoding="utf-8")
    assert rr.extract_value(tmp_path, "goals/x.json", "json:a.b") == "v"

def test_load_sidecar(tmp_path):
    (tmp_path / "goals").mkdir(parents=True)
    (tmp_path / "goals" / ".runtime-roles.json").write_text(json.dumps(
        {"version": 1, "fields": [{"artifact": "goals/GOALS.md", "field": "Falsifier",
         "locator": "section:## Falsifier", "role": "author"}]}), encoding="utf-8")
    fields = rr.load_sidecar(tmp_path)
    assert len(fields) == 1 and fields[0]["field"] == "Falsifier"

def test_load_sidecar_absent(tmp_path):
    assert rr.load_sidecar(tmp_path) == []
