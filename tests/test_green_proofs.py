"""Real green-row proving tests (Phase 1c-B). Collected from the kit root; the
green-row engine runs them via subprocess. Not requirement-marked, so the
first-outcome recorder ignores them."""
import io
import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # kit root
import preflight  # noqa: E402
import pytest  # noqa: E402


def test_adr_index_neg(monkeypatch):
    # Force emit_adr_index to omit the first ADR -> check_adr_index sees a gap and raises.
    real_emit = preflight.emit_adr_index

    def broken_emit(repo_root=preflight.ROOT):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            real_emit(repo_root)
        for line in buf.getvalue().splitlines()[1:]:  # drop the first emitted ADR line
            print(line)

    monkeypatch.setattr(preflight, "emit_adr_index", broken_emit)
    with pytest.raises(AssertionError):
        preflight.check_adr_index()


def test_adr_index_pos():
    preflight.check_adr_index()  # intact index -> no raise


def test_bug_log_neg(tmp_path, monkeypatch):
    # A BUG entry with no Status line is outside the v3.2 protocol -> check raises.
    (tmp_path / "BUGS.md").write_text(
        "# BUGS\n\n### BUG-001 broken thing\n- no status line here\n", encoding="utf-8")
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_bug_log_exists()


def test_bug_log_pos(tmp_path, monkeypatch):
    (tmp_path / "BUGS.md").write_text(
        "# BUGS\n\n### BUG-001 fixed thing\n- **Status:** fixed\n", encoding="utf-8")
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    preflight.check_bug_log_exists()  # valid -> no raise


def test_kit_version_neg(tmp_path, monkeypatch):
    # No VERSION file in the tmp ROOT -> check raises.
    (tmp_path / "CLAUDE.md").write_text("**KEEL kit version: 3.4**\n", encoding="utf-8")
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_kit_version_declared()


def test_kit_version_pos(tmp_path, monkeypatch):
    (tmp_path / "VERSION").write_text("3.4\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("**KEEL kit version: 3.4**\n", encoding="utf-8")
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    preflight.check_kit_version_declared()  # no raise


_GOOD_CI = (
    "name: kit-ci\non:\n  push:\n  release:\n    types: [published]\n"
    "jobs:\n  t:\n    runs-on: windows-latest\n    strategy:\n      matrix:\n"
    '        python-version: ["3.11", "3.12", "3.13"]\n    steps:\n      - run: pytest\n')

def _ci_kit(tmp_path, text):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "kit-ci.yml").write_text(text, encoding="utf-8")
    return tmp_path

def test_ci_matrix_neg(tmp_path, monkeypatch):
    # isolate exactly one violation: continue-on-error only (starting from _GOOD_CI)
    bad = _GOOD_CI.replace("- run: pytest", "- run: pytest\n        continue-on-error: true")
    monkeypatch.setattr(preflight, "ROOT", _ci_kit(tmp_path, bad))
    with pytest.raises(AssertionError):
        preflight.check_ci_matrix_declared()

def test_ci_matrix_missing_version(tmp_path, monkeypatch):
    bad = _GOOD_CI.replace('"3.13"', "")
    monkeypatch.setattr(preflight, "ROOT", _ci_kit(tmp_path, bad))
    with pytest.raises(AssertionError):
        preflight.check_ci_matrix_declared()

def test_ci_matrix_missing_windows(tmp_path, monkeypatch):
    bad = _GOOD_CI.replace("windows-latest", "ubuntu-latest")
    monkeypatch.setattr(preflight, "ROOT", _ci_kit(tmp_path, bad))
    with pytest.raises(AssertionError):
        preflight.check_ci_matrix_declared()

def test_ci_matrix_no_trigger(tmp_path, monkeypatch):
    bad = _GOOD_CI.replace("on:\n  push:\n  release:\n    types: [published]\n", "")
    monkeypatch.setattr(preflight, "ROOT", _ci_kit(tmp_path, bad))
    with pytest.raises(AssertionError):
        preflight.check_ci_matrix_declared()

def test_ci_matrix_pos(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "ROOT", _ci_kit(tmp_path, _GOOD_CI))
    preflight.check_ci_matrix_declared()  # no raise


def test_pilot_phase_neg(tmp_path, monkeypatch):
    # A pilot_phase block with a malformed run record -> check_pilot_phase raises.
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    adr = decisions / "0099-test-pilot.md"
    adr.write_text(
        "# Test pilot ADR\n"
        "```keel-binding\n"
        'type = "pilot_phase"\n'
        'id = "test.malformed"\n'
        'gate_thresholds = { deadline = "2026-12-31", eligible_count = 1 }\n'
        'eligibility = "test eligibility"\n'
        'dispositions = ["pilot_pass"]\n'
        'status = "pilot_pending"\n'
        "```\n",
        encoding="utf-8",
    )
    # A malformed run record causes check_pilot_record to return problems.
    records_dir = tmp_path / "goals" / "pilot-records"
    records_dir.mkdir(parents=True)
    (records_dir / "test-malformed.json").write_text(
        "not valid json {{{", encoding="utf-8"
    )
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        preflight.check_pilot_phase()


def test_pilot_phase_pos():
    # The kit's own pilot binding is pilot_pending with no run record -> no raise.
    preflight.check_pilot_phase()
