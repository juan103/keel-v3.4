"""Tests for agent_driver.py -- pluggable AgentDriver (Phase 3.5a).

Four checks:
  test_scripted_agent_applies_mutator -- mutator writes a file; projected_tree untouched.
  test_scripted_agent_noop_clean      -- no-op mutator; result content-equals projected.
  test_live_agent_raises              -- LiveAgent.run raises NotImplementedError.
  test_transcript_shape               -- transcript has 'kind' str + 'tool_calls' list.
"""
import sys
from pathlib import Path

# keel_v3.4/ root is parents[3] from this file's location.
# 'py -m pytest' from that dir already puts it in sys.path, but add it
# explicitly so the file is importable in isolation too.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest
from agent_driver import AgentDriver, LiveAgent, ScriptedAgent


# ---------------------------------------------------------------------------
# test_scripted_agent_applies_mutator
# ---------------------------------------------------------------------------

def test_scripted_agent_applies_mutator(tmp_path):
    """Mutator that writes a file: result tree has it; projected_tree is untouched."""
    projected = tmp_path / "projected"
    projected.mkdir()
    (projected / "existing.txt").write_text("original", encoding="utf-8")

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    sentinel = "added_by_mutator.txt"

    def mutator(tree: Path) -> None:
        (tree / sentinel).write_text("mutated", encoding="utf-8")

    agent = ScriptedAgent(mutator=mutator)
    result_tree, transcript = agent.run(projected, {}, work_dir)

    # resulting tree has the new file
    assert (result_tree / sentinel).exists()
    # projected_tree is untouched (copy isolation)
    assert not (projected / sentinel).exists()
    # original file preserved in result copy
    assert (result_tree / "existing.txt").read_text(encoding="utf-8") == "original"


# ---------------------------------------------------------------------------
# test_scripted_agent_noop_clean
# ---------------------------------------------------------------------------

def test_scripted_agent_noop_clean(tmp_path):
    """No-op mutator: result tree is content-equal to projected."""
    projected = tmp_path / "projected"
    projected.mkdir()
    (projected / "a.txt").write_text("hello", encoding="utf-8")
    sub = projected / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("world", encoding="utf-8")

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    agent = ScriptedAgent(mutator=lambda tree: None)
    result_tree, _ = agent.run(projected, {}, work_dir)

    proj_files = sorted(
        (str(p.relative_to(projected)), p.read_text(encoding="utf-8"))
        for p in projected.rglob("*") if p.is_file()
    )
    result_files = sorted(
        (str(p.relative_to(result_tree)), p.read_text(encoding="utf-8"))
        for p in result_tree.rglob("*") if p.is_file()
    )
    assert proj_files == result_files


# ---------------------------------------------------------------------------
# test_live_agent_raises
# ---------------------------------------------------------------------------

def test_live_agent_raises(tmp_path):
    """LiveAgent.run raises NotImplementedError containing 'Phase 4'."""
    agent = LiveAgent()
    with pytest.raises(NotImplementedError, match="Phase 4"):
        agent.run(tmp_path / "proj", {}, tmp_path / "work")


# ---------------------------------------------------------------------------
# test_transcript_shape
# ---------------------------------------------------------------------------

def test_transcript_shape(tmp_path):
    """Transcript from ScriptedAgent is a dict with 'kind' str and 'tool_calls' list."""
    projected = tmp_path / "projected"
    projected.mkdir()

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    agent = ScriptedAgent(mutator=lambda tree: None)
    _, transcript = agent.run(projected, {}, work_dir)

    assert isinstance(transcript, dict), "transcript must be a dict"
    assert "kind" in transcript, "transcript must have 'kind'"
    assert "tool_calls" in transcript, "transcript must have 'tool_calls'"
    assert isinstance(transcript["tool_calls"], list), "'tool_calls' must be a list"
