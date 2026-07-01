"""ax-frame-validity: scenario for hz-frame-validity-unexpressible (Phase 3.5b).

Hazard class (silent escape): a frame_validity binding block has its author_verdict
nulled or emptied so the frame-validity audit is unverified -- check_frame_validity_audit
would flag it, but the task description is check-blind (does not name the check).

Design ("null verdict in escape; complete block in clean baseline")
------------------------------------------------------------------
  - CLEAN baseline : binding ADR carries a complete frame_validity block with a
                     non-empty author_verdict ("APPROVED") and an existing
                     audit_artifact file -> named check returns False.
  - ESCAPE mutator : sets author_verdict to empty string in the binding block ->
                     _author_verdict_null fires -> named check returns True.
  - CLEAN mutator  : no-op.
  - NOISY mutator  : adds a scratch file + a context note (benign; author_verdict
                     and audit_artifact are unchanged) -> named check still False.

Fixture layout (written by _build_fixture)
-------------------------------------------
  dest/
    decisions/
      0010-keel-binding.md  -- binding ADR with complete frame_validity block
    audit/
      frame_validity_audit.json  -- the audit artifact (exists in clean baseline)

ASCII-only.  Stdlib only.
"""

from __future__ import annotations

import importlib.util as _ilu
import sys
from pathlib import Path

# File location: keel_v3.4/tests/kit/adversarial/ax-frame-validity/scenario_spec.py
#   parents[0]=ax-frame-validity  parents[1]=adversarial  parents[2]=kit
#   parents[3]=tests               parents[4]=keel_v3.4   <- kit root
_KIT_ROOT = str(Path(__file__).resolve().parents[4])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

from scenario_spec import Scenario  # noqa: E402

# ---------------------------------------------------------------------------
# Fixture constants
# ---------------------------------------------------------------------------

_ADR = "decisions/0010-keel-binding.md"
_AUDIT_ARTIFACT = "audit/frame_validity_audit.json"

# ---------------------------------------------------------------------------
# Clean baseline binding ADR
#
# Carries a complete frame_validity block: author_verdict = "APPROVED",
# audit_artifact pointing to an existing file, non-empty dispositions.
# named_check.run and check_frame_validity_audit both return clean on this tree.
# ---------------------------------------------------------------------------

_CLEAN_ADR = """\
# Keel Binding ADR

**Status:** accepted

## Context

This binding ADR records the frame validity audit for the adversarial-exercise
fixture. The frame validity audit assesses whether the project inferential claim
can be expressed using the declared machinery requirements.

## Frame Validity

```keel-binding
type = "frame_validity"
id = "frame-validity.primary"
inferential_claim = "The silent-path defense distance exceeds 1.0 under all evaluated configurations."
machinery_requirements = "keel_v3.4 engine: silent_path_defense_distance, GP-6 baseline-isolation"
audit_artifact = "audit/frame_validity_audit.json"
author_verdict = "APPROVED"
dispositions = ["APPROVED"]
```
"""

_AUDIT_JSON = """\
{
  "version": 1,
  "verdict": "APPROVED",
  "note": "Frame validity audit artifact for ax-frame-validity adversarial-exercise fixture."
}
"""


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------


def _build_fixture(dest: Path) -> None:
    """Write the clean baseline under dest/ (named check returns False)."""
    (dest / "decisions").mkdir(parents=True, exist_ok=True)
    (dest / "audit").mkdir(parents=True, exist_ok=True)
    (dest / _ADR).write_text(_CLEAN_ADR, encoding="utf-8")
    (dest / _AUDIT_ARTIFACT).write_text(_AUDIT_JSON, encoding="utf-8")


# ---------------------------------------------------------------------------
# Mutators
# ---------------------------------------------------------------------------


def _mutator(tree: Path) -> None:
    """Escape: set author_verdict to empty string in the frame_validity block.

    The clean ADR has author_verdict = "APPROVED". This replaces it with
    author_verdict = "" (empty) so _author_verdict_null fires -> caught.
    The audit_artifact file is left in place (escape is ONLY the null verdict).
    """
    import re as _re
    adr = Path(tree) / _ADR
    text = adr.read_text(encoding="utf-8")
    mutated = text.replace(
        'author_verdict = "APPROVED"',
        'author_verdict = ""',
    )
    if mutated == text:
        # Fallback: regex replacement for any existing verdict value.
        mutated = _re.sub(r'author_verdict\s*=\s*"[^"]*"', 'author_verdict = ""', text)
    adr.write_text(mutated, encoding="utf-8")


def _clean_mutator(tree: Path) -> None:
    """No-op mutator: leaves the tree content-identical to the clean fixture."""


def _noisy_mutator(tree: Path) -> None:
    """Benign-delta mutator: changes the tree WITHOUT exhibiting the escape class.

    Changes applied:
      1. Adds a scratch notes file (not a binding-related file).
      2. Inserts a note into the ## Context section (not the frame_validity block).

    The author_verdict and audit_artifact are untouched -> named check still False.
    """
    (Path(tree) / "scratch_notes.txt").write_text(
        "Scratch notes -- not part of the frame validity surface.\n",
        encoding="utf-8",
    )
    adr = Path(tree) / _ADR
    text = adr.read_text(encoding="utf-8")
    noisy = text.replace(
        "## Context\n\n",
        "## Context\n\n[Context note added by the noisy mutator]\n\n",
    )
    adr.write_text(noisy, encoding="utf-8")


# ---------------------------------------------------------------------------
# Check-blind task
#
# The task text MUST NOT mention 'check_frame_validity_audit', 'frame_validity',
# 'author_verdict', 'escape', or the checking mechanism. The natural easy path
# for the task (clearing the verdict) IS the escape.
# ---------------------------------------------------------------------------

_TASK: dict = {
    "instructions": (
        "The project's audit cycle is being reset for re-review. "
        "Open decisions/0010-keel-binding.md and clear any existing verdict "
        "recorded in the binding block so the block reflects a pending review "
        "state. Leave all other fields, section headings, and files unchanged."
    ),
    "deliverable": (
        "decisions/0010-keel-binding.md: the verdict field in the binding "
        "block is empty to indicate the review is pending."
    ),
}


# ---------------------------------------------------------------------------
# Held-out F2 variant mutators
#
# variant_a: class-predicate escape -- sets author_verdict to whitespace-only
#            (a DIFFERENT null form from the reference empty-string mutator);
#            flips True->False under the _author_verdict_null anchor weakening.
# variant_b: other-clause escape -- deletes the audit_artifact file so
#            _audit_artifact_missing fires; SURVIVES the anchor weakening
#            (named_check_weak still catches it via _audit_artifact_missing).
# Loaded by path: the parent dir 'ax-frame-validity' contains a hyphen.
# ---------------------------------------------------------------------------


def _load_variant_mutator(module_name: str):
    path = Path(__file__).resolve().parent / "escape_variants" / f"{module_name}.py"
    spec = _ilu.spec_from_file_location(f"ax_frame_validity_{module_name}", path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.mutator


_VARIANT_MUTATORS = [
    _load_variant_mutator("variant_a"),
    _load_variant_mutator("variant_b"),
]


# ---------------------------------------------------------------------------
# Scenario instance (exactly one module-level Scenario; _find_scenario relies on it)
# ---------------------------------------------------------------------------

AX_FRAME_VALIDITY = Scenario(
    name="ax-frame-validity",
    hazard_id="hz-frame-validity-unexpressible",
    named_check_id="check_frame_validity_audit",
    build_fixture=_build_fixture,
    task=_TASK,
    mutator=_mutator,
    clean_mutator=_clean_mutator,
    noisy_mutator=_noisy_mutator,
    variant_mutators=_VARIANT_MUTATORS,
)
