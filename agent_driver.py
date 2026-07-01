"""agent_driver.py -- pluggable agent driver for the adversarial-exercise harness.

Phase 3.5a: deterministic ScriptedAgent (applies a caller-provided mutator to a
copy of the projected tree) + LiveAgent stub (Phase 4 wires the real AI agent).

Classes
-------
AgentDriver   : abstract base (abc.ABC).
ScriptedAgent : copies projected_tree under work_dir, applies self._mutator, returns
                (result_tree, transcript). Input projected_tree is never mutated.
LiveAgent     : stub; raises NotImplementedError("LiveAgent is Phase 4").

Result-dir naming
-----------------
The result dir is always work_dir / "result" (stable, deterministic -- no
timestamps). If it already exists it is cleared first (shutil.rmtree + copytree).
Timestamp-based or random names are explicitly forbidden in this kit.

ASCII-only strings throughout.
"""

import abc
import shutil
from pathlib import Path


class AgentDriver(abc.ABC):
    """Abstract base for agent drivers used in the adversarial-exercise harness."""

    @abc.abstractmethod
    def run(
        self,
        projected_tree: Path,
        task: dict,
        work_dir: Path,
    ) -> "tuple[Path, dict]":
        """Drive the agent against projected_tree and return (result_tree, transcript).

        Args:
            projected_tree: read-only snapshot the agent works from.
                            Implementations MUST NOT mutate this directory.
            task:           task descriptor (arbitrary dict; may be empty).
            work_dir:       caller-owned scratch directory; the result dir is
                            created as work_dir / 'result'.

        Returns:
            result_tree: Path to the (possibly mutated) copy of projected_tree.
            transcript:  dict with at least 'kind' (str) and 'tool_calls' (list).
        """


class ScriptedAgent(AgentDriver):
    """Deterministic scripted agent that applies a pre-planted mutator.

    The mutator stands in for the AI agent's tool calls, planting or not planting
    an escape into the result tree as the harness test requires.

    Args:
        mutator: callable ``(tree: Path) -> None`` applied to the result tree
                 copy after it is created.  Use ``lambda tree: None`` for the
                 clean (non-escaping) case.
    """

    def __init__(self, mutator):
        self._mutator = mutator

    def run(
        self,
        projected_tree: Path,
        task: dict,
        work_dir: Path,
    ) -> "tuple[Path, dict]":
        result_tree = work_dir / "result"
        if result_tree.exists():
            shutil.rmtree(result_tree)
        shutil.copytree(projected_tree, result_tree)
        self._mutator(result_tree)
        transcript: dict = {"kind": "scripted", "tool_calls": []}
        return result_tree, transcript


class LiveAgent(AgentDriver):
    """Stub for the live AI agent driver.

    Not yet implemented.  Phase 4 will replace this stub with a real
    implementation that drives a live AI subagent via the Claude API.
    """

    def run(
        self,
        projected_tree: Path,
        task: dict,
        work_dir: Path,
    ) -> "tuple[Path, dict]":
        raise NotImplementedError("LiveAgent is Phase 4")
