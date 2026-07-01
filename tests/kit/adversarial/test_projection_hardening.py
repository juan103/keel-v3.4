"""Tests for projection.py Phase 3.5c hardening.

Six tests (Phase 3.5c Task 1 -- the foundational projection hardening):
  test_decode_normalize_reversible_layers
      -- decode_normalize recovers an excluded payload through each single
         reversible codec AND through nested layers (base64-of-hex), and is
         robust to garbage (a codec that does not apply is skipped, not raised).
  test_pyc_pycache_git_path_rule_excluded
      -- __pycache__/**, **/*.pyc, **/.git/** are stripped from the projected
         tree by path-rule (no keep_override), while ordinary files are kept.
  test_keep_override_keeps_fixture_git
      -- a per-call keep_override KEEPS a fixture's project-state .git (so the
         adr-edit/vacuous F1 stays green) even though a path-rule would strip it.
  test_kept_git_carrying_oracle_still_caught
      -- a KEPT .git blob whose decoded content matches an excluded oracle file
         is STILL flagged by verify_manifest (keep_override does not open a hole).
  test_env_manifest_flags_leak
      -- env_manifest flags env var VALUES that resolve into the exclude-set or
         the harness root, and leaves clean values alone.
  test_content_absent_on_decoded_form
      -- a reversible-encoded (base64) copy of an excluded file under a kept
         path is caught by verify_manifest's decode-normalization, even though
         its RAW content-hash differs from the excluded original.

ASCII-only.  Stdlib only (test-side).
"""
from __future__ import annotations

import base64
import binascii
import gzip
import sys
import urllib.parse
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import projection  # noqa: E402
from projection import (  # noqa: E402
    decode_normalize,
    env_manifest,
    project,
    verify_manifest,
)


# ---------------------------------------------------------------------------
# test_decode_normalize_reversible_layers
# ---------------------------------------------------------------------------

def test_decode_normalize_reversible_layers():
    """decode_normalize returns the original + every reversible-codec form.

    Single layers (base64, base32, hex, url, gzip, zlib) and one nested layer
    (base64-of-hex) must all surface the underlying payload.  A codec that does
    not apply (garbage input) is skipped, never raised.
    """
    payload = b"ORACLE-PAYLOAD-decode-normalize-12345\n"

    # The original is always in the set.
    assert payload in decode_normalize(payload)

    # Single reversible layers -- each decoded form must contain the payload.
    single_forms = {
        "base64": base64.b64encode(payload),
        "base32": base64.b32encode(payload),
        "hex": binascii.hexlify(payload),
        "url": urllib.parse.quote_from_bytes(payload, safe="").encode("ascii"),
        "gzip": gzip.compress(payload),
        "zlib": zlib.compress(payload),
    }
    for codec, encoded in single_forms.items():
        forms = decode_normalize(encoded)
        assert payload in forms, (
            f"decode_normalize must recover the payload through a single {codec} "
            f"layer; forms={sorted(len(f) for f in forms)}"
        )

    # Nested: base64( hex( payload ) ) -- two reversible layers, max_depth>=2.
    nested = base64.b64encode(binascii.hexlify(payload))
    forms = decode_normalize(nested, max_depth=3)
    assert payload in forms, (
        "decode_normalize must recover the payload through nested base64-of-hex"
    )

    # Robustness: garbage / non-codec input does not raise and returns at least
    # the original.
    garbage = b"\x00\x01\x02 not-a-codec << >> !!"
    g_forms = decode_normalize(garbage)
    assert garbage in g_forms

    # Bound: the form-set is finite (no unbounded blow-up).
    assert len(decode_normalize(nested)) <= 1024


# ---------------------------------------------------------------------------
# test_pyc_pycache_git_path_rule_excluded
# ---------------------------------------------------------------------------

def test_pyc_pycache_git_path_rule_excluded(tmp_path):
    """__pycache__/**, **/*.pyc, **/.git/** are stripped by path-rule."""
    src = tmp_path / "src"
    src.mkdir()

    (src / "main.py").write_text("project code", encoding="utf-8")
    # top-level .pyc
    (src / "module.pyc").write_bytes(b"\xde\xad\xbe\xef compiled")
    # __pycache__ dir with a nested pyc
    pyc_dir = src / "__pycache__"
    pyc_dir.mkdir()
    (pyc_dir / "module.cpython-313.pyc").write_bytes(b"\xca\xfe cached")
    # nested __pycache__
    nested_pyc = src / "pkg" / "__pycache__"
    nested_pyc.mkdir(parents=True)
    (nested_pyc / "x.cpython-313.pyc").write_bytes(b"\x00 nested cache")
    # a .git dir (transformed-form carrier)
    gitdir = src / ".git"
    gitdir.mkdir()
    (gitdir / "config").write_text("[core]\n", encoding="utf-8")
    (gitdir / "objects").mkdir()
    (gitdir / "objects" / "ab").mkdir()
    (gitdir / "objects" / "ab" / "cd").write_bytes(b"git object")

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["**"])

    hashes = manifest["projected_hashes"]
    # ordinary file kept
    assert "main.py" in hashes
    assert (dest / "main.py").exists()
    # path-ruled forms stripped from manifest AND from dest
    assert "module.pyc" not in hashes
    assert "__pycache__/module.cpython-313.pyc" not in hashes
    assert "pkg/__pycache__/x.cpython-313.pyc" not in hashes
    assert ".git/config" not in hashes
    assert ".git/objects/ab/cd" not in hashes
    assert not (dest / "module.pyc").exists()
    assert not (dest / "__pycache__").exists()
    assert not (dest / ".git").exists()

    # verify_manifest asserts the path-rule exclusions hold.
    problems = verify_manifest(manifest, src)
    assert problems == [], f"clean path-rule strip must yield no problems; got {problems}"


# ---------------------------------------------------------------------------
# test_keep_override_keeps_fixture_git
# ---------------------------------------------------------------------------

def test_keep_override_keeps_fixture_git(tmp_path):
    """A keep_override KEEPS a fixture's project-state .git (no oracle content)."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("project code", encoding="utf-8")
    gitdir = src / ".git"
    gitdir.mkdir()
    (gitdir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (gitdir / "config").write_text("[core]\n\trepositoryformatversion = 0\n", encoding="utf-8")
    objs = gitdir / "objects" / "ab"
    objs.mkdir(parents=True)
    # A git object that is ordinary project state -- no oracle content.
    (objs / "cd").write_bytes(zlib.compress(b"blob 12\x00hello world\n"))

    dest = tmp_path / "dest"
    keep_overrides = [".git/**", "**/.git/**"]
    manifest = project(src, dest, keep_globs=["**"], keep_overrides=keep_overrides)

    hashes = manifest["projected_hashes"]
    assert ".git/HEAD" in hashes, "keep_override must keep .git/HEAD"
    assert ".git/config" in hashes
    assert ".git/objects/ab/cd" in hashes
    assert (dest / ".git" / "HEAD").exists()
    assert (dest / ".git" / "objects" / "ab" / "cd").exists()

    # No oracle content -> verify_manifest clean even with the .git kept.
    problems = verify_manifest(manifest, src)
    assert problems == [], f"kept project-state .git must be clean; got {problems}"


# ---------------------------------------------------------------------------
# test_kept_git_carrying_oracle_still_caught
# ---------------------------------------------------------------------------

def test_kept_git_carrying_oracle_still_caught(tmp_path):
    """A KEPT .git blob whose decoded content matches an excluded file is flagged.

    The keep_override keeps the .git path, but verify_manifest content-checks
    every kept file (including its decode-normalized forms), so a .git object
    that is a zlib-compressed copy of an excluded oracle file is still caught.
    """
    src = tmp_path / "src"
    src.mkdir()

    oracle = b"OR4CLE-GIT-BLOB-secret-check-source\n"
    # Excluded oracle file (matches EXCLUDE_RULES by name).  Write BYTES, not
    # text: Path.write_text would translate "\n" -> os.linesep on Windows and the
    # on-disk content would no longer match the compressed-blob bytes below.
    (src / "binding.py").write_bytes(oracle)
    (src / "main.py").write_text("project code", encoding="utf-8")

    gitdir = src / ".git" / "objects" / "zz"
    gitdir.mkdir(parents=True)
    # A .git blob that is a zlib-compressed VERBATIM copy of the oracle bytes.
    # Its RAW hash differs from the oracle, but decode-normalization (zlib)
    # recovers the oracle content -> must be flagged.
    (gitdir / "blob").write_bytes(zlib.compress(oracle))

    dest = tmp_path / "dest"
    keep_overrides = [".git/**", "**/.git/**"]
    manifest = project(src, dest, keep_globs=["**"], keep_overrides=keep_overrides)

    # The .git blob WAS kept (keep_override beat the path-rule).
    assert ".git/objects/zz/blob" in manifest["projected_hashes"], (
        "keep_override must keep the .git blob so the content-check can run on it"
    )
    # binding.py is excluded (not projected).
    assert "binding.py" not in manifest["projected_hashes"]

    problems = verify_manifest(manifest, src)
    assert problems, (
        "a kept .git blob carrying decode-reachable oracle content must be flagged"
    )
    combined = " ".join(problems)
    assert ".git/objects/zz/blob" in combined or "binding.py" in combined, (
        f"problem must name the offending kept .git blob / oracle; got {problems}"
    )


# ---------------------------------------------------------------------------
# test_env_manifest_flags_leak
# ---------------------------------------------------------------------------

def test_env_manifest_flags_leak(tmp_path):
    """env_manifest flags env values that resolve into the exclude-set / harness root."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / "main.py").write_text("ok", encoding="utf-8")

    harness_root = Path(projection.__file__).resolve().parent

    env = {
        "PATH_OK": "main.py",                       # ordinary sandbox file -- clean
        "PLAIN_OK": "some-token-value",             # not a path -- clean
        "ORACLE_NAME": "preflight.py",              # names an excluded oracle file
        "GIT_LEAK": "sub/.git/config",              # path-rule oracle-transform carrier
        "HARNESS_ABS": str(harness_root / "binding.py"),  # resolves into the harness root
    }

    problems = env_manifest(env, sandbox)
    blob = " ".join(problems)

    assert "ORACLE_NAME" in blob, f"must flag the excluded-name value; got {problems}"
    assert "GIT_LEAK" in blob, f"must flag the .git path-rule value; got {problems}"
    assert "HARNESS_ABS" in blob, f"must flag the harness-root path; got {problems}"
    assert "PATH_OK" not in blob, f"must NOT flag an ordinary sandbox file; got {problems}"
    assert "PLAIN_OK" not in blob, f"must NOT flag a non-path token; got {problems}"


# ---------------------------------------------------------------------------
# test_content_absent_on_decoded_form
# ---------------------------------------------------------------------------

def test_content_absent_on_decoded_form(tmp_path):
    """A base64-encoded copy of an excluded file under a kept path is caught.

    The raw content-hash of the encoded copy differs from the excluded original
    (so check (b) alone misses it); only decode-normalization recovers the match.
    """
    src = tmp_path / "src"
    src.mkdir()

    secret = b"ORACLE-SECRET-CONTENT-encoded-copy-test\n"
    (src / "binding.py").write_bytes(secret)  # excluded by name
    # A kept file whose content is the base64 encoding of the excluded bytes.
    encoded = base64.b64encode(secret)
    (src / "notes.dat").write_bytes(encoded)

    dest = tmp_path / "dest"
    manifest = project(src, dest, keep_globs=["**"])

    # notes.dat is kept; its RAW hash != the excluded hash.
    assert "notes.dat" in manifest["projected_hashes"]
    raw_secret_hash = manifest["projected_hashes"]["notes.dat"]
    import hashlib
    assert raw_secret_hash != hashlib.sha256(secret).hexdigest(), (
        "the encoded copy's RAW hash must differ from the excluded original "
        "(otherwise this would not exercise decode-normalization)"
    )

    problems = verify_manifest(manifest, src)
    assert problems, (
        "verify_manifest must catch the base64-encoded copy via decode-normalization"
    )
    combined = " ".join(problems)
    assert "notes.dat" in combined, (
        f"problem must name the encoded copy notes.dat; got {problems}"
    )
