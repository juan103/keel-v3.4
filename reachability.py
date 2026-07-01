"""
Typed reachability probes (v3.SPINE.B).

Spec: ../proposal_v3.md "v3.SPINE.B — Reachability checks at Gate 0 for every
                         external dependency"
ADR: v3-build/decisions/0008-probe-execution-policy.md

Probe types (initial v3 vocabulary):
  https_tls    HEAD/GET over HTTPS; checks status threshold AND cert subject/SAN substring.
  http_status  Plain HTTP status check.
  dns          Hostname resolution; optional sinkhole CIDR exclusion.
  script       Bounded escape hatch — Python script in scripts/probes/.

Inline shell strings are forbidden. Probes are stdlib-only (urllib, ssl, socket,
ipaddress, subprocess, re, pathlib).

Network I/O is split out via _http_fetch / _https_fetch_with_cert / _dns_resolve
so tests can monkeypatch without spinning up live servers. Production code uses
the real implementations.
"""

from __future__ import annotations

import ipaddress
import os
import re
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROBES_DIR_NAME = "scripts/probes"


# Required fields per probe type (R-5.1). Optional fields are not listed:
# Auth env, Block list (dns), URL (for script — though typically present).
REQUIRED_FIELDS_BY_TYPE: dict[str, set[str]] = {
    "https_tls":   {"URL", "Pass condition", "Used by"},
    "http_status": {"URL", "Pass condition", "Used by"},
    "dns":         {"Hostname", "Pass condition", "Used by"},
    "script":      {"Script probe", "Reason", "Path", "Used by"},
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_PROBE_HEADER_RE = re.compile(r"^### (.+)$", re.MULTILINE)
_FIELD_RE = re.compile(r"^\*\*([^*]+):\*\*\s*(.*)$", re.MULTILINE)


def validate_probe(probe: dict) -> list[str]:
    """Return list of error messages; empty list == valid.

    Per R-5.1: missing-required-field errors are surfaced; unknown extra fields
    are accepted (forward-compat).
    """
    errors: list[str] = []
    name = probe.get("name", "?")
    type_ = probe.get("Type", "").strip().lower()
    if not type_:
        errors.append(f"probe {name!r}: missing required field 'Type'")
        return errors
    if type_ not in REQUIRED_FIELDS_BY_TYPE:
        errors.append(
            f"probe {name!r}: unknown Type {type_!r} "
            f"(known: {sorted(REQUIRED_FIELDS_BY_TYPE)})"
        )
        return errors
    for field in REQUIRED_FIELDS_BY_TYPE[type_]:
        if not probe.get(field, "").strip():
            errors.append(
                f"probe {name!r}: missing required field {field!r} "
                f"for Type={type_!r}"
            )
    return errors


def parse_reachability(repo_root: Path) -> list[dict]:
    """Parse goals/reachability.md into a list of probe dicts.

    Each probe has at least 'name' (from `### <name>`) plus any `**Field:** value`
    pairs. Unknown fields preserved (forward-compat).

    Raises ValueError on missing required fields per the declared probe type
    (R-5.1).
    """
    path = repo_root / "goals" / "reachability.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")

    matches = list(_PROBE_HEADER_RE.finditer(text))
    probes: list[dict] = []
    all_errors: list[str] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        probe: dict = {"name": match.group(1).strip()}
        for fm in _FIELD_RE.finditer(body):
            key = fm.group(1).strip()
            value = fm.group(2).strip()
            probe[key] = value
        errors = validate_probe(probe)
        if errors:
            all_errors.extend(errors)
        else:
            probes.append(probe)
    if all_errors:
        raise ValueError("invalid reachability.md:\n  " + "\n  ".join(all_errors))
    return probes


# ---------------------------------------------------------------------------
# Pass-condition parsing (small ad-hoc DSL)
# ---------------------------------------------------------------------------

_STATUS_RE = re.compile(r"status\s*<\s*(\d+)", re.IGNORECASE)
_CERT_SUBSTR_RE = re.compile(
    r'cert\s+subject_or_san\s+contains\s+"([^"]+)"', re.IGNORECASE
)


def _parse_status_threshold(condition: str, default: int = 500) -> int:
    m = _STATUS_RE.search(condition)
    return int(m.group(1)) if m else default


def _parse_cert_substring(condition: str) -> str | None:
    m = _CERT_SUBSTR_RE.search(condition)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Auth / credential helpers
# ---------------------------------------------------------------------------


def _build_auth_headers(probe: dict) -> tuple[dict, str | None]:
    """Return (headers, error_or_none).

    If `Auth env` is set and the env var is unset, returns ({}, error_message).
    Credential value is never echoed back via error_message.
    """
    auth_env = probe.get("Auth env", "").strip()
    if not auth_env:
        return ({}, None)
    value = os.environ.get(auth_env)
    if not value:
        return ({}, f"required env var {auth_env!r} is not set")
    return ({"Authorization": f"Bearer {value}"}, None)


# ---------------------------------------------------------------------------
# Network seams (mockable)
# ---------------------------------------------------------------------------


# Module-level seam for unit-testing _http_fetch's HEAD/GET fallback logic
# without monkeypatching urllib.request globally.
_urlopen = urllib.request.urlopen

# HTTP status codes for which HEAD is treated as "method not supported" and
# the request should be retried as GET. 405 Method Not Allowed and 501 Not
# Implemented are the standard signals; other 4xx/5xx codes are real status
# results and pass through unchanged.
_HEAD_FALLBACK_CODES = frozenset({405, 501})


def _http_fetch(url: str, headers: dict | None = None, timeout: int = 10) -> int:
    """Issue a HEAD; fall back to GET if the server returns 405/501.

    Other HTTP error codes (e.g., 500, 503) are returned as the status — they
    are real status results, not method-refusal signals.
    """
    headers = headers or {}
    head_req = urllib.request.Request(url, headers=headers, method="HEAD")
    try:
        with _urlopen(head_req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        if e.code not in _HEAD_FALLBACK_CODES:
            return e.code
        # Method-refusal — retry as GET.
        get_req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with _urlopen(get_req, timeout=timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as e2:
            return e2.code


def _https_fetch_with_cert(
    url: str, headers: dict | None = None, timeout: int = 10
) -> tuple[int, str]:
    """Open HTTPS, inspect cert, return (status, joined_subject_or_san_string).

    The joined string is the lowercased commonName plus all SAN DNS entries,
    comma-separated.
    """
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or 443

    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()

    parts: list[str] = []
    for tuple_list in cert.get("subject", ()):
        for k, v in tuple_list:
            if k == "commonName":
                parts.append(v)
    for typ, name in cert.get("subjectAltName", ()):
        parts.append(name)
    subject_or_san = ", ".join(parts).lower()

    status = _http_fetch(url, headers=headers, timeout=timeout)
    return (status, subject_or_san)


def _dns_resolve(host: str) -> list[str]:
    """Resolve a hostname; return list of address strings. Raises on failure."""
    infos = socket.getaddrinfo(host, None)
    return [info[4][0] for info in infos]


# ---------------------------------------------------------------------------
# Probe handlers
# ---------------------------------------------------------------------------


def _result(passed: bool, details: str, error: str | None = None) -> dict:
    return {"pass": passed, "details": details, "error": error}


def probe_http_status(probe: dict) -> dict:
    url = probe.get("URL", "").strip()
    if not url:
        return _result(False, "missing URL field")

    headers, auth_error = _build_auth_headers(probe)
    if auth_error:
        return _result(False, auth_error)

    threshold = _parse_status_threshold(probe.get("Pass condition", ""))
    try:
        status = _http_fetch(url, headers=headers)
    except Exception as e:
        # Redact any auth value from error (paranoid).
        msg = str(e)
        for v in os.environ.values():
            if v and len(v) > 6 and v in msg:
                msg = msg.replace(v, "[REDACTED]")
        return _result(False, f"connection error: {msg}", error=type(e).__name__)

    if status >= threshold:
        return _result(False, f"status {status} >= threshold {threshold}")
    return _result(True, f"status {status} < {threshold}")


def probe_https_tls(probe: dict) -> dict:
    url = probe.get("URL", "").strip()
    if not url:
        return _result(False, "missing URL field")

    headers, auth_error = _build_auth_headers(probe)
    if auth_error:
        return _result(False, auth_error)

    threshold = _parse_status_threshold(probe.get("Pass condition", ""))
    cert_substr = _parse_cert_substring(probe.get("Pass condition", ""))

    try:
        status, subject_or_san = _https_fetch_with_cert(url, headers=headers)
    except Exception as e:
        msg = str(e)
        for v in os.environ.values():
            if v and len(v) > 6 and v in msg:
                msg = msg.replace(v, "[REDACTED]")
        return _result(False, f"TLS/HTTP error: {msg}", error=type(e).__name__)

    if status >= threshold:
        return _result(False, f"status {status} >= threshold {threshold}")
    if cert_substr and cert_substr.lower() not in subject_or_san:
        return _result(
            False,
            f"cert subject_or_san {subject_or_san!r} does not contain "
            f"required substring {cert_substr!r}",
        )
    return _result(True, f"status {status} < {threshold}; cert subject OK")


def probe_dns(probe: dict) -> dict:
    host = probe.get("Hostname", "").strip()
    if not host:
        return _result(False, "missing Hostname field")

    try:
        addrs = _dns_resolve(host)
    except Exception as e:
        return _result(False, f"DNS resolution failed for {host!r}: {e}",
                       error=type(e).__name__)
    if not addrs:
        return _result(False, f"DNS returned no addresses for {host!r}")

    # Optional CIDR exclusion ('Block list': "10.0.0.0/8, 192.168.0.0/16")
    block_list = probe.get("Block list", "").strip()
    if block_list:
        nets = []
        for cidr in [c.strip() for c in block_list.split(",") if c.strip()]:
            try:
                nets.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                continue
        for addr_str in addrs:
            try:
                addr = ipaddress.ip_address(addr_str)
            except ValueError:
                continue
            for net in nets:
                if addr in net:
                    return _result(
                        False,
                        f"DNS resolved to blocked range: {addr_str} in {net}",
                    )
    return _result(True, f"resolved {host!r} to {addrs}")


def probe_script(repo_root: Path, probe: dict) -> dict:
    """Bounded script escape hatch. Five rules per ADR-0008:

    1. **Script probe:** true must be present (case-insensitive on value).
    2. **Reason:** must be non-empty.
    3. Path must resolve under scripts/probes/ (no `..`, no absolute paths).
    4. Script must be tracked by git: `git ls-files --error-unmatch <path>` exits 0.
    5. Invocation: `$PYTHON_CMD <path>` (no shell). Env limited to PROBE_URL +
       optional Auth env.
    """
    # Rule 1: explicit declaration.
    if probe.get("Script probe", "").strip().lower() != "true":
        return _result(
            False,
            "script probe missing **Script probe:** true declaration "
            "(boundary rule 1)",
        )

    # Rule 2: reason.
    if not probe.get("Reason", "").strip():
        return _result(False, "script probe missing **Reason:** (boundary rule 2)")

    # Rule 3: path under scripts/probes/.
    path_str = probe.get("Path", "").strip()
    if not path_str:
        return _result(False, "script probe missing **Path:** field")
    if path_str.startswith(("/", "\\")) or ".." in Path(path_str).parts:
        return _result(
            False,
            f"script path {path_str!r} must resolve under {PROBES_DIR_NAME}/ "
            "(no absolute paths, no .. escapes)",
        )
    abs_path = (repo_root / path_str).resolve()
    probes_root = (repo_root / PROBES_DIR_NAME).resolve()
    try:
        abs_path.relative_to(probes_root)
    except ValueError:
        return _result(
            False,
            f"script path {path_str!r} is outside {PROBES_DIR_NAME}/ (boundary rule 3)",
        )

    # Rule 4: tracked by git.
    try:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", path_str],
            cwd=repo_root, check=True, capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return _result(
            False,
            f"script {path_str!r} is not tracked by git "
            "(commit it, or use `git add` -- boundary rule 4)",
        )

    # Rule 5: invocation. Limited env: PATH, PYTHONIOENCODING, PROBE_URL, optional
    # auth. v3.1 additions:
    #   (a) On Windows, pass through a minimal essentials floor so npm-installed
    #       .CMD shims (which bootstrap Node.js / cmd.exe) can resolve their
    #       runtime. The current strip-to-PATH was too aggressive for any probe
    #       that targets a CLI tool reachable via a standard package-manager
    #       shim, which is the dominant reachability case. The variables passed
    #       through (USERPROFILE, APPDATA, LOCALAPPDATA, TEMP, TMP, COMSPEC,
    #       PATHEXT, SystemRoot) do not typically carry project secrets;
    #       project secrets belong in env vars named in **Auth env:**.
    #   (b) Per-probe **Env passthrough:** field lets a probe explicitly name
    #       additional environment-variable names to pass through (comma-
    #       separated). This is an explicit opt-in: the probe author writes
    #       what their probe needs, the kit reads it from os.environ.
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
    if sys.platform == "win32":
        for var in (
            "USERPROFILE", "APPDATA", "LOCALAPPDATA",
            "TEMP", "TMP", "COMSPEC", "PATHEXT", "SystemRoot",
        ):
            val = os.environ.get(var)
            if val:
                env[var] = val
    extra_passthrough = probe.get("Env passthrough", "").strip()
    if extra_passthrough:
        for name in [n.strip() for n in extra_passthrough.split(",") if n.strip()]:
            val = os.environ.get(name)
            if val:
                env[name] = val
    if "URL" in probe:
        env["PROBE_URL"] = probe["URL"]
    auth_env = probe.get("Auth env", "").strip()
    if auth_env:
        value = os.environ.get(auth_env)
        if not value:
            return _result(False, f"required env var {auth_env!r} is not set")
        env[auth_env] = value

    try:
        # v3.1: explicit encoding="utf-8", errors="replace" on text=True. Without
        # this, Python on Windows picks up locale.getpreferredencoding() (cp1252),
        # which crashes the moment a non-ASCII char hits the subprocess pipe.
        proc = subprocess.run(
            [sys.executable, str(abs_path)],
            cwd=repo_root, env=env, capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return _result(False, f"script {path_str!r} timed out after 30s")
    except Exception as e:
        return _result(False, f"script invocation error: {e}", error=type(e).__name__)

    if proc.returncode != 0:
        # Don't echo stdout/stderr by default (might leak credentials); summary only.
        return _result(False, f"script {path_str!r} exited {proc.returncode}")
    return _result(True, f"script {path_str!r} exited 0")


# ---------------------------------------------------------------------------
# Dispatch + integration
# ---------------------------------------------------------------------------


_DISPATCH = {
    "https_tls": probe_https_tls,
    "http_status": probe_http_status,
    "dns": probe_dns,
}


def run_probe(repo_root: Path, probe: dict) -> dict:
    type_ = probe.get("Type", "").strip().lower()
    if type_ == "script":
        return probe_script(repo_root, probe)
    handler = _DISPATCH.get(type_)
    if handler is None:
        return _result(False, f"unknown probe type {type_!r}; "
                              f"known: {sorted(_DISPATCH) + ['script']}")
    return handler(probe)


def check_reachability_probes_pass(repo_root: Path) -> list[str]:
    """Run every probe in goals/reachability.md. Return list of error messages.
    Empty list == OK or no probes declared (skipped silently).

    Surfaces parser errors (missing required fields, unknown Type) as the
    error list rather than letting ValueError propagate to preflight.
    """
    try:
        probes = parse_reachability(repo_root)
    except ValueError as e:
        return [str(e)]
    if not probes:
        return []
    errors: list[str] = []
    for probe in probes:
        result = run_probe(repo_root, probe)
        if not result["pass"]:
            errors.append(
                f"probe {probe.get('name', '?')!r}: {result['details']}"
            )
    return errors


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    errs = check_reachability_probes_pass(root)
    if errs:
        for e in errs:
            print(f"[FAIL] {e}")
        sys.exit(1)
    print("[OK] reachability probes pass")
