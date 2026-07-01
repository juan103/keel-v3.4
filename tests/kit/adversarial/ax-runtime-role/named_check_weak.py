"""ax-runtime-role: SURGICALLY WEAKENED twin of named_check.py (F1 Control 1).

This module is a verbatim copy of named_check.py EXCEPT for the body of the
class-predicate anchor _author_field_unattested, which is neutralized to
`return False`.  Every other top-level function (_author_field_token_forged,
run) is byte-identical, so the AST diff between named_check.py and this file is
confined to the single anchor function (weakenings.ast_changed_functions proves
this executably for F1 Control 1 leg (a)).

Effect: the 'no matching token' (unattested-author-fill) CLASS is no longer
caught, but the forgery clause _author_field_token_forged still fires, so
forgery variants and the forgery-caught retained witness remain caught.  This is
the surgical weakening that makes the F1 cell (escape, weakened) -> caught=False.

This file is NOT a real check.  It exists only as the Control-1 weakening twin.

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
    """SURGICALLY WEAKENED CLASS PREDICATE ANCHOR.

    The intact anchor returns True iff the author field has NO matching
    attestation token.  This weakened twin returns False unconditionally, so the
    unattested-author-fill CLASS is no longer caught.  The change is confined to
    THIS function; _author_field_token_forged and run are untouched.
    """
    return False


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
