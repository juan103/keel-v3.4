"""lexical_scan.py -- Lexical oracle-leak scan over projected fixture content.

Phase 3.5c necessary-not-sufficient check: scans a projected fixture's file
contents, filenames, code comments, identifier names, and package metadata
against a scenario's locked escape-keyword set (keyword_set.json).  A clean
scan (empty result list) is NECESSARY but NOT SUFFICIENT for oracle-blindness.

HONEST SCOPE (necessary-not-sufficient):
  A clean scan does NOT prove oracle-blindness.  The keyword set is spec-derived
  and finite; escape information can survive a clean scan through:
    - semantic paraphrase: oracle meaning present but no keyword verbatim.
    - unlisted tokens: a finite keyword set is not a complete vocabulary.
    - installed-module reachability: oracle content reachable via imports not
      visible as text in the projected fixture files.
    - binary / non-text encodings: scan skips binary files gracefully; a
      keyword embedded in an opaque binary blob is not detected.
    - SELF-HOSTED VOCABULARY OVERLAP (3.5c finding): because the kit exercises
      ITS OWN hazards, a scenario's escape-concept vocabulary OVERLAPS the
      fixture's legitimate project vocabulary -- e.g. "commitment" / "contributor"
      / "settings.json" / "first-outcome" are both escape-concept words AND words
      that MUST appear in the clean fixture the agent operates on.  So a fully
      CLEAN lexical scan is NOT achievable for a self-hosted fixture, and the
      eligible scenarios' projected fixtures DO contain their own keyword tokens.
      The meaningful signal this scan provides is therefore the detection of an
      OUT-OF-BASELINE oracle-intent leak (test_injected_keyword_flagged), not a
      clean-scan guarantee.  Partitioning keyword sets into "escape-intent-only"
      vs "fixture-necessary" tokens is a Phase-4 follow-up -- and is itself bounded
      by this overlap (some tokens are irreducibly both).
  These are NAMED RESIDUES, not claimed closed by this module.

Scope:
  - load_keyword_set(scenario_dir: Path) -> list[str].
  - scan(projected_root: Path, keywords: list[str]) -> list[str]
      (empty list == clean; non-empty == found keyword hits to investigate).

What is scanned per file:
  - The file's RELATIVE PATH (all path components, including directory names).
  - The file's TEXT CONTENT (utf-8, then latin-1 fallback; binary files skipped
    gracefully).  For .py, .md, and .json files this textual scan inherently
    covers comments, identifiers, string literals, and key/value metadata.
  All comparisons are case-insensitive.

ASCII-only strings throughout.  Stdlib only: json, pathlib, re.
"""

import json
import re
from pathlib import Path


def load_keyword_set(scenario_dir: Path) -> list:
    """Load the locked escape-keyword list from keyword_set.json in scenario_dir.

    The JSON schema is: {"keywords": [...], "note": "..."}.  Returns a list of
    keyword strings (the list is ordered as in the file; values are returned
    as-is without lowercasing -- case-insensitive comparison is done at scan
    time by scan()).

    Raises FileNotFoundError / json.JSONDecodeError if the file is absent or
    malformed (the keyword_set.json files are committed fixtures -- a missing
    or malformed file is a harness authoring error, not a runtime condition).
    """
    path = Path(scenario_dir) / "keyword_set.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data["keywords"])


def scan(projected_root: Path, keywords: list) -> list:
    """Scan projected_root for any of the given keywords; return problem strings.

    Necessary-not-sufficient: see module docstring.  An empty result does NOT
    prove oracle-blindness.

    For each file under projected_root (recursively):
      1. The FILE'S RELATIVE PATH (all path components joined as a POSIX string)
         is searched case-insensitively for each keyword.  This catches keyword
         disclosure in directory or file names (e.g. a filename like
         '.attest-keys.json' would hit on keyword 'attest').
      2. The FILE'S TEXT CONTENT is read (utf-8; latin-1 fallback) and searched
         case-insensitively.  For .py / .md / .json files this covers code
         comments, identifier names, string literals, and JSON keys/values.
         Binary files that cannot be decoded are skipped gracefully.

    A hit is reported as a problem string naming the file's relative POSIX path
    and the matched keyword (lowercased in the report for readability).  At most
    ONE problem is reported per (file, scan-phase) pair -- the first match found.

    Returns:
      [] if no keywords were found anywhere in the projected tree (clean scan).
      A non-empty list of problem strings if any keyword was found.

    Raises:
      TypeError if projected_root is not Path-like.
      OSError if projected_root does not exist or cannot be traversed.
    """
    projected_root = Path(projected_root)
    if not keywords:
        return []

    # Compile a single case-insensitive pattern for fast multi-keyword search.
    # re.escape ensures keywords with special regex characters (e.g. "failed->passed",
    # "green without red") are matched as literals, not as regex operators.
    pattern = re.compile(
        "|".join(re.escape(kw) for kw in keywords),
        re.IGNORECASE,
    )

    problems: list = []

    for path in sorted(projected_root.rglob("*")):
        if not path.is_file():
            continue

        # Compute the repo-relative POSIX path for problem messages.
        try:
            rel = path.relative_to(projected_root).as_posix()
        except ValueError:
            rel = str(path)

        # 1. Check the FULL RELATIVE PATH (all components) for keyword hits.
        #    e.g. ".git/COMMIT_EDITMSG" is checked as the string ".git/COMMIT_EDITMSG".
        m = pattern.search(rel)
        if m:
            problems.append(
                "filename '{}' contains keyword '{}'".format(rel, m.group(0).lower())
            )

        # 2. Check the FILE'S TEXT CONTENT (utf-8, then latin-1 fallback).
        #    Binary files that fail both decodings are skipped gracefully.
        text = _read_text(path)
        if text is None:
            continue  # binary or unreadable -- skip gracefully

        m = pattern.search(text)
        if m:
            problems.append(
                "file '{}' content contains keyword '{}'".format(rel, m.group(0).lower())
            )

    return problems


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _read_text(path: Path):
    """Try to read path as text (utf-8, then latin-1); return None if binary."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        pass
    try:
        return path.read_text(encoding="latin-1")
    except (UnicodeDecodeError, OSError):
        pass
    return None
