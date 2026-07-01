import json, subprocess
from pathlib import Path
from log_integrity import detect_first_outcome_log_tampering

def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True, capture_output=True,
                   text=True, encoding="utf-8", errors="replace")

def _repo(tmp_path):
    _git(["init"], tmp_path); _git(["config", "user.email", "t@t"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    (tmp_path / "tests").mkdir()
    return tmp_path

def _write_log(repo, data):
    (repo / "tests" / ".first-outcome-log.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8")

def test_clean_log_no_violation(tmp_path):
    repo = _repo(tmp_path)
    _write_log(repo, {"t::a": {"first": "failed", "head": "abc"}})
    _git(["add", "-A"], repo); _git(["commit", "-m", "log"], repo)
    assert detect_first_outcome_log_tampering(repo) == []

def test_backdated_red_to_green_flip_flagged(tmp_path):
    repo = _repo(tmp_path)
    _write_log(repo, {"t::a": {"first": "failed", "head": "abc"}})
    _git(["add", "-A"], repo); _git(["commit", "-m", "log"], repo)
    _write_log(repo, {"t::a": {"first": "passed", "head": "abc"}})  # tamper
    _git(["add", "-A"], repo); _git(["commit", "-m", "sneaky"], repo)
    v = detect_first_outcome_log_tampering(repo)
    assert any("t::a" in s and "failed" in s for s in v)

def test_dropped_entry_flagged(tmp_path):
    repo = _repo(tmp_path)
    _write_log(repo, {"t::a": {"first": "failed", "head": "abc"},
                      "t::b": {"first": "failed", "head": "abc"}})
    _git(["add", "-A"], repo); _git(["commit", "-m", "log"], repo)
    _write_log(repo, {"t::a": {"first": "failed", "head": "abc"}})  # dropped b
    _git(["add", "-A"], repo); _git(["commit", "-m", "drop"], repo)
    v = detect_first_outcome_log_tampering(repo)
    assert any("t::b" in s for s in v)

def test_not_a_git_repo_silent(tmp_path):
    assert detect_first_outcome_log_tampering(tmp_path) == []
