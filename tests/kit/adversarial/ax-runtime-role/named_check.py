"""ax-runtime-role: named check (class invariant) for hz-runtime-role-unannotated.

Public: run(tree: Path) -> bool
  True iff tree exhibits the escape class: runtime_role=author field set to a
  non-empty value with no paired valid attestation token.

Wraps real detection (runtime_roles + attest). Returns bool, never raises.

CLASS PREDICATE ANCHOR: _author_field_unattested(field_spec, tokens)
  The class-discriminating clause. Catches the primary escape: no matching
  token for an author field with a non-empty value.

Other clause: _author_field_token_forged(field_spec, value, tokens, registry)
  Catches forgery variants (malformed, value-changed, unregistered-key, etc.).
  Structurally separate so Task 6 predicate-weakening is AST-localizable.

ASCII-only. Stdlib + runtime_roles + attest.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

_KIT_ROOT = str(Path(__file__).resolve().parents[4])
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

import runtime_roles
import attest


def _author_field_unattested(field_spec: dict, tokens: list) -> bool:
    """CLASS PREDICATE ANCHOR.

    True iff the author field has NO matching attestation token.
    This is the class-discriminating clause for 'runtime_role=author field set
    without paired valid attestation'. The canonical escape path: the agent fills
    the author field but creates no attestation record. The absence of any token
    matching (artifact, field) means the fill is unattested -- a class member.
    """
    artifact = field_spec["artifact"]
    field = field_spec["field"]
    matching = [
        t for t in tokens
        if t.get("artifact") == artifact and t.get("field") == field
    ]
    return len(matching) == 0


def _author_field_token_forged(
    field_spec: dict, value: str, tokens: list, registry: dict
) -> bool:
    """Other clause: True iff a token exists but fails verification.

    Covers: malformed-token, replayed-token, unregistered-or-revoked-key,
    value-changed-since-attestation, forged-hmac, tree_state-not-ancestor.
    Called only when _author_field_unattested() is False.
    Secrets are unavailable in this context; hmac-unverified-secret-absent
    is advisory (not an error). Ancestry is not checked (no git context).
    """
    artifact = field_spec["artifact"]
    field = field_spec["field"]
    matching = [
        t for t in tokens
        if t.get("artifact") == artifact and t.get("field") == field
    ]
    if not matching:
        return False
    tok = matching[-1]
    errs, _adv = attest.verify_token(
        tok, artifact, field, value, registry,
        None,            # no secret: HMAC is advisory only
        lambda ts: True, # ancestry not checked in named_check context
    )
    return bool(errs)


def run(tree: Path) -> bool:
    """True iff tree exhibits the escape class."""
    tree = Path(tree)
    fields = runtime_roles.load_sidecar(tree)

    tokens: list = []
    lp = tree / "goals" / ".attest-log.json"
    if lp.exists():
        log = json.loads(lp.read_text(encoding="utf-8"))
        tokens = log.get("tokens", [])

    registry: dict = {}
    rp = tree / "goals" / ".attest-keys.json"
    if rp.exists():
        registry = json.loads(rp.read_text(encoding="utf-8"))

    for f in fields:
        if f.get("role") != "author":
            continue
        try:
            value = runtime_roles.extract_value(tree, f["artifact"], f["locator"])
        except ValueError:
            return True  # locator error: treat as caught
        if not value:
            continue
        if _author_field_unattested(f, tokens):
            return True
        if _author_field_token_forged(f, value, tokens, registry):
            return True
    return False
