import sys, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import attest

SEC = "00ff" * 8
WRONG = "1122" * 8
REG = {"keys": [{"key_id": "k1", "status": "registered"}]}
TS = "2026-06-28T14:03:11Z"

def _vsha(v): return hashlib.sha256(v.encode("utf-8")).hexdigest()

def _good_token(value="V", artifact="a", field="f", actor="k1", secret=SEC):
    return attest.make_token(secret, artifact, field, value, actor, TS, "abc")

def _verify(tok, art="a", field="f", cur="V", reg=REG, secret=SEC, anc=True):
    return attest.verify_token(tok, art, field, cur, reg, secret, lambda ts: anc)

def test_good_token_passes():
    errs, adv = _verify(_good_token())
    assert errs == [], (errs, adv)

def test_unregistered_key():
    errs, _ = _verify(_good_token(actor="ghost"))
    assert errs == ["unregistered-or-revoked-key"], errs

def test_revoked_key():
    reg = {"keys": [{"key_id": "k1", "status": "revoked"}]}
    errs, _ = _verify(_good_token(), reg=reg)
    assert errs == ["unregistered-or-revoked-key"], errs

def test_value_changed():
    errs, _ = _verify(_good_token(value="V"), cur="DIFFERENT")
    assert errs == ["value-changed-since-attestation"], errs

def test_replayed_token():
    # token minted for field 'f' (embedded), used under expected field 'g';
    # current value equals attested so value-binding would pass -> isolated replay
    tok = _good_token(field="f", value="V")
    errs, _ = _verify(tok, field="g", cur="V")
    assert errs == ["replayed-token"], errs

def test_forged_hmac_distinct_secret():
    # structurally perfect token signed with WRONG secret, verified with SEC present
    tok = _good_token(secret=WRONG)
    errs, _ = _verify(tok, secret=SEC)
    assert errs == ["forged-hmac"], errs

def test_malformed_delimiter_injection():
    import pytest
    with pytest.raises(ValueError, match="malformed-token"):
        attest.canonical_payload("a\nb", "f", "h", "k1", TS, "abc")

def test_bad_provenance():
    errs, _ = _verify(_good_token(), anc=False)
    assert errs == ["tree_state-not-ancestor-of-HEAD"], errs

def test_secret_absent_advisory_not_error():
    errs, adv = _verify(_good_token(), secret=None)
    assert errs == [] and adv == ["hmac-unverified-secret-absent"], (errs, adv)
