"""KEEL v3.4 Phase 2a: runtime_role sidecar + author-field value extraction.
Pinned, deterministic locators so a green machine and an external reviewer
compute identical value hashes (v_final §2)."""
from __future__ import annotations
import json
import re
import unicodedata
from pathlib import Path


def load_sidecar(repo_root: Path) -> list[dict]:
    p = Path(repo_root) / "goals" / ".runtime-roles.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("fields", []))


def _norm_lines(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.split("\n")


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^(```|~~~)")


def normalize_section(text: str, heading: str) -> str:
    """heading is e.g. '## Falsifier'. Returns the normalized body."""
    m = _HEADING_RE.match(heading)
    if not m:
        raise ValueError(f"malformed section locator heading: {heading!r}")
    want_level = len(m.group(1))
    want_title = unicodedata.normalize("NFC", m.group(2)).strip()
    lines = _norm_lines(text)
    # find matching heading lines (fence-aware)
    in_fence = False
    matches = []
    for i, ln in enumerate(lines):
        if _FENCE_RE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        hm = _HEADING_RE.match(ln)
        if hm and len(hm.group(1)) == want_level and \
                unicodedata.normalize("NFC", hm.group(2)).strip() == want_title:
            matches.append(i)
    if not matches:
        raise ValueError(f"section not found: {heading!r}")
    if len(matches) > 1:
        raise ValueError(f"ambiguous-locator: duplicate heading {heading!r}")
    start = matches[0] + 1
    # body to next heading of same-or-higher level (fence-aware)
    in_fence = False
    end = len(lines)
    for j in range(start, len(lines)):
        ln = lines[j]
        if _FENCE_RE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        hm = _HEADING_RE.match(ln)
        if hm and len(hm.group(1)) <= want_level:
            end = j
            break
    body = [ln.rstrip() for ln in lines[start:end]]
    # strip leading/trailing blank lines
    while body and body[0] == "":
        body.pop(0)
    while body and body[-1] == "":
        body.pop()
    return "\n".join(body)


def extract_value(repo_root: Path, artifact: str, locator: str) -> str:
    art = Path(repo_root) / artifact
    if not art.exists():
        raise ValueError(f"artifact not found: {artifact}")
    if locator.startswith("section:"):
        return normalize_section(art.read_text(encoding="utf-8"), locator[len("section:"):])
    if locator.startswith("json:"):
        data = json.loads(art.read_text(encoding="utf-8"))
        cur = data
        for key in locator[len("json:"):].split("."):
            if not isinstance(cur, dict) or key not in cur:
                raise ValueError(f"json locator path not found: {locator}")
            cur = cur[key]
        return cur if isinstance(cur, str) else json.dumps(cur, sort_keys=True)
    raise ValueError(f"unknown locator scheme: {locator}")
