from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _green_fixture import build_fixture
from hazard_coverage import parse_matrix
import green_rows

def _row(root):
    return parse_matrix(root)[0]

def test_good_row_passes_importable_and_collectible(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return [] if repo_root else ['x']",
        neg_body="assert synth_check(None) == ['x']",   # escape -> check flags
        pos_body="assert synth_check('ok') == []")        # valid -> check passes
    v = green_rows.validate_green_row(root, _row(root))
    assert v == [], v

def test_bad_check_path_fails(tmp_path):
    root = build_fixture(tmp_path, check_body="return []",
        neg_body="assert True", pos_body="assert True")
    row = _row(root)
    row.mitigating_check = "synthcheck.nonexistent_func"
    v = green_rows.validate_green_row(root, row)
    assert any("nonexistent_func" in s or "importable" in s for s in v)

def test_dangling_proving_test_fails(tmp_path):
    root = build_fixture(tmp_path, check_body="return []",
        neg_body="assert True", pos_body="assert True")
    row = _row(root)
    row.proving_test_negative = "tests/test_synth.py::test_does_not_exist"
    v = green_rows.validate_green_row(root, row)
    assert any("test_does_not_exist" in s or "collect" in s for s in v)

def test_nonbiting_negative_test_fails(tmp_path):
    # check NEVER flags anything; negative test asserts it flags -> negative test FAILS
    root = build_fixture(tmp_path,
        check_body="return []",                      # check never flags
        neg_body="assert synth_check('escape') == ['x']",  # expects a flag -> fails
        pos_body="assert synth_check('ok') == []")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("proving test failed" in s or "test_neg" in s for s in v)

def test_biting_tests_pass(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []")
    v = green_rows.validate_green_row(root, _row(root))
    assert v == [], v

def test_vacuous_negative_test_caught_by_neuter(tmp_path):
    # negative test asserts something TRUE regardless of the check -> survives neuter
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert 1 == 1",                       # vacuous: ignores the check
        pos_body="assert synth_check('ok') == []")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("neuter" in s or "vacuous" in s for s in v)

def test_genuine_negative_test_survives_engine(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []")
    v = green_rows.validate_green_row(root, _row(root))
    assert v == [], v

def test_refusal_critical_on_post_hoc_fails(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        refusal_critical=True, layer="post_hoc", strength="partial")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("post_hoc" in s or "execution_time" in s for s in v)

def test_out_of_bounds_interval_fails(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time",   # explicit: this test targets the interval bound only
        refusal_critical=True, strength="full", interval=30)   # >7 for refusal-critical
    v = green_rows.validate_green_row(root, _row(root))
    assert any("interval" in s for s in v)

def test_unwired_check_fails(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        wired="preflight", gate_mode="default")
    # synth_check is NOT in the fixture's preflight (there is none) -> wiring fails
    v = green_rows.validate_green_row(root, _row(root))
    assert any("wired" in s or "preflight" in s for s in v)
    # gate_mode=default is valid; ONLY the wiring violation should fire (isolation)
    assert not any("gate_mode" in s for s in v), v


def test_e2e_fully_good_green_row_passes(tmp_path):
    # importable + collectible + biting + neuter-killed + prevents(A4) with a REAL
    # biting prevention gate + wired(ci) + full/execution_time + bounded interval.
    # The prevention test owns a gate: if the check flags, the tampering write is
    # refused; under neuter (check returns []) the write lands -> prevention fails.
    obs = "resource_lock_state"
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        refusal_critical=True, layer="execution_time", strength="full",
        interval=7, wired="ci", check_return_contract="findings_list",
        prevention_test_body=(
            "import sys, os\n"
            "sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n"
            "from synthcheck import synth_check\n"
            "def test_prevents(tmp_path):\n"
            "    resource_lock_state = tmp_path / 'guarded.txt'\n"
            "    resource_lock_state.write_text('ORIGINAL', encoding='utf-8')\n"
            "    before = resource_lock_state.read_text(encoding='utf-8')\n"
            "    # gate: if the check flags a problem, refuse the tampering write\n"
            "    if not synth_check('escape'):\n"
            "        resource_lock_state.write_text('TAMPERED', encoding='utf-8')\n"
            "    assert resource_lock_state.read_text(encoding='utf-8') == before\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs)
    v = green_rows.validate_green_row(root, _row(root))
    assert v == [], v

def test_e2e_kitchen_sink_broken_row_multiple_violations(tmp_path):
    # non-biting negative test (check never flags) + refusal-critical on
    # partial/post_hoc + out-of-bounds interval + preflight-wired-but-absent.
    root = build_fixture(tmp_path,
        check_body="return []",                              # never flags
        neg_body="assert synth_check('escape') == ['x']",    # expects a flag -> bite fails
        pos_body="assert synth_check('ok') == []",
        refusal_critical=True, layer="post_hoc", strength="partial",
        interval=30, wired="preflight")
    v = green_rows.validate_green_row(root, _row(root))
    # expect at least: bite-fail, strength/layer, freshness interval, wiring
    assert len(v) >= 3, v
    assert any("proving test failed" in s or "test_neg" in s for s in v)   # bite
    assert any("post_hoc" in s or "execution_time" in s for s in v)        # strength/layer
    assert any("interval" in s for s in v)                                  # freshness
    assert any("wired" in s or "preflight" in s for s in v)                 # wiring


def test_high_defense_distance_without_independence_basis_fails(tmp_path):
    # roadmap_defense_distance >= 2 but independence_basis is n/a -> violation
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        wired="ci", roadmap_defense_distance=2, independence_basis="n/a")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("independence_basis" in s or "roadmap_defense_distance" in s for s in v), v


def test_high_defense_distance_with_independence_basis_passes(tmp_path):
    # roadmap_defense_distance >= 2 WITH a populated independence_basis, otherwise fully good -> []
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        wired="ci", roadmap_defense_distance=2,
        independence_basis="distinct-author+method+data")
    v = green_rows.validate_green_row(root, _row(root))
    assert v == [], v


def test_a1_blank_nodeid_rejected(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []")
    row = _row(root)
    row.proving_test_negative = ""
    v = green_rows.validate_green_row(root, row)
    assert any("shape" in s for s in v), v


def test_a1_no_double_colon_rejected(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []")
    row = _row(root)
    row.proving_test_positive = "tests/test_synth.py"  # no ::
    v = green_rows.validate_green_row(root, row)
    assert any("shape" in s for s in v), v


def test_a1_empty_segment_rejected(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []")
    row = _row(root)
    row.proving_test_negative = "tests/test_synth.py::"   # empty segment
    v = green_rows.validate_green_row(root, row)
    assert any("shape" in s for s in v), v


def test_a1_valid_nodeid_still_collects(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="findings_list")
    v = green_rows.validate_green_row(root, _row(root))
    assert v == [], v


def test_a3_missing_contract_rejected(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="n/a")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("check_return_contract" in s or "contract" in s for s in v), v

def test_a3_inexpressible_contract_rejected(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="inexpressible")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("inexpressible" in s or "neuter-contract-inexpressible" in s for s in v), v

def test_a3_findings_list_accepted(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="findings_list")
    assert green_rows.validate_green_row(root, _row(root)) == []

def test_a3_falsy_bool_accepted(tmp_path):
    # NATURAL convention: return bool(problems) → truthy=FLAG, falsy=OK
    root = build_fixture(tmp_path,
        check_body="return True if repo_root == 'escape' else False",
        neg_body="assert synth_check('escape') is True",
        pos_body="assert synth_check('ok') is False",
        check_return_contract="falsy_bool")
    # neutral payload = return False → neutered check returns False on 'escape'
    # → neg test "assert ... is True" FAILS → mutant killed → no vacuity violation
    assert green_rows.validate_green_row(root, _row(root)) == []

def test_a3_truthy_sentinel_accepted(tmp_path):
    root = build_fixture(tmp_path,
        check_body="return True if repo_root != 'escape' else None",
        neg_body="assert synth_check('escape') is None",
        pos_body="assert synth_check('ok') is True",
        check_return_contract="truthy_sentinel")
    assert green_rows.validate_green_row(root, _row(root)) == []


def test_a3_raises_accepted(tmp_path):
    # raises contract: check raises on escape, returns None (no raise) on ok.
    # neutral payload = pass (returns None, no raise) → neg test's "assert False" fires → killed.
    root = build_fixture(tmp_path,
        check_body="if repo_root == 'escape':\n    raise ValueError('flag')",
        neg_body=(
            "try:\n"
            "    synth_check('escape')\n"
            "    assert False, 'should have raised'\n"
            "except ValueError:\n"
            "    pass"
        ),
        pos_body="synth_check('ok')",
        check_return_contract="raises")
    assert green_rows.validate_green_row(root, _row(root)) == []


def test_a3_structured_result_accepted(tmp_path):
    # structured_result contract: populated dict = FLAG, empty dict = OK.
    # neutral payload = return {} → neg test "assert ... != {}" FAILS → mutant killed.
    root = build_fixture(tmp_path,
        check_body="return {'issue': 'found'} if repo_root == 'escape' else {}",
        neg_body="assert synth_check('escape') != {}",
        pos_body="assert synth_check('ok') == {}",
        check_return_contract="structured_result")
    assert green_rows.validate_green_row(root, _row(root)) == []


def test_a3_unknown_contract_rejected(tmp_path):
    # an unrecognised contract string must produce a violation mentioning the enum.
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="bogus")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("bogus" in s or "enum" in s or "contract" in s for s in v), v


def test_a2_second_toplevel_def_rejected(tmp_path):
    """Two top-level defs of same name -> ambiguous -> reject."""
    src = (
        "def synth_check(repo_root):\n    return ['x'] if repo_root == 'escape' else []\n"
        "def synth_check(repo_root):\n    return []\n"
    )
    root = build_fixture(tmp_path, check_module_src=src, check_body="# ignored",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="findings_list")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("ambiguous" in s or "binding" in s or "multiple" in s for s in v), v

def test_a2_async_def_accepted(tmp_path):
    """Single async def is accepted."""
    src = (
        "import asyncio\n"
        "async def synth_check(repo_root):\n"
        "    return ['x'] if repo_root == 'escape' else []\n"
    )
    root = build_fixture(tmp_path, check_module_src=src, check_body="# ignored",
        neg_body="import asyncio; assert asyncio.run(synth_check('escape')) == ['x']",
        pos_body="import asyncio; assert asyncio.run(synth_check('ok')) == []",
        check_return_contract="findings_list")
    assert green_rows.validate_green_row(root, _row(root)) == []

def test_a2_reexport_rejected(tmp_path):
    """Re-exported function has wrong __module__ -> reject."""
    from pathlib import Path as _P
    import shutil as _sh
    from _green_fixture import _MATRIX_HEADER
    _kit = _P(__file__).resolve().parents[2]
    root = tmp_path / "fix"
    (root / "goals").mkdir(parents=True)
    (root / "tests").mkdir()
    _sh.copy(_kit / "goals" / "audit-v3.3.md",         root / "goals" / "audit-v3.3.md")
    _sh.copy(_kit / "goals" / ".audit-lock.json",       root / "goals" / ".audit-lock.json")
    _sh.copy(_kit / "goals" / ".pending-baseline.json", root / "goals" / ".pending-baseline.json")
    (root / "_impl.py").write_text(
        "def synth_check(repo_root):\n    return ['x'] if repo_root == 'escape' else []\n",
        encoding="utf-8")
    (root / "synthcheck.py").write_text("from _impl import synth_check\n", encoding="utf-8")
    (root / "tests" / "test_synth.py").write_text(
        "import sys; from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
        "from synthcheck import synth_check\n"
        "def test_neg():\n    assert synth_check('escape') == ['x']\n"
        "def test_pos():\n    assert synth_check('ok') == []\n", encoding="utf-8")
    row_line = ("| hz-synth | n/a | false | synthcheck.synth_check | findings_list | "
                "full | execution_time | tests/test_synth.py::test_neg | "
                "tests/test_synth.py::test_pos | n/a | n/a | "
                "n/a | ci | n/a | 7 | green | 1 | n/a | 1 | n/a | synthetic |\n")
    (root / "goals" / "hazard-coverage.md").write_text(
        "# fixture\n\n" + _MATRIX_HEADER + row_line, encoding="utf-8")
    v = green_rows.validate_green_row(root, parse_matrix(root)[0])
    assert any("ambiguous" in s or "binding" in s or "re-export" in s or "module" in s for s in v), v

def test_a2_nested_def_not_over_neutered(tmp_path):
    """Nested same-named function must not cause rejection (scoped neuter fix)."""
    src = (
        "def synth_check(repo_root):\n"
        "    def synth_check(x):\n        return ['inner']\n"
        "    return ['x'] if repo_root == 'escape' else []\n"
    )
    root = build_fixture(tmp_path, check_module_src=src, check_body="# ignored",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="findings_list")
    assert green_rows.validate_green_row(root, _row(root)) == []

def test_a2_decorated_check_rejected(tmp_path):
    """Decorated top-level function -> ambiguous-binding rejection.
    A decorator may replace the function object; the named AST node is not
    the runtime callable. Conservative rejection is the correct response."""
    src = (
        "def my_decorator(fn):\n    return fn\n"
        "@my_decorator\n"
        "def synth_check(repo_root):\n"
        "    return ['x'] if repo_root == 'escape' else []\n"
    )
    root = build_fixture(tmp_path, check_module_src=src, check_body="# ignored",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="findings_list")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("ambiguous" in s or "binding" in s or "decorator" in s for s in v), v


def test_a3_sentinel_absent_refuses_kill(tmp_path):
    """_verify_neuter_sentinel returns False when module lacks the sentinel."""
    import tempfile as _tf
    from pathlib import Path as _P
    with _tf.TemporaryDirectory() as td:
        dst = _P(td)
        (dst / "synthcheck.py").write_text(
            "def synth_check(repo_root):\n    return []\n", encoding="utf-8")
        result = green_rows._verify_neuter_sentinel(dst, "synthcheck")
    assert result is False


def test_a3_sentinel_present_ok(tmp_path):
    """_verify_neuter_sentinel returns True when __NEUTER_SENTINEL__ = True."""
    import tempfile as _tf
    from pathlib import Path as _P
    with _tf.TemporaryDirectory() as td:
        dst = _P(td)
        (dst / "synthcheck.py").write_text(
            "__NEUTER_SENTINEL__ = True\ndef synth_check(r):\n    return []\n",
            encoding="utf-8")
        result = green_rows._verify_neuter_sentinel(dst, "synthcheck")
    assert result is True


def test_a3_corollary_positive_fails_under_neuter_rejected(tmp_path):
    """Positive test fails under neuter (type-incompatible payload) -> neuter-contract-inexpressible."""
    # contract=truthy_sentinel -> neutral payload = return True
    # pos_body asserts == [] -> True == [] is False -> pos FAILS under neuter
    root = build_fixture(tmp_path,
        check_body="return [] if repo_root != 'escape' else ['x']",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="truthy_sentinel")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("inexpressible" in s or "corollary" in s or "positive" in s for s in v), v


def test_a3_clean_kill_passes_corollary(tmp_path):
    """Clean kill: negative fails + positive passes under neuter -> no violations."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        check_return_contract="findings_list")
    assert green_rows.validate_green_row(root, _row(root)) == []


def test_a4_execution_time_without_prevention_rejected(tmp_path):
    """execution_time row with no prevention_proving_test -> rejected at _assert_prevents."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        prevention_proving_test="n/a", prevention_observation="n/a")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("prevention" in s.lower() or "prevents" in s for s in v), v

def test_a4_execution_time_without_observation_rejected(tmp_path):
    """execution_time row with prevention test but no observation -> rejected."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        prevention_test_body=(
            "import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))\n"
            "def test_prevents():\n    assert True  # flag-only, no observation reference\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation="n/a")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("prevention_observation" in s or "observation" in s for s in v), v

def test_a4_flag_only_prevention_rejected(tmp_path):
    """prevention test that doesn't reference the observation resource -> rejected."""
    obs = "protected-cache-file.json"
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        prevention_test_body=(
            "def test_prevents():\n    assert True  # flag-only: no mention of the resource\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs)
    v = green_rows.validate_green_row(root, _row(root))
    assert any("flag-only" in s or "observation" in s or "reference" in s for s in v), v

def test_a4_proper_prevention_accepted(tmp_path):
    # execution_time row with a prevention test that owns a biting gate and reads
    # the observation resource in executable code -> accepted.
    obs = "protected_cache_state"
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        prevention_test_body=(
            "import sys, os\n"
            "sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n"
            "from synthcheck import synth_check\n"
            "def test_prevents(tmp_path):\n"
            "    protected_cache_state = tmp_path / 'cache.json'\n"
            "    protected_cache_state.write_text('{}', encoding='utf-8')\n"
            "    before = protected_cache_state.read_text(encoding='utf-8')\n"
            "    if not synth_check('escape'):\n"
            "        protected_cache_state.write_text('TAMPERED', encoding='utf-8')\n"
            "    assert protected_cache_state.read_text(encoding='utf-8') == before\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs,
        refusal_critical=True, strength="full")
    v = green_rows.validate_green_row(root, _row(root))
    assert v == [], v


def test_a7_name_in_comment_only_wiring_rejected(tmp_path):
    """Name appears only in a comment in preflight.py -> wiring rejected."""
    pf_src = (
        "# synth_check would go here if it were wired\n"
        "def main():\n"
        "    checks = []\n"
        "    for check in checks:\n"
        "        check()\n"
    )
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        wired="preflight", gate_mode="default",
        preflight_src=pf_src)
    v = green_rows.validate_green_row(root, _row(root))
    assert any("wired" in s or "preflight" in s or "invoked" in s for s in v), v


def test_a7_name_in_string_literal_wiring_rejected(tmp_path):
    """Name appears only as a string literal -> wiring rejected."""
    pf_src = (
        'WIRED = ["synth_check"]\n'
        "def main():\n"
        "    checks = []\n"
        "    for check in checks:\n"
        "        check()\n"
    )
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        wired="preflight", gate_mode="default",
        preflight_src=pf_src)
    v = green_rows.validate_green_row(root, _row(root))
    assert any("wired" in s or "preflight" in s or "invoked" in s for s in v), v


def test_a7_name_in_checks_list_wiring_ok(tmp_path):
    """Name is a Name node in the checks=[...] list -> wiring ok."""
    pf_src = (
        "def synth_check(): pass\n"
        "def main():\n"
        "    checks = [synth_check]\n"
        "    for check in checks:\n"
        "        check()\n"
    )
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        wired="preflight", gate_mode="default",
        preflight_src=pf_src)
    v = green_rows.validate_green_row(root, _row(root))
    assert v == [], v


def test_a7_bad_gate_mode_rejected(tmp_path):
    """gate_mode not in enum -> rejected."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        gate_mode="unknown-mode")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("gate_mode" in s for s in v), v


def test_a7_preflight_row_gate_mode_na_rejected(tmp_path):
    """wired_into=preflight but gate_mode=n/a -> rejected."""
    pf_src = (
        "def synth_check(): pass\n"
        "def main():\n"
        "    checks = [synth_check]\n"
        "    for check in checks:\n"
        "        check()\n"
    )
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        wired="preflight", gate_mode="n/a",  # bad: preflight row needs a real mode
        preflight_src=pf_src)
    v = green_rows.validate_green_row(root, _row(root))
    assert any("gate_mode" in s for s in v), v


def test_a7_direct_call_invocation_ok(tmp_path):
    """Pattern (i): direct Call(func=Name(id=name)) anywhere in preflight AST satisfies wiring."""
    pf_src = (
        "def main():\n"
        "    synth_check(repo_root)   # direct call, NOT in a checks=[] list\n"
    )
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        wired="preflight", gate_mode="default",
        preflight_src=pf_src)
    v = green_rows.validate_green_row(root, _row(root))
    # Direct call satisfies pattern (i) -> no wiring violation
    assert not any("wired" in s or "invoked" in s.lower() for s in v), v

    # Bite evidence: replace direct call with a comment -> wiring violation reappears
    pf_src_no_call = (
        "def main():\n"
        "    pass  # synth_check(repo_root)  -- commented out\n"
    )
    root2 = build_fixture(tmp_path / "bite",
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        wired="preflight", gate_mode="default",
        preflight_src=pf_src_no_call)
    v2 = green_rows.validate_green_row(root2, _row(root2))
    assert any("wired" in s or "invoked" in s.lower() for s in v2), v2


def test_a8_distance_overclaim_refusal_critical_rejected(tmp_path):
    """refusal_critical=True with silent_path_defense_distance=2 -> rejected at step 5."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        refusal_critical=True, strength="partial",  # strength/layer will also fail; that's ok
        silent_path_defense_distance="2")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("distance" in s for s in v), v

def test_a8_non_critical_numeric_distance_rejected(tmp_path):
    """refusal_critical=False with numeric silent_path_defense_distance -> rejected."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        refusal_critical=False,
        silent_path_defense_distance="2")   # non-critical must be n/a
    v = green_rows.validate_green_row(root, _row(root))
    assert any("distance" in s for s in v), v

def test_a8_refusal_critical_distance_1_roadmap_2_independence_ok(tmp_path):
    """refusal_critical=True, silent=1, roadmap=2, independence_basis populated -> ok."""
    obs = "cache_state_file"  # was "cache.json" (tokens <6); renamed so len>=6 token is present
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        refusal_critical=True, strength="full", interval=7, wired="ci",
        silent_path_defense_distance="1",
        roadmap_defense_distance=2,
        independence_basis="distinct-method+data",
        prevention_test_body=(
            f"import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n"
            f"from synthcheck import synth_check\n"
            f"def test_prevents():\n"
            f"    # {obs} intact -- check must detect escape path\n"
            f"    assert synth_check('escape') != [], '{obs} not protected'\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs)
    v = green_rows.validate_green_row(root, _row(root))
    assert v == [], v


def test_a9_display_rule_surfaces_silent_distance(tmp_path):
    """render_row_summary surfaces silent_path_defense_distance, not roadmap_defense_distance."""
    from hazard_coverage import render_row_summary
    # Make the two distance fields have DIFFERENT values so we can distinguish them
    obs = "log.json"
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        refusal_critical=True, strength="full", interval=7, wired="ci",
        silent_path_defense_distance="1",   # achieved
        roadmap_defense_distance=2,          # aspirational (different value)
        independence_basis="distinct-layer",
        prevention_test_body=(
            "def test_prevents():\n    # log.json intact = stopped\n    assert True\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs)
    row = _row(root)
    summary = render_row_summary(row)
    # achieved distance must appear; roadmap distance must NOT appear as the distance figure
    assert row.roadmap_defense_distance != row.silent_path_defense_distance, \
        "test setup: roadmap and silent must differ"
    assert "1" in summary, f"silent distance '1' absent from summary: {summary!r}"

def test_a9_display_rule_rejects_roadmap_renderer(tmp_path):
    """A render function using roadmap_defense_distance as the headline fails the rule."""
    from hazard_coverage import render_row_summary
    obs = "log.json"
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        refusal_critical=True, strength="full", interval=7, wired="ci",
        silent_path_defense_distance="1",
        roadmap_defense_distance=2,
        independence_basis="distinct-layer",
        prevention_test_body=(
            "def test_prevents():\n    # log.json intact = stopped\n    assert True\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs)
    row = _row(root)
    # Good renderer: uses silent_path_defense_distance
    good = render_row_summary(row)
    assert row.silent_path_defense_distance in good
    # The rule: bad renderer would fail because it surfaces roadmap not silent
    assert row.roadmap_defense_distance not in good, \
        "render_row_summary must not expose roadmap_defense_distance as the distance figure"


import pytest

# ---------------------------------------------------------------------------
# ADV-1: post-hoc relabeled as execution_time
# ---------------------------------------------------------------------------

def test_adv_posthoc_relabeled_execution_time_rejected(tmp_path):
    """ADV-1: detector declared execution_time but no real prevention test.
    A post-hoc check that merely detects after the fact cannot earn the
    execution_time label without a prevention_proving_test referencing the
    protected resource. Caught at step 4b (_assert_prevents)."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        prevention_proving_test="n/a",   # missing: no real prevention
        prevention_observation="n/a")    # missing
    v = green_rows.validate_green_row(root, _row(root))
    assert any("prevention" in s.lower() or "prevents" in s for s in v), \
        f"Expected prevention violation for post-hoc-relabeled pattern; got: {v}"


# ---------------------------------------------------------------------------
# ADV-2: vacuous-but-collectible
# ---------------------------------------------------------------------------

def test_adv_vacuous_but_collectible_rejected(tmp_path):
    """ADV-2: negative test is collectible and passes bite (trivially true)
    but does not depend on the check -> survives neuter -> caught at _assert_neuter_probe.
    Demonstrates that test existence alone does not satisfy the engine."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert 1 == 1",     # vacuous: ignores the check entirely
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("neuter" in s or "vacuous" in s for s in v), \
        f"Expected neuter-survived violation for vacuous-but-collectible pattern; got: {v}"


# ---------------------------------------------------------------------------
# ADV-3: distance-overclaim
# ---------------------------------------------------------------------------

def test_adv_distance_overclaim_rejected(tmp_path):
    """ADV-3: silent_path_defense_distance=2 on a non-critical row (no second
    executably-verified barrier exists in Phase 1c). Caught at _assert_distance (step 5).
    Companion display falsifier: a renderer using roadmap_defense_distance would
    surface the overclaim as if it were achieved (caught by A.9 test suite)."""
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="post_hoc", check_return_contract="findings_list",
        refusal_critical=False,
        silent_path_defense_distance="2")   # overclaim: non-critical must be n/a
    v = green_rows.validate_green_row(root, _row(root))
    assert any("distance" in s for s in v), \
        f"Expected distance violation for overclaim pattern; got: {v}"


# ---------------------------------------------------------------------------
# ADV-4: cache-survives-strict (deferred)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason=(
    "cache-survives-strict adversarial pattern requires real reachability/"
    "--strict cache semantics and cannot be honestly encoded against a "
    "synthetic green-row fixture in 1c-A. The pattern: a check whose cached "
    "pass survives --strict mode (session-mode cache accepted in ratification) "
    "is realized in 1c-B against the real check_reachability_probes_pass row, "
    "which has the actual --strict/cache logic. Do NOT remove or fake this test; "
    "it is the 1c-B anchor."
))
def test_adv_cache_survives_strict_deferred():
    """ADV-4 deferred to 1c-B. See skip reason."""
    pytest.fail("should be skipped")


# ---------------------------------------------------------------------------
# GP-6: baseline-isolation
# ---------------------------------------------------------------------------

def test_baseline_isolation_schema_strictness(tmp_path):
    """GP-6: parse_matrix raises ValueError for wrong column count, isolating
    test failures to substantive engine violations, not schema skew."""
    from hazard_coverage import parse_matrix, _EXPECTED_COLS
    import pytest as _pytest
    assert len(_EXPECTED_COLS) == 21, (
        f"Expected 21 columns post-migration; got {len(_EXPECTED_COLS)}")
    bad_md = "# x\n\n| col1 | col2 |\n|---|---|\n| a | b |\n"
    (tmp_path / "goals").mkdir()
    (tmp_path / "goals" / "hazard-coverage.md").write_text(bad_md, encoding="utf-8")
    with _pytest.raises(ValueError, match="columns"):
        parse_matrix(tmp_path)


def test_i1_vacuous_prevention_test_caught_by_neuter(tmp_path):
    # execution_time row whose prevention test ALWAYS passes (assert True) and
    # mentions the observation token in EXECUTABLE code (so it is not rejected by
    # the obs-enforcement in Task 2) -- it must still be rejected by the I1
    # prevention-bite: neutering the check does not make the prevention test fail.
    obs = "resource_lock_file"
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        prevention_test_body=(
            "def test_prevents():\n"
            "    resource_lock_file = 'present'\n"
            "    assert resource_lock_file == 'present'  # vacuous: never depends on the check\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs,
        refusal_critical=True, strength="full")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("prevention-probe survived" in s for s in v), v


def test_i1_obs_in_comment_only_rejected(tmp_path):
    # prevention_observation token appears ONLY in a comment -> rejected (comments
    # do not reach the AST; an executable reference is required).
    obs = "protected_resource_file"
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        prevention_test_body=(
            "def test_prevents():\n"
            "    # protected_resource_file stays intact after the attempt\n"
            "    assert True\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs,
        refusal_critical=True, strength="full")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("EXECUTABLE code" in s for s in v), v


def test_i1_obs_too_short_rejected(tmp_path):
    # prevention_observation has no token of length >=6 -> too vague to anchor.
    obs = "x.y z"
    root = build_fixture(tmp_path,
        check_body="return ['x'] if repo_root == 'escape' else []",
        neg_body="assert synth_check('escape') == ['x']",
        pos_body="assert synth_check('ok') == []",
        layer="execution_time", check_return_contract="findings_list",
        prevention_test_body=(
            "def test_prevents():\n"
            "    assert True  # x present\n"),
        prevention_proving_test="tests/test_prevention.py::test_prevents",
        prevention_observation=obs,
        refusal_critical=True, strength="full")
    v = green_rows.validate_green_row(root, _row(root))
    assert any("length>=6" in s for s in v), v


def test_i2_raises_root_global_shape_neuter_bites(tmp_path):
    # Realistic shape: a zero-arg check that reads a module-global ROOT and raises
    # (assert) on a bad state. The neutral payload for 'raises' is `pass` (no raise);
    # the negative proving test (expects a raise) must then FAIL under neuter.
    check_src = (
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parent\n"
        "def synth_check():\n"
        "    sentinel = ROOT / 'sentinel.txt'\n"
        "    assert sentinel.exists(), 'sentinel missing'\n")
    test_src = (
        "import sys, os\n"
        "sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n"
        "import synthcheck, pytest\n"
        "def test_neg(tmp_path, monkeypatch):\n"
        "    monkeypatch.setattr(synthcheck, 'ROOT', tmp_path)\n"
        "    # tmp_path has no sentinel.txt -> the check must raise\n"
        "    with pytest.raises(AssertionError):\n"
        "        synthcheck.synth_check()\n"
        "def test_pos(tmp_path, monkeypatch):\n"
        "    (tmp_path / 'sentinel.txt').write_text('ok', encoding='utf-8')\n"
        "    monkeypatch.setattr(synthcheck, 'ROOT', tmp_path)\n"
        "    synthcheck.synth_check()  # no raise -> pass\n")
    root = build_fixture(tmp_path,
        check_module_src=check_src, check_body="# ignored",
        synth_test_src=test_src,
        neg_body="# ignored", pos_body="# ignored",
        check_return_contract="raises")
    row = _row(root)
    row.mitigating_check = "synthcheck.synth_check"
    assert green_rows.validate_green_row(root, row) == [], \
        green_rows.validate_green_row(root, row)


def test_i2_raises_root_global_vacuous_neg_caught(tmp_path):
    # Same shape, but the negative test does NOT actually drive the check into a
    # raising state (it asserts something unconditional) -> neuter survives -> reject.
    check_src = (
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parent\n"
        "def synth_check():\n"
        "    sentinel = ROOT / 'sentinel.txt'\n"
        "    assert sentinel.exists(), 'sentinel missing'\n")
    test_src = (
        "import sys, os\n"
        "sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n"
        "import synthcheck, pytest\n"
        "def test_neg():\n"
        "    assert 1 == 1  # vacuous: never calls the check\n"
        "def test_pos(tmp_path, monkeypatch):\n"
        "    (tmp_path / 'sentinel.txt').write_text('ok', encoding='utf-8')\n"
        "    monkeypatch.setattr(synthcheck, 'ROOT', tmp_path)\n"
        "    synthcheck.synth_check()\n")
    root = build_fixture(tmp_path,
        check_module_src=check_src, check_body="# ignored",
        synth_test_src=test_src, neg_body="# ignored", pos_body="# ignored",
        check_return_contract="raises")
    row = _row(root)
    row.mitigating_check = "synthcheck.synth_check"
    v = green_rows.validate_green_row(root, row)
    assert any("neuter" in s or "vacuous" in s for s in v), v


# ---------------------------------------------------------------------------
# C-5: production-gate rule (_assert_production_gate)
# ---------------------------------------------------------------------------

def _c5_row(root, mitigating_check, ppt):
    r = _row(root)
    r.mitigating_check = mitigating_check
    r.prevention_proving_test = ppt
    return r

def test_c5_test_owned_gate_rejected(tmp_path):
    # Prevention test calls should_block itself and branches on its return ->
    # fails C-5(b): the gate is test-local, not driven through main().
    check_src = (
        "def should_block(tool_input, project_dir):\n"
        "    return bool(tool_input)\n"
        "def main():\n"
        "    pass\n")
    root = build_fixture(tmp_path,
        check_module_src=check_src, check_body="# ignored",
        neg_body="# ignored", pos_body="# ignored",
        synth_test_src=(
            "import sys, os\n"
            "sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n"
            "import synthcheck\n"
            "def test_prevents(tmp_path):\n"
            "    guarded = tmp_path / 'adr.md'\n"
            "    guarded.write_text('ACCEPTED', encoding='utf-8')\n"
            "    before = guarded.read_text(encoding='utf-8')\n"
            "    if not synthcheck.should_block({'x': 1}, str(tmp_path)):\n"
            "        guarded.write_text('TAMPERED', encoding='utf-8')\n"
            "    assert guarded.read_text(encoding='utf-8') == before\n"),
        check_return_contract="falsy_bool")
    # repoint test_synth's generated names is unnecessary; we drive _assert_production_gate directly.
    (root / "tests" / "test_prevention.py").write_text(
        (root / "tests" / "test_synth.py").read_text(encoding="utf-8"), encoding="utf-8")
    row = _c5_row(root, "synthcheck.should_block",
                  "tests/test_prevention.py::test_prevents")
    v = green_rows._assert_production_gate(root, row)
    assert any("C-5(b)" in s for s in v), v

def test_c5_main_driven_gate_accepted(tmp_path):
    # Prevention test drives the real main() via a subprocess with stdin; the test
    # does NOT call should_block itself -> passes C-5 (a),(b),(c).
    check_src = (
        "import sys, json\n"
        "def should_block(tool_input, project_dir):\n"
        "    return bool(tool_input.get('blocked'))\n"
        "def main():\n"
        "    data = json.loads(sys.stdin.read() or '{}')\n"
        "    if should_block(data.get('tool_input', {}), data.get('cwd', '.')):\n"
        "        print(json.dumps({'decision': 'ask'}))\n"
        "if __name__ == '__main__':\n"
        "    main()\n")
    root = build_fixture(tmp_path,
        check_module_src=check_src, check_body="# ignored",
        neg_body="# ignored", pos_body="# ignored",
        synth_test_src="def test_placeholder():\n    pass\n",
        check_return_contract="falsy_bool")
    (root / "tests" / "test_prevention.py").write_text(
        "import sys, os, json, subprocess\n"
        "def test_prevents(tmp_path):\n"
        "    guarded = tmp_path / 'adr.md'\n"
        "    guarded.write_text('ACCEPTED', encoding='utf-8')\n"
        "    before = guarded.read_text(encoding='utf-8')\n"
        "    payload = json.dumps({'tool_input': {'blocked': True}, 'cwd': str(tmp_path)})\n"
        "    mod = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'synthcheck.py')\n"
        "    r = subprocess.run([sys.executable, mod], input=payload,\n"
        "                       capture_output=True, text=True)\n"
        "    if 'ask' not in r.stdout:\n"
        "        guarded.write_text('TAMPERED', encoding='utf-8')\n"
        "    assert guarded.read_text(encoding='utf-8') == before\n",
        encoding="utf-8")
    row = _c5_row(root, "synthcheck.should_block",
                  "tests/test_prevention.py::test_prevents")
    v = green_rows._assert_production_gate(root, row)
    assert v == [], v

def test_c5_test_module_symbol_rejected(tmp_path):
    # mitigating_check resolves into a tests/ module -> fails C-5(a).
    root = build_fixture(tmp_path,
        check_body="return []", neg_body="# ignored", pos_body="# ignored",
        check_return_contract="falsy_bool")
    (root / "tests" / "test_prevention.py").write_text(
        "def test_prevents():\n    assert True  # adr_content\n", encoding="utf-8")
    row = _c5_row(root, "tests.test_prevention.test_prevents",
                  "tests/test_prevention.py::test_prevents")
    v = green_rows._assert_production_gate(root, row)
    assert any("C-5(a)" in s for s in v), v
