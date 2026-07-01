"""Tests for projection.py -- rule-derived exclude-set + path/content manifest.

Five tests (Phase 3.5a core):
  test_excluded_path_absent    -- an excluded file is not copied to dest.
  test_content_hash_absent     -- verbatim copy of excluded file under kept path
                                  is caught by verify_manifest.
  test_symlink_resolved        -- a symlink into the exclude-set is caught
                                  via content-hash comparison.
  test_meta_properties         -- keep_set x exclude_set == {} and
                                  check_sources <= exclude_set hold.
  test_clean_projection_ok     -- a fixture with only kept files yields no problems.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest
from projection import EXCLUDE_RULES, project, verify_manifest


# ---------------------------------------------------------------------------
# test_excluded_path_absent
# ---------------------------------------------------------------------------

def test_excluded_path_absent(tmp_path):
    """An excluded file must not appear in the projected workspace."""
    src = tmp_path / "src"
    src.mkdir()

    # A check source file (excluded by EXCLUDE_RULES)
    (src / "preflight.py").write_text("oracle check code", encoding="utf-8")
    # A legitimately kept file
    (src / "main.py").write_text("project code", encoding="utf-8")

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["*.py"])

    # preflight.py must not be in projected_hashes
    assert "preflight.py" not in manifest["projected_hashes"], (
        "excluded file 'preflight.py' must not appear in projected_hashes"
    )
    # preflight.py must not be physically present in dest
    assert not (dest / "preflight.py").exists(), (
        "excluded file 'preflight.py' must not be physically copied to dest"
    )
    # main.py must be kept
    assert "main.py" in manifest["projected_hashes"], (
        "kept file 'main.py' must appear in projected_hashes"
    )
    assert (dest / "main.py").exists(), (
        "kept file 'main.py' must be physically present in dest"
    )


# ---------------------------------------------------------------------------
# test_content_hash_absent
# ---------------------------------------------------------------------------

def test_content_hash_absent(tmp_path):
    """A verbatim copy of an excluded file under a kept path is caught.

    Even though the copy lives at a kept path (not excluded by name), its
    content hash matches the excluded original -- verify_manifest must
    return a problem for this.
    """
    src = tmp_path / "src"
    src.mkdir()

    secret_content = "oracle data -- must not escape"
    # Excluded file
    (src / "binding.py").write_text(secret_content, encoding="utf-8")
    # Verbatim copy under a kept path
    (src / "my_binding_copy.py").write_text(secret_content, encoding="utf-8")

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["*.py"])

    # my_binding_copy.py is kept (name not excluded)
    assert "my_binding_copy.py" in manifest["projected_hashes"], (
        "my_binding_copy.py should be in projected_hashes (not excluded by path)"
    )

    problems = verify_manifest(manifest, src)
    assert problems, (
        "verify_manifest must detect content-hash collision (verbatim copy of excluded file)"
    )
    combined = " ".join(problems)
    assert "my_binding_copy.py" in combined or "binding.py" in combined, (
        f"problem message should name the offending files; got: {problems}"
    )


# ---------------------------------------------------------------------------
# test_symlink_resolved
# ---------------------------------------------------------------------------

def test_symlink_resolved(tmp_path):
    """A symlink in a kept path that resolves to an excluded file is caught.

    project() copies real content (resolves symlinks -- never a symlink into
    the exclude-set in dest). verify_manifest detects the content-hash match.
    """
    src = tmp_path / "src"
    src.mkdir()

    # Excluded file
    secret_content = "secret oracle content"
    secret = src / "preflight.py"
    secret.write_text(secret_content, encoding="utf-8")

    # Symlink at a kept path that resolves to the excluded file
    link = src / "innocent_module.py"
    try:
        link.symlink_to(secret)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform/fs")

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["*.py"])

    # innocent_module.py should have been copied (its path is not excluded)
    # but its content matches the excluded file
    problems = verify_manifest(manifest, src)
    assert problems, (
        "verify_manifest must detect that innocent_module.py has same content "
        "as excluded preflight.py (symlink resolved to excluded content)"
    )


# ---------------------------------------------------------------------------
# test_meta_properties
# ---------------------------------------------------------------------------

def test_meta_properties(tmp_path):
    """Meta-properties: keep_set x exclude_set == {} and check_sources <= exclude_set."""
    src = tmp_path / "src"
    src.mkdir()

    # Check source files (should be excluded)
    (src / "preflight.py").write_text("check code", encoding="utf-8")
    (src / "binding.py").write_text("binding code", encoding="utf-8")
    # Kept files
    (src / "my_code.py").write_text("project code", encoding="utf-8")
    (src / "data.txt").write_text("data", encoding="utf-8")

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["*.py", "*.txt"])

    keep = set(manifest["keep_set"])
    exc = set(manifest["exclude_set"])
    chk = set(manifest["check_sources"])

    # (c) keep_set x exclude_set == {}
    overlap = keep & exc
    assert not overlap, (
        f"keep_set and exclude_set must be disjoint; overlap: {sorted(overlap)}"
    )

    # (d) check_sources <= exclude_set
    orphans = chk - exc
    assert not orphans, (
        f"check_sources must be a subset of exclude_set; not covered: {sorted(orphans)}"
    )

    # Both check source files must appear in exclude_set and check_sources
    assert "preflight.py" in exc, "preflight.py must be in exclude_set"
    assert "binding.py" in exc, "binding.py must be in exclude_set"
    assert "preflight.py" in chk, "preflight.py must be in check_sources"
    assert "binding.py" in chk, "binding.py must be in check_sources"

    # Kept files must not be in exclude_set
    assert "my_code.py" not in exc, "my_code.py must not be in exclude_set"
    assert "data.txt" not in exc, "data.txt must not be in exclude_set"

    # verify_manifest must be clean
    problems = verify_manifest(manifest, src)
    assert not problems, f"clean fixture must have no problems; got: {problems}"


# ---------------------------------------------------------------------------
# test_clean_projection_ok
# ---------------------------------------------------------------------------

def test_clean_projection_ok(tmp_path):
    """A source tree with only kept files (no excluded files) yields no problems."""
    src = tmp_path / "src"
    src.mkdir()
    sub = src / "subpkg"
    sub.mkdir()

    (src / "main.py").write_text("entry point", encoding="utf-8")
    (src / "utils.py").write_text("utility functions", encoding="utf-8")
    (sub / "helper.py").write_text("helper module", encoding="utf-8")
    (src / "README.txt").write_text("readme text", encoding="utf-8")

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["*.py", "*.txt", "subpkg/*.py"])

    problems = verify_manifest(manifest, src)
    assert problems == [], (
        f"clean projection with no excluded files must yield no problems; got: {problems}"
    )

    # All four files should be projected
    assert "main.py" in manifest["projected_hashes"]
    assert "utils.py" in manifest["projected_hashes"]
    assert "subpkg/helper.py" in manifest["projected_hashes"]
    assert "README.txt" in manifest["projected_hashes"]
