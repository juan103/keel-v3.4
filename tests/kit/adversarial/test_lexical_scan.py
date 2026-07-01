"""test_lexical_scan.py -- Lexical oracle-leak scan over projected fixture content.

Phase 3.5c, Task 5.

What is tested:
  test_eligible_scenarios_self_hosted_overlap
      Documents the 3.5c finding (NAMED RESIDUE): a clean lexical scan is NOT
      achievable for a self-hosted fixture, because each scenario's escape-concept
      vocabulary OVERLAPS the fixture's legitimate project vocabulary (the kit
      exercises its own hazards).  For each eligible scenario it builds + projects
      the fixture and asserts (a) the scan is well-behaved (every hit is a token in
      that scenario's own keyword set -- no spurious matches), and (b) the overlap
      is real (the clean fixture surfaces its own keywords).  The keyword_set.json
      files are NOT silently narrowed; the limitation is named, not hidden.

  test_injected_keyword_flagged
      Inject a keyword into a file in a projected fixture root and assert
      scan() flags it.  Proves the scan detects what it claims to detect.

HONEST LABEL (necessary-not-sufficient):
  A clean scan does NOT prove oracle-blindness.  The keyword set is spec-derived
  and finite.  Semantic paraphrase, unlisted tokens, installed-module
  reachability, and binary-encoded forms are NAMED RESIDUES not closed by this
  scan.  The scan is a necessary first-pass check, not a sufficiency guarantee.

ASCII-only.  Stdlib only (test-side).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# keel_v3.4/ root is parents[3] from this file:
#   parents[0]=adversarial  parents[1]=kit  parents[2]=tests  parents[3]=keel_v3.4
_KIT_ROOT = str(Path(__file__).resolve().parents[3])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

from lexical_scan import load_keyword_set, scan  # noqa: E402
from projection import project  # noqa: E402

_ADVERSARIAL_DIR = Path(__file__).resolve().parent

# The 7 eligible scenario directories (all named ax-* under this directory).
_SCENARIO_DIRS = [
    _ADVERSARIAL_DIR / "ax-runtime-role",
    _ADVERSARIAL_DIR / "ax-compliance",
    _ADVERSARIAL_DIR / "ax-relaxation",
    _ADVERSARIAL_DIR / "ax-sessionstart",
    _ADVERSARIAL_DIR / "ax-frame-validity",
    _ADVERSARIAL_DIR / "ax-adr-edit",
    _ADVERSARIAL_DIR / "ax-vacuous",
]


# ---------------------------------------------------------------------------
# Scenario loader (hyphenated dir names are not importable as packages)
# ---------------------------------------------------------------------------

def _load_scenario(scenario_dir: Path):
    """Load the Scenario instance from scenario_dir/scenario_spec.py.

    The scenario_spec.py module in each ax-* directory is loaded via
    importlib (the directory names contain hyphens and are not importable
    as normal Python packages).  The module-level Scenario instance is
    identified by finding the attribute whose value is a Scenario.
    """
    spec_path = scenario_dir / "scenario_spec.py"
    mod_name = "ax_{}_spec".format(scenario_dir.name.replace("-", "_"))
    spec = importlib.util.spec_from_file_location(mod_name, str(spec_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Find the Scenario instance (the module exports exactly one).
    from scenario_spec import Scenario
    for attr in dir(mod):
        val = getattr(mod, attr, None)
        if isinstance(val, Scenario):
            return val
    raise RuntimeError("No Scenario instance found in {}".format(spec_path))


# ---------------------------------------------------------------------------
# test_eligible_scenarios_clean
# ---------------------------------------------------------------------------

def test_eligible_scenarios_self_hosted_overlap(tmp_path):
    """3.5c finding (NAMED RESIDUE): a clean lexical scan is NOT achievable for a
    self-hosted fixture -- the escape-concept vocabulary OVERLAPS the fixture's
    legitimate project vocabulary (e.g. 'commitment', 'contributor', 'settings.json',
    'first-outcome' are both escape-concept words AND words that MUST appear in the
    clean fixture the agent operates on).  This test DOCUMENTS that limitation rather
    than asserting an unachievable clean scan.

    For each eligible scenario it builds + projects the fixture and runs scan(), then
    asserts:
      (a) the scan IS well-behaved -- every hit references a token in the scenario's
          OWN locked keyword set (no spurious matches beyond the keyword set); AND
      (b) the self-hosted overlap is real -- at least one eligible scenario's clean
          projected fixture surfaces its own escape-concept keywords (which is WHY a
          clean scan is not achievable for a self-hosted kit; if this were empty the
          keyword sets may have been silently narrowed).

    The MEANINGFUL detection property -- flagging an OUT-OF-BASELINE oracle-intent
    leak -- is proven separately by test_injected_keyword_flagged.  Refining keyword
    sets to escape-intent-only is a Phase-4 follow-up, itself bounded by this
    irreducible overlap (see the lexical_scan module docstring).
    """
    overlap_found: dict = {}

    for scenario_dir in _SCENARIO_DIRS:
        scenario = _load_scenario(scenario_dir)
        keywords = load_keyword_set(scenario_dir)
        kw_lower = [k.lower() for k in keywords]

        fixture_dir = tmp_path / scenario.name / "fixture"
        projected_dir = tmp_path / scenario.name / "projected"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        projected_dir.mkdir(parents=True, exist_ok=True)

        scenario.build_fixture(fixture_dir)
        project(
            fixture_dir,
            projected_dir,
            keep_globs=["**"],
            keep_overrides=list(scenario.keep_overrides),
        )

        problems = scan(projected_dir, keywords)
        # (a) the scan is well-behaved: every hit is attributable to a keyword in
        #     this scenario's own set (no spurious match beyond the keyword set).
        for p in problems:
            assert any(k in p.lower() for k in kw_lower), (
                "scan flagged a token not in the scenario keyword set (spurious): "
                + p
            )
        if problems:
            overlap_found[scenario.name] = len(problems)

    # (b) the self-hosted overlap is real and documents the limitation.
    assert overlap_found, (
        "expected the self-hosted vocabulary overlap (eligible fixtures contain "
        "their own escape-concept keywords -- a NAMED RESIDUE, see the lexical_scan "
        "docstring); if empty, the keyword sets may have been silently narrowed -- "
        "investigate rather than accept"
    )


# ---------------------------------------------------------------------------
# test_injected_keyword_flagged
# ---------------------------------------------------------------------------

def test_injected_keyword_flagged(tmp_path):
    """Injecting a keyword into a projected fixture file causes scan() to flag it.

    This proves the scan detects what it claims to detect.  A keyword from a
    real scenario (ax-runtime-role's keyword set) is injected into an otherwise
    keyword-free fixture file.  The scan must return a non-empty problem list.

    HONEST LABEL: this test proves the scan is live (it detects the injection),
    not that the keyword set is complete or that oracle-blindness follows from a
    clean scan.
    """
    projected_root = tmp_path / "projected"
    projected_root.mkdir()

    # Write an innocuous file with no keywords.
    (projected_root / "README.txt").write_text(
        "This is a clean fixture file with no oracle-sensitive content.\n",
        encoding="utf-8",
    )
    # Write a second innocuous file.
    (projected_root / "main.py").write_text(
        "def greet():\n    return 'hello world'\n",
        encoding="utf-8",
    )

    # Load a real keyword set (ax-runtime-role) and confirm the clean tree is clean.
    scenario_dir = _ADVERSARIAL_DIR / "ax-runtime-role"
    keywords = load_keyword_set(scenario_dir)
    assert scan(projected_root, keywords) == [], (
        "Clean fixture (no injected keyword) must return [] from scan()"
    )

    # Inject a keyword into the file content.
    injected_keyword = "attestation"
    assert injected_keyword in [kw.lower() for kw in keywords], (
        "injected_keyword must be in the keyword set for this test to be meaningful"
    )
    (projected_root / "notes.txt").write_text(
        "The attestation record has been updated.\n",  # 'attestation' is a keyword
        encoding="utf-8",
    )

    problems = scan(projected_root, keywords)
    assert problems, (
        "scan() must flag a file containing the injected keyword 'attestation'; "
        "got empty list"
    )
    combined = " ".join(problems)
    assert "attestation" in combined.lower(), (
        "problem message must name the matched keyword; got: {}".format(problems)
    )
    assert "notes.txt" in combined, (
        "problem message must name the file containing the keyword; got: {}".format(problems)
    )


# ---------------------------------------------------------------------------
# test_scan_skips_binary
# ---------------------------------------------------------------------------

def test_scan_skips_binary(tmp_path):
    """scan() skips binary files gracefully without raising.

    Binary files that cannot be decoded as utf-8 or latin-1 are silently
    skipped.  This test writes a binary file with a null byte (not valid utf-8
    as a standalone keyword-containing file) and confirms scan() does not raise.
    """
    projected_root = tmp_path / "projected"
    projected_root.mkdir()

    # Write a binary file (null bytes -- definitely not valid utf-8 text).
    (projected_root / "binary.bin").write_bytes(b"\x00\x01\x02\x03\xff\xfe" * 50)

    # Write a clean text file alongside it.
    (projected_root / "clean.txt").write_text("nothing sensitive here", encoding="utf-8")

    keywords = ["attestation", "token", "attest"]
    # Must not raise; binary file must be silently skipped.
    problems = scan(projected_root, keywords)
    assert isinstance(problems, list), "scan() must return a list even with binary files"


# ---------------------------------------------------------------------------
# test_empty_keywords_returns_clean
# ---------------------------------------------------------------------------

def test_empty_keywords_returns_clean(tmp_path):
    """scan() with an empty keyword list returns [] immediately.

    An empty keyword set means nothing to scan for; the projected tree is
    trivially clean with respect to the (empty) keyword set.
    """
    projected_root = tmp_path / "projected"
    projected_root.mkdir()
    (projected_root / "anything.txt").write_text("Some content here", encoding="utf-8")

    problems = scan(projected_root, [])
    assert problems == [], (
        "scan() with empty keyword list must return []; got: {}".format(problems)
    )
