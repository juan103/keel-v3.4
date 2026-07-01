"""KEEL v3.4: per-check revalidation freshness (closes hz-green-rotting).
A check's last_run is valid only when it passed against the current tree
(recorded git HEAD matches) AND within its interval (wall-clock backstop)."""
from __future__ import annotations
import json
import re
import time
from pathlib import Path

_CACHE_REL = ".checks-cache.json"
_ROW = re.compile(r"^\|\s*(\w+)\s*\|\s*(\d+)\s*\|\s*(true|false)\s*\|\s*$")
_MAX_RC = 7
_MAX_OTHER = 90


def _cache_path(repo_root: Path) -> Path:
    return repo_root / _CACHE_REL


def read_cache(repo_root: Path) -> dict:
    try:
        data = json.loads(_cache_path(repo_root).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def record_pass(repo_root: Path, check_name: str, head: str, now: float | None = None) -> None:
    cache = read_cache(repo_root)
    cache[check_name] = {"timestamp": time.time() if now is None else now, "head": head}
    try:
        _cache_path(repo_root).write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def invalidate(repo_root: Path, check_name: str) -> None:
    """Remove check_name from the cache (best-effort). No-op if absent or on OSError."""
    cache = read_cache(repo_root)
    if check_name not in cache:
        return
    cache.pop(check_name)
    try:
        _cache_path(repo_root).write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def parse_freshness_config(repo_root: Path) -> dict:
    path = repo_root / "goals" / "freshness-config.md"
    text = path.read_text(encoding="utf-8")  # fail-closed: FileNotFoundError if absent
    out: dict[str, int] = {}
    for line in text.splitlines():
        m = _ROW.match(line.strip())
        if not m:
            continue
        name, interval, rc = m.group(1), int(m.group(2)), m.group(3) == "true"
        cap = _MAX_RC if rc else _MAX_OTHER
        if interval < 1 or interval > cap:
            raise ValueError(
                f"freshness-config: {name} interval {interval} out of bounds "
                f"(refusal_critical={rc}, max {cap})")
        out[name] = interval
    if not out:
        raise ValueError("freshness-config: no check entries parsed")
    return out


def check_falsifier_freshness_impl(repo_root: Path, strict: bool, now: float, head: str) -> list[str]:
    cfg = parse_freshness_config(repo_root)  # raises ValueError on bad config (fail-closed)
    cache = read_cache(repo_root)
    violations: list[str] = []
    for name, interval in sorted(cfg.items()):
        rec = cache.get(name)
        if not rec:
            violations.append(f"{name}: no recorded pass in {_CACHE_REL}")
            continue
        if rec.get("head") != head:
            violations.append(f"{name}: tree changed since last recorded pass (re-run preflight)")
            continue
        age_days = (now - float(rec.get("timestamp", 0))) / 86400.0
        if age_days > interval:
            violations.append(f"{name}: last pass {age_days:.1f}d ago exceeds interval of {interval}d")
    return violations
