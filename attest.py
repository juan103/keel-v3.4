"""KEEL v3.4 Phase 2a: HMAC-SHA256 author-fill attestation core (stdlib only).
Token binds (artifact, field, value_sha256, actor, timestamp, tree_state) under a
length-prefixed canonical payload (v_final §2). verify_token returns (errors,
advisories) in the normative short-circuit order (v_final §3 Commitment 6)."""
from __future__ import annotations
import hashlib
import hmac

_FIELDS = ("artifact", "field", "value_sha256", "actor", "timestamp", "tree_state")


def value_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_payload(artifact, field, value_sha256_, actor, timestamp, tree_state) -> str:
    comps = [artifact, field, value_sha256_, actor, timestamp, tree_state]
    for c in comps:
        if "\n" in c or "\r" in c:
            raise ValueError("malformed-token: newline/CR in component")
    return "\n".join(f"{len(c.encode('utf-8'))}:{c}" for c in comps)


def _hmac(secret: str, payload: str) -> str:
    return hmac.new(bytes.fromhex(secret), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def make_token(secret, artifact, field, value, actor, timestamp, tree_state) -> dict:
    vsha = value_sha256(value)
    payload = canonical_payload(artifact, field, vsha, actor, timestamp, tree_state)
    return {"artifact": artifact, "field": field, "value_sha256": vsha,
            "actor": actor, "timestamp": timestamp, "tree_state": tree_state,
            "hmac": _hmac(secret, payload)}


def _key_status(registry, actor):
    for k in registry.get("keys", []):
        if k.get("key_id") == actor:
            return k.get("status")
    return None


def verify_token(token, expected_artifact, expected_field, current_value,
                 registry, secret_or_none, is_ancestor):
    errors, advisories = [], []
    # 1. presence / well-formedness
    if not all(f in token for f in _FIELDS) or "hmac" not in token:
        return ["malformed-token"], advisories
    try:
        payload = canonical_payload(
            token["artifact"], token["field"], token["value_sha256"],
            token["actor"], token["timestamp"], token["tree_state"])
    except ValueError:
        return ["malformed-token"], advisories
    # 2. replay: embedded (artifact, field) must equal expected
    if token["artifact"] != expected_artifact or token["field"] != expected_field:
        return ["replayed-token"], advisories
    # 3. key state
    if _key_status(registry, token["actor"]) != "registered":
        return ["unregistered-or-revoked-key"], advisories
    # 4. value binding
    if token["value_sha256"] != value_sha256(current_value):
        return ["value-changed-since-attestation"], advisories
    # 5. HMAC (advisory if secret absent)
    if secret_or_none is None:
        advisories.append("hmac-unverified-secret-absent")
    else:
        if not hmac.compare_digest(token["hmac"], _hmac(secret_or_none, payload)):
            return ["forged-hmac"], advisories
    # 6. provenance: ancestry
    if not is_ancestor(token["tree_state"]):
        return ["tree_state-not-ancestor-of-HEAD"], advisories
    return errors, advisories


# ---------------------------------------------------------------------------
# Phase 2a CLI + IO (register / sign / revoke)
# ---------------------------------------------------------------------------
import json
import secrets as _secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import runtime_roles


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _dump(p: Path, data):
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def register(repo_root, key_id) -> None:
    root = Path(repo_root)
    secret = _secrets.token_hex(32)
    sp = root / "goals" / ".attest-secrets.json"
    store = _load(sp, {})
    store[key_id] = secret
    _dump(sp, store)
    rp = root / "goals" / ".attest-keys.json"
    reg = _load(rp, {"version": 1, "keys": [], "events": []})
    reg["keys"] = [k for k in reg["keys"] if k["key_id"] != key_id]
    reg["keys"].append({"key_id": key_id, "status": "registered",
                        "secret_sha256": hashlib.sha256(secret.encode()).hexdigest(),
                        "registered_at": _now_iso()})
    reg["events"].append({"event": "register", "key_id": key_id, "at": _now_iso()})
    _dump(rp, reg)


def revoke(repo_root, key_id) -> None:
    root = Path(repo_root)
    rp = root / "goals" / ".attest-keys.json"
    reg = _load(rp, {"version": 1, "keys": [], "events": []})
    for k in reg["keys"]:
        if k["key_id"] == key_id:
            k["status"] = "revoked"
            k["revoked_at"] = _now_iso()
    reg["events"].append({"event": "revoke", "key_id": key_id, "at": _now_iso()})
    _dump(rp, reg)


def _git_head(repo_root) -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_root),
                       capture_output=True, text=True)
    return r.stdout.strip()


def _is_ancestor(repo_root, commit) -> bool:
    r = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                       cwd=str(repo_root), capture_output=True, text=True)
    return r.returncode == 0


def sign(repo_root, artifact, field, actor=None) -> None:
    root = Path(repo_root)
    fields = runtime_roles.load_sidecar(root)
    spec = next((f for f in fields if f["artifact"] == artifact and f["field"] == field), None)
    if spec is None:
        raise ValueError(f"no sidecar entry for {artifact}::{field}")
    value = runtime_roles.extract_value(root, artifact, spec["locator"])
    store = _load(root / "goals" / ".attest-secrets.json", {})
    if actor is None:
        actor = next(iter(store))  # single-owner convenience
    secret = store[actor]
    token = make_token(secret, artifact, field, value, actor, _now_iso(), _git_head(root))
    lp = root / "goals" / ".attest-log.json"
    log = _load(lp, {"version": 1, "tokens": []})
    log["tokens"].append(token)
    _dump(lp, log)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    root = Path(".")
    if argv and argv[0] == "register":
        register(root, argv[1])
    elif argv and argv[0] == "revoke":
        revoke(root, argv[1])
    elif argv and argv[0] == "sign":
        sign(root, argv[1], argv[2])
    else:
        print("usage: attest.py register <key_id> | sign <artifact> <field> | revoke <key_id>")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
