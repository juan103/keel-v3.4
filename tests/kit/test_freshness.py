from pathlib import Path
import json, pytest
import freshness
ROOT = Path(__file__).resolve().parents[2]

def test_parse_config_reads_intervals():
    cfg = freshness.parse_freshness_config(ROOT)
    assert cfg["check_adr_immutability"] == 7
    assert cfg["check_paradigm_declared"] == 90

def test_out_of_bounds_interval_fails_closed(tmp_path):
    (tmp_path / "goals").mkdir()
    (tmp_path / "goals" / "freshness-config.md").write_text(
        "| check | interval_days | refusal_critical |\n|---|---|---|\n"
        "| c | 999 | false |\n", encoding="utf-8")
    with pytest.raises(ValueError):
        freshness.parse_freshness_config(tmp_path)

def test_rc_interval_over_7_fails_closed(tmp_path):
    (tmp_path / "goals").mkdir()
    (tmp_path / "goals" / "freshness-config.md").write_text(
        "| check | interval_days | refusal_critical |\n|---|---|---|\n"
        "| c | 30 | true |\n", encoding="utf-8")
    with pytest.raises(ValueError):
        freshness.parse_freshness_config(tmp_path)

def test_missing_record_is_violation(tmp_path):
    (tmp_path / "goals").mkdir()
    (tmp_path / "goals" / "freshness-config.md").write_text(
        "| check | interval_days | refusal_critical |\n|---|---|---|\n"
        "| c | 7 | true |\n", encoding="utf-8")
    v = freshness.check_falsifier_freshness_impl(tmp_path, strict=True, now=1000.0, head="aaa")
    assert any("c" in s and "no recorded pass" in s for s in v)

def test_stale_by_age_and_tree(tmp_path):
    (tmp_path / "goals").mkdir()
    (tmp_path / "goals" / "freshness-config.md").write_text(
        "| check | interval_days | refusal_critical |\n|---|---|---|\n"
        "| c | 7 | true |\n", encoding="utf-8")
    freshness.record_pass(tmp_path, "c", head="aaa", now=0.0)
    # same head, but 8 days later -> stale by age
    v = freshness.check_falsifier_freshness_impl(tmp_path, strict=True, now=8*86400.0, head="aaa")
    assert any("interval" in s for s in v)
    # within age but head changed -> stale by tree
    v2 = freshness.check_falsifier_freshness_impl(tmp_path, strict=True, now=1.0, head="bbb")
    assert any("tree changed" in s for s in v2)

def test_fresh_record_no_violation(tmp_path):
    (tmp_path / "goals").mkdir()
    (tmp_path / "goals" / "freshness-config.md").write_text(
        "| check | interval_days | refusal_critical |\n|---|---|---|\n"
        "| c | 7 | true |\n", encoding="utf-8")
    freshness.record_pass(tmp_path, "c", head="aaa", now=100.0)
    v = freshness.check_falsifier_freshness_impl(tmp_path, strict=True, now=200.0, head="aaa")
    assert v == []

def test_invalidate_removes_record(tmp_path):
    freshness.record_pass(tmp_path, "c", head="aaa", now=1.0)
    assert "c" in freshness.read_cache(tmp_path)
    freshness.invalidate(tmp_path, "c")
    assert "c" not in freshness.read_cache(tmp_path)
    # no-op on absent name must not raise
    freshness.invalidate(tmp_path, "c")
