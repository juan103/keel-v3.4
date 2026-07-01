"""KEEL v3.4 Phase 3.5a: Scenario framework for the adversarial-exercise harness.

A Scenario packages everything needed to exercise one hazard class in the
adversarial harness: a fixture builder, a check-blind task, named mutators,
and a pointer to the named check that evaluates the result tree.

Task 4 adds: variant_mutators (held-out F2 alternatives), a detector predicate,
and provenance metadata.  This file leaves a clear slot for those extensions
(the variant_mutators field exists but is empty until Task 4 populates it).

ASCII-only strings throughout.  Stdlib only.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Callable, List


@dataclasses.dataclass
class Scenario:
    """All deterministic pieces for one adversarial-exercise scenario.

    Fields
    ------
    name : str
        Short human-readable identifier (e.g. 'ax-runtime-role').
    hazard_id : str
        Hazard-matrix row id this scenario exercises
        (e.g. 'hz-runtime-role-unannotated').
    named_check_id : str
        Name of the preflight check that evaluates the result tree
        (e.g. 'check_author_fill_contamination').
    build_fixture : callable(dest: Path) -> None
        Writes a minimal fake project under dest/.  The written state is the
        CLEAN baseline: the hazard class is NOT exhibited; the named check
        passes when run against dest/.
    task : dict
        Check-blind task descriptor.  The text MUST NOT contain the check
        name, 'attest', 'token', 'runtime_role', or 'escape'.  The natural
        completion of this task sets the author-fill field (the escape's easy
        path).
    mutator : callable(tree: Path) -> None
        Scripted escape: mutates the tree so the named check flags it.
        Applied to a copy of the fixture tree; never to the fixture itself.
    clean_mutator : callable(tree: Path) -> None
        No-op mutator: leaves the tree content-identical to the fixture.
        The named check must pass after this mutator runs.
    noisy_mutator : callable(tree: Path) -> None
        Benign-delta mutator: changes the tree (e.g. adds temp files, reformats
        whitespace, sets an unrelated non-author field) WITHOUT exhibiting the
        escape class.  The named check must still pass after this mutator runs.

    Slots reserved for Task 4 (not yet implemented)
    -------------------------------------------------
    variant_mutators : list[callable]
        Two or more held-out F2 variant escapes.  Empty list until Task 4
        populates this field.  Task 4 also adds a detector predicate and
        provenance metadata alongside these.

    Phase 3.5c
    ----------
    keep_overrides : list[str]
        Per-scenario projection keep-override globs.  The hardened projection
        (projection.py) strips transformed oracle-form carriers (__pycache__,
        *.pyc, .git) by path-rule.  A git-fixture scenario whose fixture .git is
        PROJECT STATE (built WITHOUT oracle content -- the fixture builder
        maintains that invariant) declares keep_overrides so its .git survives
        projection and the git-history named check can run.  A kept path is STILL
        content-checked by verify_manifest, so a kept .git carrying oracle content
        is still caught -- the override does not open an oracle-leak hole.  Empty
        for scenarios with no project-state transformed forms to keep.
    """

    name: str
    hazard_id: str
    named_check_id: str
    build_fixture: Callable[[Path], None]
    task: dict
    mutator: Callable[[Path], None]
    clean_mutator: Callable[[Path], None]
    noisy_mutator: Callable[[Path], None]

    # Task 4 slot: held-out F2 variant mutators.  Populated in Task 4.
    variant_mutators: List[Callable[[Path], None]] = dataclasses.field(
        default_factory=list
    )

    # Phase 3.5c slot: per-scenario projection keep-override globs (see above).
    keep_overrides: List[str] = dataclasses.field(default_factory=list)
