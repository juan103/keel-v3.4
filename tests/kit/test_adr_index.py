import subprocess, sys, re
from pathlib import Path
import preflight
ROOT = Path(__file__).resolve().parents[2]

def _adr_files():
    return sorted(p for p in (ROOT / "decisions").rglob("*.md")
                  if re.match(r"\d{4}-", p.name))

def test_index_lists_every_adr(capsys):
    preflight.emit_adr_index(ROOT)
    out = capsys.readouterr().out
    for p in _adr_files():
        num = p.name[:4]
        assert f"ADR-{num}" in out, f"index omitted {p.name}"

def test_check_adr_index_passes_on_real_tree():
    preflight.check_adr_index()  # must not raise

def test_adr_index_cli_runs():
    r = subprocess.run([sys.executable, "preflight.py", "--adr-index"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0
    assert "ADR-0000" in r.stdout or "ADR-0001" in r.stdout

def test_index_shows_status(capsys):
    preflight.emit_adr_index(ROOT)
    out = capsys.readouterr().out
    # ADR-0001 and ADR-0002 both use inline **Status:** accepted format;
    # confirm the index reflects real status, not the '?' fallback.
    assert "accepted" in out, (
        "ADR index shows no 'accepted' status — inline **Status:** regex may be broken"
    )
