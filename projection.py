"""projection.py -- rule-derived workspace projection for the adversarial-exercise harness.

Phase 3.5a: core projection -- rule-derived exclude-set, path-absence + content-hash
absence, symlink resolution, keep/exclude disjointness and check-sources-in-exclude
meta-property asserts.

Phase 3.5c (IMPLEMENTED below): the three 3.5a extension points are now live, plus
per-scenario keep-overrides:
  - decode-normalization: each projected file's content is decoded through a
    bounded, enumerated set of REVERSIBLE codecs (base64, base32, hex, URL-encoding,
    gzip, zlib) recursively to a depth bound, and every decoded form is re-tested
    for content-absence.  This catches a reversible-encoded copy of an excluded
    file (e.g. a base64 blob, or a zlib-compressed .git object) hiding under a
    kept path.
  - transformed-format path-rules: __pycache__/**, **/*.pyc and **/.git/** are
    stripped from the projected tree by PATH (they carry transformed oracle forms
    that content-hash/decode cannot always catch) -- EXCEPT paths matched by a
    per-call keep_overrides glob list.
  - keep_overrides: a per-scenario list of globs that are KEPT even when a path-rule
    would strip them (a scenario's fixture .git is PROJECT STATE built WITHOUT
    oracle content -- it must survive projection so the git-history named checks
    run).  A kept path is STILL content-checked (verify_manifest), so a kept .git
    carrying oracle content is still caught: keep_overrides do not open a hole.
  - env-scrub: env_manifest() flags any environment-variable VALUE that resolves
    into the rule-derived exclude surface or the harness (oracle) root.

NAMED RESIDUES (channels NOT closed by this module -- do NOT claim them closed):
  - installed-module reachability: an excluded check imported from site-packages
    (not from a file under source_root) is invisible to a path/content projection.
  - unbounded / nested semantic transforms: decode_normalize is bounded (a fixed
    codec set, a depth bound, a form-count bound).  An encoding outside the set, a
    nesting depth beyond the bound, or a NON-reversible / semantic transform
    (summarise, paraphrase, re-implement) is not normalized away.
  - residual env: env_manifest inspects VALUES passed to it; an env channel never
    passed in, or a value that leaks oracle SEMANTICS rather than a path, is not
    covered.
  - paraphrase: a human/agent re-description of oracle content carries no byte
    correspondence and is out of scope for any hash/decode comparison here.

Scope:
  - EXCLUDE_RULES: globs naming the oracle surface (matched by name).
  - PATH_EXCLUDE_RULES: path-rule globs for transformed oracle forms.
  - project(source_root, dest, keep_globs, keep_overrides=()) -> manifest dict.
  - verify_manifest(manifest, source_root) -> list[str] (empty == clean).
  - decode_normalize(data, max_depth=3) -> set[bytes].
  - env_manifest(env, source_root) -> list[str].

ASCII-only strings throughout.  Stdlib only: base64, binascii, gzip, zlib,
urllib.parse, hashlib, fnmatch, pathlib, os, shutil, io.
"""

import base64
import binascii
import fnmatch
import gzip
import hashlib
import io
import os
import shutil
import urllib.parse
import zlib
from pathlib import Path


# ---------------------------------------------------------------------------
# Oracle exclude surface
# ---------------------------------------------------------------------------

# Globs matched against repo-relative POSIX paths.  fnmatch semantics: '**'
# is equivalent to '*' (fnmatch treats '/' as a regular character, so a
# single '*' or '**' both cross directory boundaries).
EXCLUDE_RULES: list[str] = [
    # Adversarial test kit: per-scenario detectors, predicates, keyword sets,
    # retained witnesses, scenario specs, and the test suite itself.
    "tests/kit/adversarial/**",
    # Check source files (the oracle surface; agent must NOT read these to pass).
    "preflight.py",
    "binding.py",
    "commitment_lock.py",
    "runtime_roles.py",
    "attest.py",
    "pilot.py",
    "hazard_coverage.py",
    "check_coverage.py",
    "adr_guard.py",
    "assumptions.py",
    "freshness.py",
    "log_integrity.py",
    "reachability.py",
    # Goals / harness oracle files.
    "goals/hazard-coverage.md",
    "goals/.harness-contract.json",
    "goals/.harness-ledger.jsonl",
]

# Subset of EXCLUDE_RULES that identifies "check sources" (the named kit check
# modules).  Used to validate the check_sources <= exclude_set meta-property.
_CHECK_SOURCE_RULES: list[str] = [
    "preflight.py",
    "binding.py",
    "commitment_lock.py",
    "runtime_roles.py",
    "attest.py",
    "pilot.py",
    "hazard_coverage.py",
    "check_coverage.py",
    "adr_guard.py",
    "assumptions.py",
    "freshness.py",
    "log_integrity.py",
    "reachability.py",
]

# Phase 3.5c path-rules.  These are the HUMAN-READABLE globs for the transformed
# oracle-form carriers.  Matching is implemented component-wise in
# _path_rule_excluded (depth-independent), because plain fnmatch globs of the
# form "**/*.pyc" do not match a top-level "x.pyc" (fnmatch's '**' requires the
# literal '/' that follows it).  The list is exported for documentation/manifest.
PATH_EXCLUDE_RULES: list[str] = [
    "__pycache__/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "*.pyc",
    "**/.git/**",
    ".git/**",
]

# Directory names whose presence anywhere in a path triggers a path-rule strip.
_PATH_RULE_DIRS = ("__pycache__", ".git")

# The harness (oracle) root: the directory holding this module and the real
# check sources.  env_manifest flags values that resolve into it.
_HARNESS_ROOT = Path(__file__).resolve().parent

# decode_normalize bounds (anti-blow-up + anti-decompression-bomb).
_DECODE_MAX_FORMS = 256          # total normalized-form set size bound
_DECODE_MAX_BYTES = 1 << 22      # 4 MiB cap per decoded form


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of a file's binary content."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel_posix(abs_path: Path, root: Path) -> str:
    """Return the POSIX-style path of abs_path relative to root."""
    return abs_path.relative_to(root).as_posix()


def _matches_any(rel: str, patterns) -> bool:
    """Return True if rel matches at least one fnmatch pattern."""
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat):
            return True
    return False


def _path_rule_excluded(rel: str) -> bool:
    """True if rel is a transformed-oracle-form carrier (path-rule strip).

    Depth-independent semantics for PATH_EXCLUDE_RULES:
      - any path component is __pycache__ or .git  -> excluded
      - the path ends in .pyc                       -> excluded
    """
    parts = rel.split("/")
    if any(p in _PATH_RULE_DIRS for p in parts):
        return True
    if rel.endswith(".pyc"):
        return True
    return False


def _is_relative_to(child: Path, parent: Path) -> bool:
    """Backport of Path.is_relative_to (3.9+) for resolved paths."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def _safe_rel(child: Path, parent: Path):
    """Return child relative to parent as POSIX, or None if not under parent."""
    try:
        return child.resolve().relative_to(parent.resolve()).as_posix()
    except (ValueError, OSError):
        return None


# ---------------------------------------------------------------------------
# decode_normalize() -- reversible-codec normalization (Phase 3.5c)
# ---------------------------------------------------------------------------

def _dec_base64(data: bytes):
    """Strict standard-alphabet base64 decode, or None if not applicable."""
    if len(data) < 4 or len(data) % 4 != 0:
        return None
    return base64.b64decode(data, validate=True)


def _dec_base32(data: bytes):
    """Strict base32 decode, or None if not applicable."""
    if len(data) < 8 or len(data) % 8 != 0:
        return None
    return base64.b32decode(data)


def _dec_hex(data: bytes):
    """Hex decode, or None if not applicable."""
    if len(data) < 2 or len(data) % 2 != 0:
        return None
    return binascii.unhexlify(data)


def _dec_url(data: bytes):
    """URL-percent decode (never raises; identity when no %XX present)."""
    return urllib.parse.unquote_to_bytes(data)


def _dec_gzip(data: bytes):
    """Bounded gzip decompress, or None if not applicable / over the cap."""
    if len(data) < 2 or data[:2] != b"\x1f\x8b":
        return None
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as gf:
        out = gf.read(_DECODE_MAX_BYTES + 1)
    if len(out) > _DECODE_MAX_BYTES:
        return None
    return out


def _dec_zlib(data: bytes):
    """Bounded zlib decompress, or None if not applicable / over the cap."""
    if len(data) < 2:
        return None
    out = zlib.decompressobj().decompress(data, _DECODE_MAX_BYTES + 1)
    if len(out) > _DECODE_MAX_BYTES:
        return None
    return out


# Enumerated, bounded REVERSIBLE codec set.  An encoding outside this set is a
# NAMED residue (see module docstring), not silently covered.
_DECODERS = (_dec_base64, _dec_base32, _dec_hex, _dec_url, _dec_gzip, _dec_zlib)


def decode_normalize(data: bytes, max_depth: int = 3) -> set:
    """Return {data} plus every form reachable by reversible codecs to max_depth.

    For each form, every decoder in _DECODERS is attempted; a decoder that raises
    or does not apply is skipped.  A decoded form that is new (not already seen)
    is added and itself decoded, recursively, up to max_depth layers.  The total
    set size is bounded by _DECODE_MAX_FORMS and each form by _DECODE_MAX_BYTES,
    so the enumeration cannot blow up (and a decompression bomb is capped).

    Used by verify_manifest so a reversible-encoded copy of an excluded file
    (e.g. base64 text, or a zlib-compressed .git object) is caught by comparing
    EACH decoded form's content-hash against the excluded files.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("decode_normalize requires bytes")
    data = bytes(data)
    forms = {data}
    frontier = [(data, 0)]
    while frontier:
        cur, depth = frontier.pop()
        if depth >= max_depth:
            continue
        for dec in _DECODERS:
            if len(forms) >= _DECODE_MAX_FORMS:
                return forms
            try:
                out = dec(cur)
            except Exception:  # noqa: BLE001 -- a codec that does not apply is skipped
                continue
            if not out or out == cur or out in forms or len(out) > _DECODE_MAX_BYTES:
                continue
            forms.add(out)
            frontier.append((out, depth + 1))
    return forms


# ---------------------------------------------------------------------------
# env_manifest() -- env-scrub leak detection (Phase 3.5c)
# ---------------------------------------------------------------------------

def env_manifest(env: dict, source_root: Path) -> list[str]:
    """Flag env var VALUES that resolve into the exclude-set or the harness root.

    A value is flagged when either:
      (1) interpreted as a sandbox-relative path, it matches the rule-derived
          exclude surface (EXCLUDE_RULES or a path-rule), OR
      (2) interpreted as a filesystem path (absolute, or relative to source_root),
          it resolves into the harness (oracle) root while escaping the sandbox.

    Returns a list of problem strings (empty == no env leak detected).  This is a
    standalone detector -- NOT wired into preflight or the projection pipeline.
    """
    source_root = Path(source_root).resolve()
    problems: list[str] = []
    for name in sorted(env):
        value = env[name]
        if not isinstance(value, str) or not value:
            continue
        reason = _env_value_leak_reason(value, source_root)
        if reason:
            problems.append(f"env var {name!r} value {value!r} {reason}")
    return problems


def _env_value_leak_reason(value: str, source_root: Path) -> str:
    """Return a leak-reason string for an env value, or '' if it is clean."""
    rel_norm = value.replace("\\", "/").lstrip("/")
    # (1) sandbox-relative name matching the rule-derived exclude surface.
    if _matches_any(rel_norm, EXCLUDE_RULES) or _path_rule_excluded(rel_norm):
        return f"names an excluded oracle path ({rel_norm})"
    # (2) path resolution that escapes the sandbox into the harness/oracle root.
    try:
        p = Path(value)
        base = p if p.is_absolute() else (source_root / p)
        resolved = base.resolve()
    except (ValueError, OSError):
        return ""
    if _is_relative_to(resolved, _HARNESS_ROOT) and not _is_relative_to(resolved, source_root):
        rel = _safe_rel(resolved, _HARNESS_ROOT)
        return f"resolves into the harness root ({rel})"
    return ""


# ---------------------------------------------------------------------------
# project()
# ---------------------------------------------------------------------------

def project(source_root: Path, dest: Path, keep_globs: list, keep_overrides=()) -> dict:
    """Copy only kept paths from source_root to dest, resolving symlinks.

    "Kept" means: matched by at least one keep_glob, AND not matched by any
    EXCLUDE_RULES pattern, AND not stripped by a path-rule (unless a
    keep_override re-admits it).

    Precedence (highest first):
      1. EXCLUDE_RULES (oracle by name)  -> never copied (cannot be overridden).
      2. path-rule (__pycache__/.pyc/.git transformed forms) -> stripped, UNLESS
         a keep_override glob matches (project-state .git of a git-fixture).
      3. keep_globs -> copied (real content; symlinks resolved).

    A keep_override re-admits a path-ruled file but does NOT bypass step 1 and
    does NOT bypass verify_manifest's content/decode checks: a kept .git that
    carries oracle content (verbatim or reversible-encoded) is still flagged.

    Symlink handling: symlinks are resolved via Path.resolve(); the real file
    content is copied to dest (never a symlink into the exclude-set).  A kept
    path whose resolved target is excluded content is caught by verify_manifest.

    Returns a manifest dict containing:
      projected_hashes      -- {rel_posix: sha256_hex} for every copied file.
      keep_set              -- [rel_posix, ...] paths that were kept.
      exclude_set           -- [rel_posix, ...] paths excluded by EXCLUDE_RULES.
      stripped_by_path_rule -- [rel_posix, ...] path-rule strips (not overridden).
      check_sources         -- [rel_posix, ...] paths matched by _CHECK_SOURCE_RULES.
      source_root           -- str(source_root) (for verify_manifest).
      projected_root        -- str(dest) (where the copied files live).
      exclude_rules         -- copy of EXCLUDE_RULES used.
      path_rules            -- copy of PATH_EXCLUDE_RULES used.
      keep_globs            -- copy of keep_globs used.
      keep_overrides        -- copy of keep_overrides used.
      excluded_paths_absent -- True: excluded files were not copied by path.
      content_absent        -- True placeholder; verify_manifest is authoritative.
    """
    keep_overrides = list(keep_overrides or [])
    dest.mkdir(parents=True, exist_ok=True)
    source_root = source_root.resolve()

    keep_set: list[str] = []
    exclude_set: list[str] = []
    check_sources: list[str] = []
    stripped_by_path_rule: list[str] = []
    projected_hashes: dict[str, str] = {}

    for dirpath_str, _dirnames, filenames in os.walk(source_root):
        dirpath = Path(dirpath_str)
        for filename in filenames:
            abs_path = dirpath / filename
            try:
                rel = _rel_posix(abs_path, source_root)
            except ValueError:
                continue  # outside source_root (should not happen in os.walk)

            # 1. Oracle exclude by name -- highest precedence, never overridable.
            if _matches_any(rel, EXCLUDE_RULES):
                exclude_set.append(rel)
                if _matches_any(rel, _CHECK_SOURCE_RULES):
                    check_sources.append(rel)
                continue

            # 2. Path-rule strip (transformed oracle forms) unless a keep_override
            #    re-admits this path as project-state.
            if _path_rule_excluded(rel) and not _matches_any(rel, keep_overrides):
                stripped_by_path_rule.append(rel)
                continue

            # 3. Keep iff a keep_glob matches.
            if _matches_any(rel, keep_globs):
                # Resolve symlinks: copy real content, never a link into the
                # exclude-set.  Content-hash/decode collision (if the resolved
                # target is excluded content) is caught by verify_manifest.
                real_path = abs_path.resolve()
                if not real_path.exists():
                    continue  # dangling symlink -- skip

                dest_path = dest / rel
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(real_path, dest_path)

                projected_hashes[rel] = _sha256_file(dest_path)
                keep_set.append(rel)

    return {
        "projected_hashes": projected_hashes,
        "keep_set": keep_set,
        "exclude_set": exclude_set,
        "stripped_by_path_rule": stripped_by_path_rule,
        "check_sources": check_sources,
        "source_root": str(source_root),
        "projected_root": str(dest),
        "exclude_rules": list(EXCLUDE_RULES),
        "path_rules": list(PATH_EXCLUDE_RULES),
        "keep_globs": list(keep_globs),
        "keep_overrides": list(keep_overrides),
        "excluded_paths_absent": True,
        "content_absent": True,  # placeholder; verify_manifest is authoritative
    }


# ---------------------------------------------------------------------------
# verify_manifest()
# ---------------------------------------------------------------------------

def verify_manifest(manifest: dict, source_root: Path) -> list[str]:
    """Return a list of problem strings (empty list == clean projection).

    Checks performed:
      (a) No excluded path is present in projected_hashes.
      (b) No projected file's content-hash matches any excluded file's hash
          (verbatim copy of excluded content under a kept path; symlink that
          resolved to excluded content).
      (c) keep_set x exclude_set == {} (disjointness meta-property).
      (d) check_sources <= exclude_set (check-coverage meta-property).
      (e) (Phase 3.5c) No DECODE-NORMALIZED form of any projected file matches an
          excluded file's hash -- catches reversible-encoded copies (base64,
          base32, hex, url, gzip, zlib, nested) of excluded content under a kept
          path, including a kept .git object carrying oracle content.
      (f) (Phase 3.5c) The path-rules hold: every source file matching a path-rule
          and NOT re-admitted by a keep_override is absent from projected_hashes.
    """
    problems: list[str] = []

    projected_hashes: dict[str, str] = manifest.get("projected_hashes", {})
    keep_set: set = set(manifest.get("keep_set", []))
    exclude_set: set = set(manifest.get("exclude_set", []))
    check_sources: set = set(manifest.get("check_sources", []))
    keep_overrides = manifest.get("keep_overrides", [])
    projected_root = manifest.get("projected_root")
    source_root = source_root.resolve()

    # (a) No excluded path present in projected_hashes.
    for rel in exclude_set:
        if rel in projected_hashes:
            problems.append(f"excluded path present in projection: {rel}")

    # (b)+(e) Compute excluded files' content-hashes (re-read from source_root so
    # verify_manifest does not depend on excluded content being in the manifest).
    excluded_hash_to_path: dict[str, str] = {}
    for rel in exclude_set:
        exc_path = source_root / rel
        if exc_path.is_file():
            h = _sha256_file(exc_path)
            if h not in excluded_hash_to_path:
                excluded_hash_to_path[h] = rel

    # (b) Raw content-hash collision.
    for rel, h in projected_hashes.items():
        if h in excluded_hash_to_path:
            exc_rel = excluded_hash_to_path[h]
            problems.append(
                f"projected file '{rel}' has same content-hash as excluded "
                f"file '{exc_rel}' (content-hash collision)"
            )

    # (e) Decode-normalized content collision: decode each projected file through
    # the reversible codecs and re-test every form's hash against the exclude-set.
    # Read the actual projected bytes from projected_root (authoritative copy).
    if excluded_hash_to_path and projected_root:
        proot = Path(projected_root)
        for rel in projected_hashes:
            pfile = proot / rel
            if not pfile.is_file():
                continue
            try:
                raw = pfile.read_bytes()
            except OSError:
                continue
            for form in decode_normalize(raw):
                fh = hashlib.sha256(form).hexdigest()
                if fh == projected_hashes[rel]:
                    continue  # the raw form is handled by check (b)
                if fh in excluded_hash_to_path:
                    exc_rel = excluded_hash_to_path[fh]
                    problems.append(
                        f"projected file '{rel}' decode-normalizes to the content "
                        f"of excluded file '{exc_rel}' (reversible-encoded oracle copy)"
                    )
                    break

    # (c) keep_set x exclude_set == {} (disjointness meta-property).
    overlap = keep_set & exclude_set
    if overlap:
        problems.append(
            f"keep_set and exclude_set overlap (meta-property violation): "
            f"{sorted(overlap)}"
        )

    # (d) check_sources <= exclude_set (check-coverage meta-property).
    orphan_checks = check_sources - exclude_set
    if orphan_checks:
        problems.append(
            f"check_sources not fully covered by exclude_set "
            f"(meta-property violation): {sorted(orphan_checks)}"
        )

    # (f) Path-rules hold: re-walk source_root and assert every path-ruled file
    # that no keep_override re-admits is absent from the projection.
    for dirpath_str, _dirnames, filenames in os.walk(source_root):
        dirpath = Path(dirpath_str)
        for filename in filenames:
            abs_path = dirpath / filename
            try:
                rel = _rel_posix(abs_path, source_root)
            except ValueError:
                continue
            if _matches_any(rel, EXCLUDE_RULES):
                continue  # handled by (a)
            if _path_rule_excluded(rel) and not _matches_any(rel, keep_overrides):
                if rel in projected_hashes:
                    problems.append(
                        f"path-rule violation: transformed-form path present in "
                        f"projection (should be stripped): {rel}"
                    )

    return problems
