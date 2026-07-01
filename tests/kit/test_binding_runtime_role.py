import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import binding

def test_runtime_role_valid_accepted():
    for role in ("author", "orchestrator", "subprocess"):
        block = {"type": "behavioral", "id": "x", "behavior": "b", "test": "t",
                 "runtime_role": role}
        assert binding.validate_block(block) == [], role

def test_runtime_role_invalid_rejected():
    block = {"type": "behavioral", "id": "x", "behavior": "b", "test": "t",
             "runtime_role": "human"}
    v = binding.validate_block(block)
    assert any("runtime_role" in s for s in v), v

def test_runtime_role_absent_ok():
    block = {"type": "behavioral", "id": "x", "behavior": "b", "test": "t"}
    assert binding.validate_block(block) == []
