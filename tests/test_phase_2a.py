"""keel_v3.4 Phase-2a: check_author_fill_contamination proving fixtures.

Claims A-D:
  A -- negative: each forgery mode raises AssertionError (8 modes)
  B -- positive: a correctly-attested field does NOT raise
  C -- neuter-bite: disabling author-field iteration removes the raise
  D -- prevention: the gate blocks before returning; the Falsifier value is unmutated

Note on ancestry in non-git fixtures:
  The check calls attest._is_ancestor(ROOT, ts) which runs git and returns False
  in a non-git tmp dir. Every fixture monkeypatches attest._is_ancestor to return
  True EXCEPT the dedicated "bad-provenance" negative case which sets it to False.

Note on replayed-token at the preflight level:
  verify_token raises replayed-token when the token's embedded (artifact, field)
  differs from what is expected. check_author_fill_contamination FIRST filters
  tokens by (artifact, field); a token whose field name does not match is not
  found by the filter at all, so the error manifests as no-token (matching
  subsumption). The replayed fixture case at the preflight level is the closest
  approximation possible: a log exists containing a token for "OtherField" (not
  "Falsifier"); no matching token is found for Falsifier; the check raises with
  no-token. This is documented here and the reason check is omitted for this
  mode per the "(where practical)" caveat.
"""
import sys
import json
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # keel_v3.4/ kit root

import preflight  # noqa: E402
import attest     # noqa: E402
import runtime_roles  # noqa: E402
import pytest     # noqa: E402

# ---------------------------------------------------------------------------
# Fixture constants
# ---------------------------------------------------------------------------

FIX_SECRET = "abcd" * 8      # 64 hex chars = 32 bytes; fixture HMAC secret (never the owner's)
WRONG_SECRET = "ef01" * 8    # distinct wrong secret for forged-hmac mode

ART = "goals/GOALS.md"
FIELD = "Falsifier"
LOCATOR = "section:## Falsifier"
TS = "2026-06-28T12:00:00Z"
TS_STATE = "abc123"


def _sha256(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _build_token(value: str, token_mode: str) -> dict:
    """Return a single token dict for the given mode.

    Modes and their intended defect:
      good           -- valid token (for Claim B positive case)
      revoked        -- valid token for k1; registry marks k1 revoked (set outside)
      bad-provenance -- valid token; _is_ancestor monkeypatched to False
      unregistered   -- token by actor 'ghost' absent from the registry
      replayed       -- token for "OtherField" (not Falsifier); matching step
                        will not find it for Falsifier -> manifests as no-token
      forged-hmac    -- structurally perfect token; HMAC computed with WRONG_SECRET
      malformed      -- raw dict with correct (artifact, field) so it IS selected,
                        but tree_state contains an embedded newline; canonical_payload
                        raises ValueError at verify_token step 1 -> malformed-token
    """
    if token_mode in ("good", "revoked", "bad-provenance"):
        return attest.make_token(FIX_SECRET, ART, FIELD, value, "k1", TS, TS_STATE)
    if token_mode == "unregistered":
        # actor "ghost" is not present in the registry
        return attest.make_token(FIX_SECRET, ART, FIELD, value, "ghost", TS, TS_STATE)
    if token_mode == "replayed":
        # Token for "OtherField" (different field).  The Falsifier filter will not
        # match it; error manifests as no-token at the preflight check level.
        return attest.make_token(FIX_SECRET, ART, "OtherField", value, "k1", TS, TS_STATE)
    if token_mode == "forged-hmac":
        # Structurally perfect token but HMAC uses WRONG_SECRET; FIX_SECRET is
        # present in .attest-secrets.json so the HMAC step actually runs.
        return attest.make_token(WRONG_SECRET, ART, FIELD, value, "k1", TS, TS_STATE)
    if token_mode == "malformed":
        # Built as a raw dict -- NOT via attest.make_token (which would itself
        # reject the newline at canonical_payload time).
        # artifact and field match the selector exactly so the token IS found;
        # tree_state carries a newline so canonical_payload raises ValueError
        # inside verify_token step 1 -> returns ["malformed-token"].
        # value_sha256 is the correct hash of the current value so the defect
        # is isolated to step 1 (it would pass step 4 if it got that far).
        return {
            "artifact": ART,
            "field": FIELD,
            "value_sha256": _sha256(value),
            "actor": "k1",
            "timestamp": TS,
            "tree_state": "abc\ndef",
            "hmac": "bogus",
        }
    raise ValueError(f"unknown token_mode: {token_mode!r}")


def _fixture_kit(tmp_path: Path, *, value: str = "V", token_mode: str = "good") -> Path:
    """Build a minimal fixture kit under tmp_path.

    Writes:
      goals/GOALS.md                -- with ## Falsifier section containing `value`
      goals/.runtime-roles.json     -- declares Falsifier as role:author
      goals/.attest-keys.json       -- k1 registered (revoked for token_mode="revoked")
      goals/.attest-secrets.json    -- {"k1": FIX_SECRET}
      goals/.attest-log.json        -- absent for token_mode="none"; one token otherwise

    Returns tmp_path (the fixture kit root).
    """
    g = tmp_path / "goals"
    g.mkdir(parents=True)

    (g / "GOALS.md").write_text(
        f"## Falsifier\n\n{value}\n", encoding="utf-8")

    (g / ".runtime-roles.json").write_text(json.dumps({"version": 1, "fields": [
        {"artifact": ART, "field": FIELD, "locator": LOCATOR, "role": "author"}
    ]}), encoding="utf-8")

    # Registry: k1 is registered for all modes except "revoked"
    key_status = "revoked" if token_mode == "revoked" else "registered"
    (g / ".attest-keys.json").write_text(json.dumps({
        "version": 1,
        "keys": [{"key_id": "k1", "status": key_status,
                  "secret_sha256": _sha256(FIX_SECRET)}],
        "events": []
    }), encoding="utf-8")

    (g / ".attest-secrets.json").write_text(
        json.dumps({"k1": FIX_SECRET}), encoding="utf-8")

    if token_mode != "none":
        tok = _build_token(value, token_mode)
        (g / ".attest-log.json").write_text(
            json.dumps({"version": 1, "tokens": [tok]}), encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# Claim A -- negative: each forgery mode raises AssertionError
# ---------------------------------------------------------------------------

# (mode, expected_reason_substring_or_None, ancestry_return_value)
# ancestry_return_value is injected into attest._is_ancestor via monkeypatch.
# True for all modes except bad-provenance (which needs False to isolate its defect).
_NEGATIVE_MODES = [
    ("none",          "no-token",                        True),
    ("unregistered",  "unregistered-or-revoked-key",     True),
    ("revoked",       "unregistered-or-revoked-key",     True),
    ("value-changed", "value-changed-since-attestation", True),
    # replayed: manifests as no-token at preflight level (see module docstring);
    # reason check omitted per "(where practical)" caveat.
    ("replayed",      None,                              True),
    ("forged-hmac",   "forged-hmac",                    True),
    ("bad-provenance","tree_state-not-ancestor-of-HEAD", False),
    ("malformed",     "malformed-token",                 True),
]


@pytest.mark.parametrize(
    "mode,reason,ancestry",
    _NEGATIVE_MODES,
    ids=[m[0] for m in _NEGATIVE_MODES],
)
def test_author_fill_unattested_fails(tmp_path, monkeypatch, mode, reason, ancestry):
    """Claim A: every forgery mode raises AssertionError.

    For each mode, every EARLIER check in verify_token's normative order passes
    so that the intended distinct reason is deterministic (GP-5 isolation):
      none          -> no matching token in log                   -> no-token
      unregistered  -> actor not in registry                      -> unregistered-or-revoked-key
      revoked       -> k1 status=revoked                          -> unregistered-or-revoked-key
      value-changed -> sha256(current) != token value_sha256      -> value-changed-since-attestation
      replayed      -> no matching token (field mismatch in log)  -> (no-token at preflight level)
      forged-hmac   -> HMAC with WRONG_SECRET vs FIX_SECRET       -> forged-hmac
      bad-provenance-> _is_ancestor monkeypatched to False        -> tree_state-not-ancestor-of-HEAD
      malformed     -> tree_state has embedded newline; canonical_payload raises -> malformed-token
    """
    value = "V"

    if mode == "value-changed":
        # Build with a good token for "V" then mutate GOALS.md to "CHANGED".
        # The token's value_sha256 is sha256("V"); current is now "CHANGED".
        kit = _fixture_kit(tmp_path, value=value, token_mode="good")
        (kit / "goals" / "GOALS.md").write_text(
            "## Falsifier\n\nCHANGED\n", encoding="utf-8")
    else:
        kit = _fixture_kit(tmp_path, value=value, token_mode=mode)

    monkeypatch.setattr(preflight, "ROOT", kit)
    # Inject ancestry so it does not interfere with the intended defect.
    # bad-provenance: False (the intended defect); all others: True.
    monkeypatch.setattr(attest, "_is_ancestor", lambda root, ts: ancestry)

    with pytest.raises(AssertionError) as exc_info:
        preflight.check_author_fill_contamination()

    if reason is not None:
        assert reason in str(exc_info.value), (
            f"[{mode}] expected distinct reason {reason!r} in error: {exc_info.value!r}"
        )


# ---------------------------------------------------------------------------
# Claim B -- positive: correct attestation does NOT raise
# ---------------------------------------------------------------------------

def test_author_fill_attested_passes(tmp_path, monkeypatch):
    """Claim B: a correctly-attested author field does not raise.

    The fixture mints a token with FIX_SECRET (right value hash, registered
    fixture key, valid HMAC, embedded locator matching the queried field).
    Ancestry is monkeypatched to True because the fixture is not a git repo;
    _is_ancestor would return False in a non-git tmp dir.
    """
    kit = _fixture_kit(tmp_path, value="V", token_mode="good")
    monkeypatch.setattr(preflight, "ROOT", kit)
    monkeypatch.setattr(attest, "_is_ancestor", lambda root, ts: True)

    # Must not raise.
    preflight.check_author_fill_contamination()


# ---------------------------------------------------------------------------
# Claim C -- neuter-bite: disabling author-field iteration removes the raise
# ---------------------------------------------------------------------------

def test_neuter_bite_check_author_fill(tmp_path, monkeypatch):
    """Claim C: the raise in Claim A comes from the author-field iteration,
    not from incidental fixture setup.

    Method: monkeypatch runtime_roles.load_sidecar to return [] (no author
    fields). The same unattested fixture that raises in Claim A must then
    NOT raise -- the check has no author fields to iterate over.

    If the raise persists after the neuter, the test is self-satisfying and
    Claim A is invalid.
    """
    kit = _fixture_kit(tmp_path, value="V", token_mode="none")  # no log -> unattested
    monkeypatch.setattr(preflight, "ROOT", kit)
    monkeypatch.setattr(attest, "_is_ancestor", lambda root, ts: True)

    # Neuter: replace the sidecar loader so no author fields are returned.
    monkeypatch.setattr(runtime_roles, "load_sidecar", lambda root: [])

    # Must NOT raise (the loop body is never entered).
    preflight.check_author_fill_contamination()


# ---------------------------------------------------------------------------
# Claim D -- prevention: gate blocks before returning; Falsifier is unmutated
# ---------------------------------------------------------------------------

def test_prevention_unattested_blocks_gate(tmp_path, monkeypatch):
    """Claim D: check_author_fill_contamination raises (gate blocks) on an
    unattested author-fill BEFORE preflight proceeds. The protected resource
    is the Falsifier value; it must be unchanged by the check (the check is
    read-only/gating, not mutating).
    """
    kit = _fixture_kit(tmp_path, value="V", token_mode="none")
    monkeypatch.setattr(preflight, "ROOT", kit)
    monkeypatch.setattr(attest, "_is_ancestor", lambda root, ts: True)

    goals_md = kit / "goals" / "GOALS.md"
    content_before = goals_md.read_text(encoding="utf-8")

    # Gate blocks: the check raises before returning.
    with pytest.raises(AssertionError):
        preflight.check_author_fill_contamination()

    # Read-only gate: GOALS.md must be unchanged after the check.
    content_after = goals_md.read_text(encoding="utf-8")
    assert content_before == content_after, (
        "check_author_fill_contamination must not mutate GOALS.md "
        f"(before: {content_before!r}, after: {content_after!r})"
    )


# ---------------------------------------------------------------------------
# Conditional-warn: deferred-green discipline (Task 6)
# ---------------------------------------------------------------------------

# Minimal valid hazard-coverage.md for the conditional-warn fixture.
_MATRIX_COLS = [
    "hazard_id", "audit_hazard_ref", "refusal_critical",
    "mitigating_check", "check_return_contract",
    "falsifier_strength", "falsifier_layer",
    "proving_test_negative", "proving_test_positive",
    "prevention_proving_test", "prevention_observation",
    "exercise_scenario", "wired_into", "gate_mode",
    "revalidation_interval_days", "status",
    "silent_path_defense_distance", "substantive_residue",
    "roadmap_defense_distance", "independence_basis", "notes",
]
_MATRIX_HEADER = "| " + " | ".join(_MATRIX_COLS) + " |"
_MATRIX_SEP = "|" + "|".join(["---"] * 21) + "|"
# Minimal conditional row for hz-runtime-role-unannotated (no pipe chars in cells)
_HZ_COND_CELLS = [
    "hz-runtime-role-unannotated", "hz-runtime-role-unannotated", "true",
    "preflight.check_author_fill_contamination", "raises", "full", "execution_time",
    "t_neg", "t_pos", "t_prev", "obs", "ax-runtime-role", "preflight", "default",
    "7", "conditional", "1", "residue", "1", "basis", "notes",
]
_HZ_COND_ROW = "| " + " | ".join(_HZ_COND_CELLS) + " |"


def _fixture_kit_conditional(tmp_path: Path, *, value: str = "V", forged: bool = False) -> Path:
    """Fixture kit with a conditional hz-runtime-role-unannotated row.

    forged=False -> no attestation log  -> no-token problem (SOFT when conditional)
    forged=True  -> token for a wrong value  -> value-changed problem (HARD)
    """
    g = tmp_path / "goals"
    g.mkdir(parents=True)

    (g / "GOALS.md").write_text(f"## Falsifier\n\n{value}\n", encoding="utf-8")

    (g / ".runtime-roles.json").write_text(json.dumps({"version": 1, "fields": [
        {"artifact": ART, "field": FIELD, "locator": LOCATOR, "role": "author"}
    ]}), encoding="utf-8")

    # Minimal hazard-coverage.md: one conditional row for hz-runtime-role-unannotated
    (g / "hazard-coverage.md").write_text(
        "\n".join([_MATRIX_HEADER, _MATRIX_SEP, _HZ_COND_ROW, ""]),
        encoding="utf-8")

    if forged:
        # Token for DIFFERENT_VALUE (not `value`) -> value-changed-since-attestation (HARD)
        tok = attest.make_token(FIX_SECRET, ART, FIELD, "DIFFERENT_VALUE", "k1", TS, TS_STATE)
        (g / ".attest-keys.json").write_text(json.dumps({
            "version": 1,
            "keys": [{"key_id": "k1", "status": "registered",
                      "secret_sha256": _sha256(FIX_SECRET)}],
            "events": [],
        }), encoding="utf-8")
        (g / ".attest-log.json").write_text(
            json.dumps({"version": 1, "tokens": [tok]}), encoding="utf-8")
        (g / ".attest-secrets.json").write_text(
            json.dumps({"k1": FIX_SECRET}), encoding="utf-8")
    else:
        # No log -> no-token (SOFT when conditional -> warns, not raises)
        (g / ".attest-keys.json").write_text(
            json.dumps({"version": 1, "keys": [], "events": []}), encoding="utf-8")

    return tmp_path


def test_conditional_row_warns_not_fails(tmp_path, monkeypatch):
    """Deferred-green discipline: conditional row + no token -> WARN not FAIL.
    Same conditional row + value-changed (HARD forgery) -> still raises.

    Verifies:
    - Soft problems (no-token) downgrade to _WARNED when conditional.
    - Hard problems (value-changed-since-attestation) still assert-fail.
    """
    # -- Part 1: no token -> SOFT -> check does NOT raise; adds to _WARNED --
    preflight._WARNED.clear()
    kit_no_tok = _fixture_kit_conditional(tmp_path / "no_tok", value="V", forged=False)
    monkeypatch.setattr(preflight, "ROOT", kit_no_tok)
    monkeypatch.setattr(attest, "_is_ancestor", lambda root, ts: True)

    # Must NOT raise (warns instead of failing)
    preflight.check_author_fill_contamination()

    # The check must have recorded itself in _WARNED (proof a warn was emitted)
    assert "check_author_fill_contamination" in preflight._WARNED, (
        "expected check to add itself to _WARNED for deferred-green no-token case"
    )

    # -- Part 2: value-changed forged token -> HARD -> raises even when conditional --
    preflight._WARNED.clear()
    kit_forged = _fixture_kit_conditional(tmp_path / "forged", value="V", forged=True)
    monkeypatch.setattr(preflight, "ROOT", kit_forged)
    monkeypatch.setattr(attest, "_is_ancestor", lambda root, ts: True)

    with pytest.raises(AssertionError) as exc_info:
        preflight.check_author_fill_contamination()

    assert "value-changed" in str(exc_info.value), (
        f"expected value-changed-since-attestation in error, got: {exc_info.value!r}"
    )


# ---------------------------------------------------------------------------
# I1: secret-absent advisory -- WARN in session mode, FAIL under --strict
# ---------------------------------------------------------------------------

def _fixture_kit_secret_absent(tmp_path: Path, *, value: str = "V") -> Path:
    """Fixture: valid token for k1, k1 registered, but secret ABSENT from store.

    verify_token receives secret_or_none=None -> advisory 'hmac-unverified-secret-absent'.
    No hazard-coverage.md -> _conditional is False -> strict path goes through assert.
    """
    g = tmp_path / "goals"
    g.mkdir(parents=True)

    (g / "GOALS.md").write_text(f"## Falsifier\n\n{value}\n", encoding="utf-8")

    (g / ".runtime-roles.json").write_text(json.dumps({"version": 1, "fields": [
        {"artifact": ART, "field": FIELD, "locator": LOCATOR, "role": "author"}
    ]}), encoding="utf-8")

    # k1 registered in registry (so key-state step passes)
    (g / ".attest-keys.json").write_text(json.dumps({
        "version": 1,
        "keys": [{"key_id": "k1", "status": "registered",
                  "secret_sha256": _sha256(FIX_SECRET)}],
        "events": [],
    }), encoding="utf-8")

    # Token is structurally valid (correct value hash, registered key, matching locator)
    tok = attest.make_token(FIX_SECRET, ART, FIELD, value, "k1", TS, TS_STATE)
    (g / ".attest-log.json").write_text(
        json.dumps({"version": 1, "tokens": [tok]}), encoding="utf-8")

    # .attest-secrets.json intentionally ABSENT -> secrets.get("k1") returns None
    # No hazard-coverage.md -> _conditional = False

    return tmp_path


def test_secret_absent_session_warns_strict_fails(tmp_path, monkeypatch):
    """I1: hmac-unverified-secret-absent advisory is surfaced as [WARN] in session
    mode (non-fatal) and promoted to AssertionError under --strict.

    Fixture: valid token (k1 registered, correct value hash, embedded locator matching,
    ancestry True), but .attest-secrets.json absent -> secret_or_none=None ->
    verify_token returns errs==[] + advisory 'hmac-unverified-secret-absent'.
    No hazard-coverage.md -> _conditional=False.
    """
    kit = _fixture_kit_secret_absent(tmp_path)
    monkeypatch.setattr(preflight, "ROOT", kit)
    monkeypatch.setattr(attest, "_is_ancestor", lambda root, ts: True)

    # -- Part 1: session mode -> WARN, not raise --
    monkeypatch.setattr(preflight, "STRICT", False)
    preflight._WARNED.clear()
    preflight.check_author_fill_contamination()  # must NOT raise
    assert "check_author_fill_contamination" in preflight._WARNED, (
        "session mode: expected check to add itself to _WARNED for secret-absent advisory"
    )

    # -- Part 2: strict mode -> raise AssertionError with hmac-unverifiable --
    monkeypatch.setattr(preflight, "STRICT", True)
    preflight._WARNED.clear()
    with pytest.raises(AssertionError) as exc_info:
        preflight.check_author_fill_contamination()
    assert "hmac-unverifiable" in str(exc_info.value), (
        f"strict mode: expected 'hmac-unverifiable' in error, got: {exc_info.value!r}"
    )
