import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import attest

def _kit(tmp_path):
    (tmp_path / "goals").mkdir(parents=True)
    return tmp_path

def test_register_writes_secret_gitignored_not_registry(tmp_path):
    k = _kit(tmp_path)
    attest.register(k, "owner")
    secrets = json.loads((k / "goals" / ".attest-secrets.json").read_text())
    registry = json.loads((k / "goals" / ".attest-keys.json").read_text())
    assert "owner" in secrets and len(secrets["owner"]) >= 32
    key = [x for x in registry["keys"] if x["key_id"] == "owner"][0]
    assert key["status"] == "registered"
    # the raw secret must NOT appear in the committed registry text
    assert secrets["owner"] not in (k / "goals" / ".attest-keys.json").read_text()

def test_revoke_sets_status(tmp_path):
    k = _kit(tmp_path)
    attest.register(k, "owner")
    attest.revoke(k, "owner")
    registry = json.loads((k / "goals" / ".attest-keys.json").read_text())
    key = [x for x in registry["keys"] if x["key_id"] == "owner"][0]
    assert key["status"] == "revoked"
    assert any(e["event"] == "revoke" for e in registry["events"])
