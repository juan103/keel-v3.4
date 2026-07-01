"""F3 projection-leak falsifier -- inject each oracle-leak channel, assert closed or named.

Phase 3.5c Task 2.  Each test injects ONE channel into a synthetic source tree
and asserts the real projection / verify_manifest / env_manifest catches it
(CLOSED), or that the channel is NAMED as a residue in projection.py's docstring
(NAMED residue, not silently claimed closed).

Channels tested:
  test_f3_new_check_source
      -- brand-new file matching the check-source glob is excluded (rule-derived
         glob, not an enumerated allowlist).
  test_f3_symlink_into_exclude
      -- symlink pointing into the exclude-set is caught via content-hash
         (skip-guard on Windows if symlinks are unavailable).
  test_f3_verbatim_content_dup
      -- verbatim copy of excluded file under a kept path is flagged by
         verify_manifest (content-hash collision).
  test_f3_reversible_encoded_copy
      -- base64, hex, gzip encoded copies, plus one nesting (base64-of-hex),
         of excluded content are caught by decode-normalization; raw hashes differ.
  test_f3_pyc_pycache_excluded
      -- __pycache__/x.pyc of an excluded module is path-rule-excluded from
         the projection (not kept under any glob).
  test_f3_oracle_git_caught_vs_project_state_git_kept
      -- Part A: a .git blob carrying zlib-compressed oracle content is flagged
         by verify_manifest EVEN WHEN a keep_override keeps .git paths
         (keep-override-opens-no-hole proof).
         Part B: a fixture project-state .git with NO oracle content is kept and
         passes verify_manifest cleanly.
  test_f3_parent_traversal
      -- no projected path contains '..' (path-escape is closed); content of a
         symlink-outside-src is still content-checked.
  test_f3_env_state_leak
      -- env var values resolving into the exclude-set or the harness root are
         flagged by env_manifest; clean values are not.
  test_f3_named_residues_documented
      -- the four un-closable residue channels (installed-module reachability,
         unbounded transforms, residual env, paraphrase) are NAMED in
         projection.py's docstring, not silently missing.

ASCII-only.  Stdlib only (test-side).  Not wired into preflight.
"""
from __future__ import annotations

import base64
import binascii
import gzip
import hashlib
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest

import projection  # noqa: E402
from projection import (  # noqa: E402
    env_manifest,
    project,
    verify_manifest,
)


# ---------------------------------------------------------------------------
# Shared oracle payload
# ---------------------------------------------------------------------------

# A distinctive byte sequence used as the "oracle secret" in all injection
# tests.  It must be present in the excluded file to drive content-hash checks.
_ORACLE_BYTES = b"F3-ORACLE-SECRET-keel-v3.4-do-not-leak\n"


def _make_excluded_oracle(src: Path) -> None:
    """Write _ORACLE_BYTES to binding.py (excluded by EXCLUDE_RULES) in src."""
    (src / "binding.py").write_bytes(_ORACLE_BYTES)


# ---------------------------------------------------------------------------
# test_f3_new_check_source
# ---------------------------------------------------------------------------

def test_f3_new_check_source(tmp_path):
    """A brand-new file matching the check-source glob is excluded.

    EXCLUDE_RULES contains "tests/kit/adversarial/**" which catches ANY new
    file added under that directory without a new individual entry.  This test
    injects a brand-new (not individually listed) file and asserts the
    rule-derived exclude-set catches it: the channel is CLOSED by the glob.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("project code", encoding="utf-8")

    # Brand-new check-source file: not in _CHECK_SOURCE_RULES by name, but
    # matched by the "tests/kit/adversarial/**" wildcard in EXCLUDE_RULES.
    new_dir = src / "tests" / "kit" / "adversarial"
    new_dir.mkdir(parents=True)
    (new_dir / "new_scenario_check_v99.py").write_text(
        "oracle = 'must-be-excluded-by-glob'\n", encoding="utf-8"
    )

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["**"])

    new_rel = "tests/kit/adversarial/new_scenario_check_v99.py"

    # Must appear in exclude_set via the derived glob rule.
    assert new_rel in manifest["exclude_set"], (
        "brand-new file under tests/kit/adversarial/ must be in exclude_set "
        "via the derived glob rule (rule-derived, not enumerated allowlist)"
    )
    # Must NOT appear in projected_hashes.
    assert new_rel not in manifest["projected_hashes"], (
        "brand-new check-source file must not appear in projected_hashes"
    )
    # Must NOT be physically present in dest.
    dest_file = dest / "tests" / "kit" / "adversarial" / "new_scenario_check_v99.py"
    assert not dest_file.exists(), (
        "brand-new check-source file must not be physically copied to dest"
    )
    # Ordinary kept file is projected.
    assert "main.py" in manifest["projected_hashes"]

    problems = verify_manifest(manifest, src)
    assert problems == [], f"clean projection must yield no problems; got {problems}"


# ---------------------------------------------------------------------------
# test_f3_symlink_into_exclude
# ---------------------------------------------------------------------------

def test_f3_symlink_into_exclude(tmp_path):
    """A symlink pointing into the exclude-set is caught via content-hash.

    project() resolves symlinks (copies real content, never a symlink into
    the exclude-set in dest).  verify_manifest detects the content-hash match
    between the projected copy and the excluded original.
    """
    src = tmp_path / "src"
    src.mkdir()
    _make_excluded_oracle(src)   # binding.py (excluded by name)

    link = src / "innocent_link.py"
    try:
        link.symlink_to(src / "binding.py")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform/fs")

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["*.py"])

    # The symlink path is not excluded by name, so it should be projected.
    assert "innocent_link.py" in manifest["projected_hashes"], (
        "symlink at a kept path must appear in projected_hashes (before content-check)"
    )
    # binding.py is excluded; its hash must be known to verify_manifest.
    assert "binding.py" not in manifest["projected_hashes"]

    problems = verify_manifest(manifest, src)
    assert problems, (
        "verify_manifest must catch the symlink-into-exclude via content-hash"
    )
    combined = " ".join(problems)
    assert "innocent_link.py" in combined or "binding.py" in combined, (
        f"problem must name the offending symlink / excluded file; got {problems}"
    )


# ---------------------------------------------------------------------------
# test_f3_verbatim_content_dup
# ---------------------------------------------------------------------------

def test_f3_verbatim_content_dup(tmp_path):
    """Verbatim copy of an excluded file under a kept path is flagged (content-hash).

    The copy lives at a kept path (not excluded by name), but its SHA-256
    matches the excluded original: verify_manifest must detect this collision.
    """
    src = tmp_path / "src"
    src.mkdir()
    _make_excluded_oracle(src)   # binding.py (excluded)
    # Verbatim copy at a kept path.
    (src / "my_copy.dat").write_bytes(_ORACLE_BYTES)

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["**"])

    # my_copy.dat is not excluded by name; it must be in the projection.
    assert "my_copy.dat" in manifest["projected_hashes"], (
        "verbatim copy at a kept path must be in projected_hashes (not excluded by name)"
    )

    problems = verify_manifest(manifest, src)
    assert problems, (
        "verify_manifest must detect content-hash collision for verbatim copy of "
        "excluded file"
    )
    combined = " ".join(problems)
    assert "my_copy.dat" in combined or "binding.py" in combined, (
        f"problem must name the offending copy / excluded file; got {problems}"
    )


# ---------------------------------------------------------------------------
# test_f3_reversible_encoded_copy
# ---------------------------------------------------------------------------

def test_f3_reversible_encoded_copy(tmp_path):
    """Reversible-encoded copies of excluded content are caught by decode-normalization.

    Channels injected: base64, hex, gzip (single layer), and base64-of-hex (one
    nesting level).  Each encoded copy has a RAW hash that differs from the
    excluded original; only decode-normalization recovers the match.
    """
    oracle = _ORACLE_BYTES
    oracle_hash = hashlib.sha256(oracle).hexdigest()

    channels = [
        ("b64_copy.dat", base64.b64encode(oracle)),
        ("hex_copy.dat", binascii.hexlify(oracle)),
        ("gz_copy.dat",  gzip.compress(oracle)),
        # one nesting: base64( hex( oracle ) )
        ("nested_b64hex.dat", base64.b64encode(binascii.hexlify(oracle))),
    ]

    for i, (filename, encoded) in enumerate(channels):
        src = tmp_path / f"src_{i}"
        src.mkdir()
        _make_excluded_oracle(src)   # binding.py (excluded)
        (src / filename).write_bytes(encoded)

        # Confirm the encoded copy's raw hash differs from the oracle hash;
        # otherwise this would not exercise decode-normalization at all.
        encoded_hash = hashlib.sha256(encoded).hexdigest()
        assert encoded_hash != oracle_hash, (
            f"{filename}: encoded copy raw hash must differ from oracle hash "
            f"(otherwise decode-normalization is not exercised)"
        )

        dest = tmp_path / f"dest_{i}"
        manifest = project(src, dest, keep_globs=["**"])

        # The encoded copy must be in projected_hashes (not excluded by name).
        assert filename in manifest["projected_hashes"], (
            f"{filename} must be in projected_hashes (not excluded by name)"
        )

        problems = verify_manifest(manifest, src)
        assert problems, (
            f"verify_manifest must catch {filename} (encoded oracle copy) via "
            f"decode-normalization; got no problems"
        )
        combined = " ".join(problems)
        assert filename in combined or "binding.py" in combined, (
            f"{filename}: problem must name the encoded copy / excluded file; "
            f"got {problems}"
        )


# ---------------------------------------------------------------------------
# test_f3_pyc_pycache_excluded
# ---------------------------------------------------------------------------

def test_f3_pyc_pycache_excluded(tmp_path):
    """__pycache__/x.pyc of an excluded module is path-rule-excluded.

    Even if the .pyc content were a transformed form of oracle bytes, the
    path-rule strips it from the projection BY PATH before any content check
    is needed -- the path-rule closes this channel at the naming layer.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("project code", encoding="utf-8")

    # Pseudo-pyc in __pycache__ for excluded module binding.py.
    pyc_dir = src / "__pycache__"
    pyc_dir.mkdir()
    pyc_file = pyc_dir / "binding.cpython-313.pyc"
    pyc_file.write_bytes(b"\xde\xad\xbe\xef" + _ORACLE_BYTES)

    # Top-level .pyc (no __pycache__ dir).
    top_pyc = src / "binding.pyc"
    top_pyc.write_bytes(b"\xca\xfe\xba\xbe" + _ORACLE_BYTES)

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["**"])

    # Both must be stripped by the path-rule -- absent from projected_hashes.
    assert "__pycache__/binding.cpython-313.pyc" not in manifest["projected_hashes"], (
        "__pycache__/binding.cpython-313.pyc must be stripped by path-rule"
    )
    assert "binding.pyc" not in manifest["projected_hashes"], (
        "top-level binding.pyc must be stripped by path-rule"
    )
    # Physical absence in dest.
    assert not (dest / "__pycache__").exists(), (
        "__pycache__ dir must not be created in dest"
    )
    assert not (dest / "binding.pyc").exists(), (
        "binding.pyc must not be physically copied to dest"
    )
    # Both must appear in stripped_by_path_rule manifest field.
    stripped = manifest["stripped_by_path_rule"]
    assert "__pycache__/binding.cpython-313.pyc" in stripped, (
        "must appear in stripped_by_path_rule"
    )
    assert "binding.pyc" in stripped, (
        "top-level .pyc must appear in stripped_by_path_rule"
    )
    # Ordinary kept file is present.
    assert "main.py" in manifest["projected_hashes"]

    problems = verify_manifest(manifest, src)
    assert problems == [], f"clean projection after path-rule strip; got {problems}"


# ---------------------------------------------------------------------------
# test_f3_oracle_git_caught_vs_project_state_git_kept
# ---------------------------------------------------------------------------

def test_f3_oracle_git_caught_vs_project_state_git_kept(tmp_path):
    """Load-bearing keep-override-opens-no-hole proof (mirrors T1's proof).

    Part A (oracle caught): a .git blob carrying zlib-compressed oracle content
    is flagged by verify_manifest EVEN WHEN a keep_override keeps .git paths.
    keep_override does NOT bypass the content / decode-normalization check.

    Part B (project-state kept): a fixture .git with ordinary project-state
    content (no oracle bytes) is kept and passes verify_manifest cleanly.
    The keep_override correctly admits it without false positives.
    """
    oracle = _ORACLE_BYTES
    keep_overrides = [".git/**", "**/.git/**"]

    # ------------------------------------------------------------------ Part A
    src_a = tmp_path / "src_a"
    src_a.mkdir()
    (src_a / "binding.py").write_bytes(oracle)   # excluded oracle file
    (src_a / "main.py").write_text("project code", encoding="utf-8")

    git_obj_dir_a = src_a / ".git" / "objects" / "ab"
    git_obj_dir_a.mkdir(parents=True)
    # .git blob = zlib-compressed verbatim oracle bytes.  Raw hash differs
    # from the oracle, but decode-normalization (zlib layer) recovers it.
    (git_obj_dir_a / "cd").write_bytes(zlib.compress(oracle))

    dest_a = tmp_path / "dest_a"
    manifest_a = project(src_a, dest_a, keep_globs=["**"], keep_overrides=keep_overrides)

    # The .git blob must be KEPT (keep_override beat the path-rule) so that
    # the content-check can run on it.
    assert ".git/objects/ab/cd" in manifest_a["projected_hashes"], (
        "Part A: keep_override must keep the .git blob so content-check can run"
    )
    # Oracle file itself must be excluded.
    assert "binding.py" not in manifest_a["projected_hashes"], (
        "Part A: binding.py (oracle) must not appear in the projection"
    )

    problems_a = verify_manifest(manifest_a, src_a)
    assert problems_a, (
        "Part A: a kept .git blob carrying decode-reachable oracle content must be "
        "flagged -- keep_override does not open a hole"
    )
    combined_a = " ".join(problems_a)
    assert ".git/objects/ab/cd" in combined_a or "binding.py" in combined_a, (
        f"Part A: problem must name the offending .git blob or oracle; got {problems_a}"
    )

    # ------------------------------------------------------------------ Part B
    src_b = tmp_path / "src_b"
    src_b.mkdir()
    (src_b / "main.py").write_text("project code", encoding="utf-8")

    git_obj_dir_b = src_b / ".git" / "objects" / "zz"
    git_obj_dir_b.mkdir(parents=True)
    (src_b / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    # Ordinary project-state git blob: zlib("blob 5\x00hello") -- no oracle content.
    (git_obj_dir_b / "ee").write_bytes(zlib.compress(b"blob 5\x00hello"))

    dest_b = tmp_path / "dest_b"
    manifest_b = project(src_b, dest_b, keep_globs=["**"], keep_overrides=keep_overrides)

    assert ".git/HEAD" in manifest_b["projected_hashes"], (
        "Part B: keep_override must keep the fixture .git HEAD"
    )
    assert ".git/objects/zz/ee" in manifest_b["projected_hashes"], (
        "Part B: keep_override must keep the fixture project-state .git object"
    )

    problems_b = verify_manifest(manifest_b, src_b)
    assert problems_b == [], (
        f"Part B: fixture project-state .git with no oracle content must be clean; "
        f"got {problems_b}"
    )


# ---------------------------------------------------------------------------
# test_f3_parent_traversal
# ---------------------------------------------------------------------------

def test_f3_parent_traversal(tmp_path):
    """No projected path contains '..' (parent-directory traversal is closed).

    Baseline: os.walk + relative_to() ensures projected keys are always
    clean relative paths -- no '..' escape.

    Symlink injection: a symlink inside src pointing OUTSIDE src resolves to
    external content (which is still content-checked), but the PROJECTED KEY
    uses the symlink's own within-src relative path -- no '..' component.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("project code", encoding="utf-8")

    # Baseline assertion: a clean projection never has '..' in any projected path.
    dest_base = tmp_path / "dest_base"
    manifest_base = project(src, dest_base, keep_globs=["**"])
    for rel in manifest_base["projected_hashes"]:
        assert ".." not in rel.split("/"), (
            f"projected path '{rel}' must not contain '..' (baseline)"
        )

    # Symlink injection: a symlink inside src pointing to a file OUTSIDE src.
    outside = tmp_path / "outside_ordinary.txt"
    outside.write_text("ordinary content outside src -- not oracle", encoding="utf-8")
    link = src / "link_to_outside.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        # Baseline assertion already ran above; symlink part not supported here.
        pytest.skip("symlinks not supported on this platform/fs; baseline passed")

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["**"])

    # No projected path must have '..' regardless of symlink resolution.
    for rel in manifest["projected_hashes"]:
        assert ".." not in rel.split("/"), (
            f"projected path '{rel}' must not contain '..' (symlink-outside-src case)"
        )

    # The symlink's within-src path is the projected key (not an escaped path).
    assert "link_to_outside.txt" in manifest["projected_hashes"], (
        "symlink's own within-src path must be the projected key"
    )

    # Content of the symlink (ordinary, not oracle) must pass verify_manifest.
    problems = verify_manifest(manifest, src)
    assert problems == [], (
        f"symlink to ordinary outside content must produce no problems; got {problems}"
    )


# ---------------------------------------------------------------------------
# test_f3_env_state_leak
# ---------------------------------------------------------------------------

def test_f3_env_state_leak(tmp_path):
    """Env var values resolving into the exclude-set / harness root are flagged.

    Three leak channels injected:
      ORACLE_NAME  -- names an excluded oracle path directly (EXCLUDE_RULES).
      GIT_LEAK     -- names a path-rule carrier (.git/...).
      HARNESS_ABS  -- an absolute path that resolves into the harness root.

    Clean env vars are NOT flagged (no false positives).
    """
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / "main.py").write_text("project code", encoding="utf-8")

    harness_root = Path(projection.__file__).resolve().parent

    env = {
        "CLEAN_PATH":   "main.py",                # ordinary sandbox file -- clean
        "CLEAN_TOKEN":  "some-random-value-abc",  # non-path token -- clean
        "ORACLE_NAME":  "preflight.py",           # names an excluded oracle file
        "GIT_LEAK":     "sub/.git/config",        # path-rule carrier
        "HARNESS_ABS":  str(harness_root / "binding.py"),  # resolves into harness root
    }

    problems = env_manifest(env, sandbox)
    blob = " ".join(problems)

    assert "ORACLE_NAME" in blob, (
        f"must flag the excluded-name env var ORACLE_NAME; got {problems}"
    )
    assert "GIT_LEAK" in blob, (
        f"must flag the .git path-rule env var GIT_LEAK; got {problems}"
    )
    assert "HARNESS_ABS" in blob, (
        f"must flag the harness-root env var HARNESS_ABS; got {problems}"
    )
    assert "CLEAN_PATH" not in blob, (
        f"must NOT flag ordinary sandbox file CLEAN_PATH; got {problems}"
    )
    assert "CLEAN_TOKEN" not in blob, (
        f"must NOT flag non-path token CLEAN_TOKEN; got {problems}"
    )


# ---------------------------------------------------------------------------
# test_f3_named_residues_documented
# ---------------------------------------------------------------------------

def test_f3_named_residues_documented():
    """Un-closable residue channels are NAMED in projection.py's docstring.

    Four channels cannot be closed by this module in Phase 3.5c.  Each must
    be NAMED (honest scope) -- not silently claimed closed.  This test asserts
    their names appear in the module docstring.

    Channels (and keywords searched for):
      installed-module reachability  -> "installed-module" or "site-packages"
      unbounded / nested transforms  -> "unbounded"
      residual env                   -> "residual env"
      paraphrase                     -> "paraphrase"
    """
    doc = (getattr(projection, "__doc__", "") or "").lower()
    assert doc, "projection.py must have a module docstring"

    residues = [
        ("installed-module reachability", ["installed-module", "site-packages"]),
        ("unbounded / nested transforms", ["unbounded"]),
        ("residual env",                  ["residual env"]),
        ("paraphrase",                    ["paraphrase"]),
    ]
    for name, keywords in residues:
        found = any(kw.lower() in doc for kw in keywords)
        assert found, (
            f"residue channel '{name}' must be NAMED in projection.py docstring "
            f"(not silently claimed closed); searched for: {keywords}"
        )
