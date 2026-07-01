# Test patterns

Three patterns for the work cycle in CLAUDE.md §3. Pick one per requirement based on what kind of behavior the requirement asserts.

## Pattern 1: Example-based — deterministic requirements

Use when the requirement is: "given input X, produce output Y."

```python
import pytest

@pytest.mark.requirement("R-N.X")
def test_R_N_X_example():
    """R-N.X: [restate the requirement here]"""
    from mymodule import some_function
    assert some_function(input) == expected_output
```

## Pattern 2: Property-based — invariants

Use when the requirement is "for any valid input of this kind, this invariant must hold." Hypothesis generates hundreds of random inputs trying to break the invariant. Install with `pip install hypothesis`.

```python
import pytest
from hypothesis import given, strategies as st

@pytest.mark.requirement("R-N.X")
@given(graph=st.builds(...))
def test_R_N_X_property(graph):
    """R-N.X: For any graph G with N nodes, [some invariant must hold]."""
    result = some_function(graph)
    assert invariant_holds(result, graph)
```

## Pattern 3: Snapshot-based — non-deterministic outputs with regression protection

Use when the output is non-deterministic but should be reproducible with a fixed seed. First run saves the snapshot; subsequent runs compare against it. When intentionally changing the algorithm, delete the snapshot and write an ADR.

```python
import json
from pathlib import Path
import pytest

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"

@pytest.mark.requirement("R-N.X")
def test_R_N_X_snapshot():
    """R-N.X: [restate the non-deterministic requirement]"""
    import numpy as np
    np.random.seed(42)
    result = compute_metric_on_real_graph()

    snapshot_path = SNAPSHOT_DIR / "R_N_X_metric.json"
    tolerance = 1e-6

    if not snapshot_path.exists():
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        snapshot_path.write_text(json.dumps({"value": result}))
        pytest.skip("Snapshot created on first run. Re-run to verify.")

    snapshot = json.loads(snapshot_path.read_text())
    assert abs(result - snapshot["value"]) < tolerance, (
        f"Result drifted from snapshot. Got {result}, expected {snapshot['value']}. "
        f"If this change was intentional, delete the snapshot file and write an ADR."
    )
```

See `decisions/0001-non-deterministic-testing.md` for the project's policy on when to combine patterns 2 and 3.

(v3.3 note: the snapshot pattern's first run ends in `pytest.skip`, which the
first-outcome recorder deliberately does not record — the test's first
recorded outcome will come from the second run. Write the test before the
implementation as usual so that second run is red.)
