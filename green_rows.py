"""KEEL v3.4 green-row assertion engine: what a matrix row must satisfy to be
status: green honestly. Called by check_hazard_coverage for green rows only.
Phase 1b: assertions importable(1), collectible(2), bite+neuter(3), wiring(4),
strength/layer(7), freshness-decl(8). No real rows are green yet."""
from __future__ import annotations
import ast
import importlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _run_pytest(repo_root: Path, args: list[str]):
    return subprocess.run([sys.executable, "-m", "pytest", *args],
                          cwd=repo_root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _assert_importable(repo_root: Path, row) -> list[str]:
    dotted = row.mitigating_check
    if "." not in dotted:
        return [f"{row.hazard_id}: mitigating_check '{dotted}' is not module.func"]
    mod_name, func = dotted.rsplit(".", 1)
    added = str(repo_root) not in sys.path
    if added:
        sys.path.insert(0, str(repo_root))
    try:
        mod = importlib.import_module(mod_name)
        importlib.reload(mod)
        if not hasattr(mod, func):
            return [f"{row.hazard_id}: {mod_name} has no '{func}'"]
    except Exception as e:  # noqa: BLE001 -- surfaced as a violation, fail-closed
        return [f"{row.hazard_id}: cannot import {mod_name}: {e}"]
    finally:
        if added and str(repo_root) in sys.path:
            sys.path.remove(str(repo_root))
    return []


def _valid_nodeid(nodeid: str) -> bool:
    """True iff nodeid contains '::' followed by a non-empty test segment."""
    if not nodeid or "::" not in nodeid:
        return False
    return bool(nodeid.split("::")[-1].strip())


def _assert_collectible(repo_root: Path, row) -> list[str]:
    out: list[str] = []
    nodeids = [row.proving_test_negative, row.proving_test_positive]
    if (row.falsifier_layer == "execution_time"
            and row.prevention_proving_test not in ("", "n/a")):
        nodeids.append(row.prevention_proving_test)
    for nodeid in nodeids:
        if not _valid_nodeid(nodeid):
            out.append(
                f"{row.hazard_id}: nodeid shape invalid "
                f"(must contain '::' + non-empty segment): {nodeid!r}")
            continue  # skip pytest spawn for malformed nodeid
        r = _run_pytest(repo_root, ["--collect-only", "-q", nodeid])
        if r.returncode != 0 or nodeid.split("::")[-1] not in r.stdout:
            out.append(f"{row.hazard_id}: proving test not collectible: {nodeid}")
    return out


def _assert_bite(repo_root: Path, row) -> list[str]:
    out: list[str] = []
    for label, nodeid in (("negative", row.proving_test_negative),
                          ("positive", row.proving_test_positive)):
        r = _run_pytest(repo_root, ["-q", nodeid])
        if r.returncode != 0:
            out.append(f"{row.hazard_id}: {label} proving test failed "
                       f"({nodeid}) -- a green row's proving tests must pass:\n"
                       + r.stdout[-400:])
    return out


_CONTRACT_ENUM = frozenset({
    "findings_list", "falsy_bool", "raises", "truthy_sentinel", "structured_result"
})


def _neutral_payload(contract: str) -> "list[ast.stmt]":
    if contract == "findings_list":
        return [ast.Return(value=ast.List(elts=[], ctx=ast.Load()))]
    if contract == "falsy_bool":
        return [ast.Return(value=ast.Constant(value=False))]
    if contract == "raises":
        return [ast.Pass()]
    if contract == "truthy_sentinel":
        return [ast.Return(value=ast.Constant(value=True))]
    if contract == "structured_result":
        return [ast.Return(value=ast.Dict(keys=[], values=[]))]
    return [ast.Return(value=ast.Constant(value=None))]  # unreachable after validation


_SENTINEL_ATTR = "__NEUTER_SENTINEL__"


def _neuter_source(src: str, func: str, contract: str) -> "str | None":
    """Scoped neuter with sentinel injection at tree.body[0].
    Claim bound (A3, R2): sentinel proves neutered module was imported, not that mutation caused failure."""
    tree = ast.parse(src)
    payload = _neutral_payload(contract)
    found = False
    for node in tree.body:   # module top-level only
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
            node.body = payload[:]
            found = True
            break
    if not found:
        return None
    sentinel = ast.Assign(
        targets=[ast.Name(id=_SENTINEL_ATTR, ctx=ast.Store())],
        value=ast.Constant(value=True),
        lineno=0, col_offset=0)
    tree.body.insert(0, sentinel)
    return ast.unparse(ast.fix_missing_locations(tree))


def _verify_neuter_sentinel(dst: Path, mod_name: str) -> bool:
    """True iff the module at dst has __NEUTER_SENTINEL__ = True when imported in subprocess."""
    r = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, '.'); "
         f"import {mod_name}; "
         f"assert getattr({mod_name}, '{_SENTINEL_ATTR}', None) is True"],
        cwd=dst, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0


def _resolve_binding(repo_root: Path, mod_name: str, func: str) -> list[str]:
    """Returns violations for ambiguous top-level bindings."""
    rel = mod_name.replace(".", "/") + ".py"
    src_file = repo_root / rel
    if not src_file.exists():
        return []  # caught by _assert_importable; no double-report
    try:
        tree = ast.parse(src_file.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"{mod_name}.{func}: SyntaxError in binding check: {exc}"]
    toplevel = [
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func
    ]
    if len(toplevel) > 1:
        return [f"{mod_name}.{func}: ambiguous binding -- {len(toplevel)} top-level defs "
                f"of same name (later shadows earlier); cannot safely mutate"]
    # Conservative decorator rejection: a decorator may replace the function object;
    # the named AST node is then not the runtime callable, making mutation unsound.
    if len(toplevel) == 1 and toplevel[0].decorator_list:
        return [f"{mod_name}.{func}: ambiguous binding -- decorated function "
                f"(non-empty decorator_list); decorator may replace the function object "
                f"so the named AST node may not be the runtime callable; "
                f"cannot safely select mutation target (spec A2)"]
    # Runtime __module__ check
    added = str(repo_root) not in sys.path
    if added:
        sys.path.insert(0, str(repo_root))
    try:
        mod = importlib.import_module(mod_name)
        importlib.reload(mod)
        obj = getattr(mod, func, None)
        if obj is None:
            return []  # caught by importable
        if hasattr(obj, "__wrapped__"):
            return [f"{mod_name}.{func}: ambiguous binding -- __wrapped__ attribute present "
                    f"(decorator replaced the function object); "
                    f"cannot safely mutate the named AST def (spec A2)"]
        obj_mod = getattr(obj, "__module__", None)
        if obj_mod is not None and obj_mod != mod_name:
            return [f"{mod_name}.{func}: ambiguous binding -- re-export detected "
                    f"(runtime __module__={obj_mod!r} != declared {mod_name!r}); "
                    f"real definition lives in {obj_mod!r}"]
    except Exception as exc:  # noqa: BLE001
        return [f"{mod_name}.{func}: binding-identity import error: {exc}"]
    finally:
        if added and str(repo_root) in sys.path:
            sys.path.remove(str(repo_root))
    return []


def _assert_binding_identity(repo_root: Path, row) -> list[str]:
    if "." not in row.mitigating_check:
        return []
    mod_name, func = row.mitigating_check.rsplit(".", 1)
    return _resolve_binding(repo_root, mod_name, func)


def _assert_return_contract(repo_root: Path, row) -> list[str]:
    contract = row.check_return_contract
    if not contract or contract in ("", "n/a"):
        return [f"{row.hazard_id}: check_return_contract not declared "
                f"(must be one of {sorted(_CONTRACT_ENUM)})"]
    if contract == "inexpressible":
        return [f"{row.hazard_id}: neuter-contract-inexpressible -- "
                f"check_return_contract='inexpressible' means this row may not green in 1c; "
                f"stay pending with honest label"]
    if contract not in _CONTRACT_ENUM:
        return [f"{row.hazard_id}: check_return_contract '{contract}' not in enum "
                f"{sorted(_CONTRACT_ENUM)}"]
    return []


def _assert_neuter_probe(repo_root: Path, row) -> list[str]:
    mod_name, func = row.mitigating_check.rsplit(".", 1)
    rel = mod_name.replace(".", "/") + ".py"
    src_file = repo_root / rel
    if not src_file.exists():
        return [f"{row.hazard_id}: cannot locate source for {mod_name} to neuter-probe"]
    neutered = _neuter_source(
        src_file.read_text(encoding="utf-8"), func, row.check_return_contract)
    if neutered is None:
        return [f"{row.hazard_id}: function {func} not found in {mod_name} for neuter-probe"]
    with tempfile.TemporaryDirectory() as td:
        # Copy the repo and overwrite the check's source with the neutered version,
        # then run the negative test with cwd=copy so the neutered module wins import.
        # (A PYTHONPATH shadow does not work: `python -m pytest` puts cwd at sys.path[0]
        #  and the fixture's test re-inserts the real module dir at sys.path[0].)
        dst = Path(td) / "neutered_copy"
        shutil.copytree(repo_root, dst)
        (dst / rel).write_text(neutered, encoding="utf-8")

        # A3: sentinel — confirm subprocess imports the neutered module
        if not _verify_neuter_sentinel(dst, mod_name):
            return [f"{row.hazard_id}: neuter-sentinel-absent -- "
                    f"subprocess did not import the neutered module (sentinel check failed); "
                    f"kill verdict refused (A3)"]

        # A3 corollary: positive test must still pass under neuter
        r_pos = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", row.proving_test_positive],
            cwd=dst, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r_pos.returncode != 0:
            snippet = (r_pos.stdout + r_pos.stderr)[-300:]
            return [f"{row.hazard_id}: neuter-contract-inexpressible (A3 corollary) -- "
                    f"positive proving test ({row.proving_test_positive}) fails under neuter; "
                    f"neutral payload incompatible with check pass-signal; "
                    f"classify crash/inconclusive, reject verdict. Snippet: {snippet}"]

        # Kill check: negative test must fail under neutered module.
        # mutant KILLED == negative test now FAILS (returncode != 0).
        r_neg = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", row.proving_test_negative],
            cwd=dst, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r_neg.returncode == 0:
            return [f"{row.hazard_id}: neuter-probe survived -- negative proving test "
                    f"({row.proving_test_negative}) still passes when {func} is neutered (vacuous)"]

        # I1: prevention-bite. An execution_time row's prevention test must ALSO
        # fail under neuter -- otherwise it is vacuous (e.g. an assert True that
        # passes regardless of the check). A prevention test that survives neuter
        # does not depend on the check and cannot prove the action was stopped.
        if (row.falsifier_layer == "execution_time"
                and row.prevention_proving_test not in ("", "n/a")):
            r_prev = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", row.prevention_proving_test],
                cwd=dst, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r_prev.returncode == 0:
                return [f"{row.hazard_id}: prevention-probe survived -- prevention proving "
                        f"test ({row.prevention_proving_test}) still passes when {func} is "
                        f"neutered (vacuous prevention; the test does not depend on the "
                        f"check -- I1)"]
    return []


_GATE_MODE_ENUM = frozenset({"default", "--strict", "--compliance", "n/a"})


def _assert_invoked_in(repo_root: Path, name: str) -> bool:
    """True iff 'name' is statically invoked (or listed in a checks=[...] list)
    in preflight.py. Comment/string/dead-import presence does NOT satisfy this.

    Recognizes two patterns from preflight.py's actual structure:
      (i)  direct call: name(...)  anywhere in the AST
      (ii) list element: checks = [..., name, ...] as an ast.Name node

    Static over-approximation (R8): structural AST match; does not prove
    runtime reachability of the loop. Caught at the gate by the green-row
    proving tests that exercise the declared entrypoint (1c-B)."""
    pf = repo_root / "preflight.py"
    if not pf.exists():
        return False
    try:
        tree = ast.parse(pf.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        # Pattern (i): direct call synth_check(...)
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == name):
            return True
        # Pattern (ii): checks = [..., synth_check, ...]
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "checks":
                    if isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Name) and elt.id == name:
                                return True
    return False


def _assert_wiring(repo_root: Path, row) -> list[str]:
    """Wiring-by-invocation (A.7): replaces the old textual 'name in preflight.py'."""
    targets = [t.strip() for t in row.wired_into.split("|")] if row.wired_into else []
    name = row.mitigating_check.rsplit(".", 1)[-1]
    out: list[str] = []
    if "preflight" in targets:
        if not _assert_invoked_in(repo_root, name):
            out.append(
                f"{row.hazard_id}: wired_into=preflight but '{name}' is not "
                f"statically invoked in preflight.py (not in checks list or direct call); "
                f"comment/string/dead-import presence does not satisfy wiring (A.7)")
    return out


def _assert_gate_mode(row) -> list[str]:
    out: list[str] = []
    if row.gate_mode not in _GATE_MODE_ENUM:
        out.append(
            f"{row.hazard_id}: gate_mode '{row.gate_mode}' not in "
            f"{sorted(_GATE_MODE_ENUM)}")
        return out
    targets = [t.strip() for t in row.wired_into.split("|")] if row.wired_into else []
    if "preflight" in targets and row.gate_mode == "n/a":
        out.append(
            f"{row.hazard_id}: wired_into=preflight requires a real gate_mode "
            f"('default', '--strict', or '--compliance'); 'n/a' is not valid for preflight rows")
    return out


def _assert_distance(row) -> list[str]:
    """Step 5: single-barrier accounting.

    Phase 1c constraint: only one barrier can be executably verified (the
    mitigating check itself). Therefore:
    - refusal_critical rows must declare silent_path_defense_distance == "1"
    - non-refusal_critical rows must declare silent_path_defense_distance == "n/a"
      (a numeric claim on a non-critical row is an overclaim)

    roadmap_defense_distance >= 2 -> independence_basis is enforced in
    _assert_strength_layer (unchanged)."""
    spdd = row.silent_path_defense_distance
    out: list[str] = []
    if row.refusal_critical:
        if spdd != "1":
            out.append(
                f"{row.hazard_id}: refusal_critical green row must have "
                f"silent_path_defense_distance==1 (one executably-verified barrier "
                f"in Phase 1c); got {spdd!r}")
    else:
        try:
            int(spdd)  # any numeric value on a non-critical row is an overclaim
            out.append(
                f"{row.hazard_id}: non-refusal_critical row must have "
                f"silent_path_defense_distance=='n/a' (only one barrier may be claimed "
                f"per executably-verified check; non-critical rows claim no achieved "
                f"silent-path distance); got {spdd!r}")
        except (ValueError, TypeError):
            pass  # "n/a" or "pending" -> ok for non-critical
    return out


def _assert_strength_layer(repo_root: Path, row) -> list[str]:
    out: list[str] = []
    if row.refusal_critical and (row.falsifier_layer != "execution_time"
                                 or row.falsifier_strength != "full"):
        out.append(f"{row.hazard_id}: refusal-critical green row needs full/execution_time "
                   f"(has {row.falsifier_strength}/{row.falsifier_layer})")
    try:
        if int(row.roadmap_defense_distance) >= 2 and row.independence_basis in ("", "n/a"):
            out.append(f"{row.hazard_id}: roadmap_defense_distance>=2 requires an independence_basis")
    except (ValueError, TypeError):
        pass
    return out


def _obs_in_executable_code(test_src: str, test_func: str, obs: str) -> bool:
    """True iff an obs-token (len>=6) appears in EXECUTABLE code of the named test
    function -- as an identifier (Name/Attribute/arg/keyword) or a non-docstring
    string constant -- not merely in a comment. Comments never reach the AST, so
    this closes the comment-only-naming hole (I1). Substring match: token 'content'
    matches identifier 'content_before'."""
    tokens = [t for t in obs.replace("-", " ").replace(".", " ")
              .replace("(", " ").replace(")", " ").split() if len(t) >= 6]
    if not tokens:
        return False
    try:
        tree = ast.parse(test_src)
    except SyntaxError:
        return False
    func = None
    for node in ast.walk(tree):
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == test_func):
            func = node
            break
    if func is None:
        return False
    doc = ast.get_docstring(func)
    haystacks: list[str] = []
    for n in ast.walk(func):
        if isinstance(n, ast.Name):
            haystacks.append(n.id)
        elif isinstance(n, ast.Attribute):
            haystacks.append(n.attr)
        elif isinstance(n, ast.arg):
            haystacks.append(n.arg)
        elif isinstance(n, ast.keyword) and n.arg:
            haystacks.append(n.arg)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            if doc is None or n.value != doc:
                haystacks.append(n.value)
    return any(any(tok in h for h in haystacks) for tok in tokens)


def _assert_prevents(repo_root: Path, row) -> list[str]:
    """A4: execution_time rows must show the action stops, not just detect it.
    Requires a passing prevention_proving_test whose source references the
    prevention_observation resource (not a local flag).
    Claim bound (A4/R4): token presence in source proves the test READ the
    protected resource; it does not prove the resource's state is authoritative.
    Scope bound: verifies the prevention test passes and references the observation
    resource, but does NOT verify the test exercises the check through the declared
    gate_mode entrypoint (runtime-reachability binding is the §4 conformance
    non-commitment / R8; the greening proving tests in 1c-B drive the real entrypoint)."""
    if row.falsifier_layer != "execution_time":
        return []
    out: list[str] = []
    ppt = row.prevention_proving_test
    obs = row.prevention_observation
    if not ppt or ppt in ("", "n/a"):
        out.append(
            f"{row.hazard_id}: falsifier_layer=execution_time requires "
            f"prevention_proving_test (A4: must show action stops, not just detect after the fact)")
        return out
    if not obs or obs in ("", "n/a"):
        out.append(
            f"{row.hazard_id}: falsifier_layer=execution_time requires "
            f"prevention_observation (the protected resource the prevention test reads)")
        return out
    # prevention_proving_test shape already checked by _assert_collectible;
    # here: must pass (action was prevented)
    r = _run_pytest(repo_root, ["-q", ppt])
    if r.returncode != 0:
        out.append(
            f"{row.hazard_id}: prevention_proving_test FAILED ({ppt}); "
            f"a passing prevention test is required (A4). "
            f"Snippet:\n{(r.stdout + r.stderr)[-300:]}")
        return out
    # Source must reference the observation resource (not a flag-only detector)
    test_file_rel = ppt.split("::")[0]
    test_src_path = repo_root / test_file_rel
    if not test_src_path.exists():
        out.append(f"{row.hazard_id}: prevention_proving_test file not found: {test_file_rel}")
        return out
    src_text = test_src_path.read_text(encoding="utf-8")
    test_func = ppt.split("::")[-1]
    obs_min6 = [t for t in obs.replace("-", " ").replace(".", " ").split() if len(t) >= 6]
    if not obs_min6:
        out.append(
            f"{row.hazard_id}: prevention_observation has no token of length>=6 to "
            f"anchor an executable reference (got {obs!r}); too vague to verify a "
            f"protected resource was read")
        return out
    if not _obs_in_executable_code(src_text, test_func, obs):
        out.append(
            f"{row.hazard_id}: prevention_proving_test does not reference "
            f"prevention_observation in EXECUTABLE code (comment-only mention "
            f"rejected; the test must read/assert the protected resource's "
            f"post-attempt state). Observation: {obs!r}")
    return out


def _assert_production_gate(repo_root: Path, row) -> list[str]:
    """C-5 (trio verdict, hz-adr-silent-edit-scoped): for an execution_time
    prevention green, the neutered decision point must be PRODUCTION code on the
    resource's pre-action path -- not a test-owned gate. Mechanical rule:
      (a) the check's module is a non-test module inside the shipped tree
          (path not under a tests/ dir; module name does not start with 'test');
      (b) the prevention test drives the production entrypoint (a subprocess run of
          the module, or a call to its main()) and does NOT itself call the bare
          predicate and branch on its return value;
      (c) the neuter rewrites the production symbol's body -- satisfied by
          construction because mitigating_check IS the neutered symbol.
    Returns [] when (a)-(c) hold; a 'C-5(a)'/'C-5(b)'/'C-5-undecidable' violation
    otherwise. NOTE: not wired into validate_green_row in 1c-B; its consumer is
    control F-1.1 in Plan 1c-C, where hz-adr-silent-edit greens."""
    out: list[str] = []
    if "." not in row.mitigating_check:
        return [f"{row.hazard_id}: C-5-undecidable -- mitigating_check is not module.func"]
    mod_name, func = row.mitigating_check.rsplit(".", 1)

    # (a) non-test module inside the shipped tree
    rel = mod_name.replace(".", "/") + ".py"
    src_file = repo_root / rel
    parts = mod_name.split(".")
    if any(p == "tests" or p.startswith("test") for p in parts) or not src_file.exists():
        out.append(f"{row.hazard_id}: C-5(a) -- mitigating_check '{row.mitigating_check}' is "
                   f"not a non-test production module (must live outside tests/ in the "
                   f"shipped tree); test-local decision points are inadmissible")
        return out

    # (b) prevention test drives the production entrypoint, not a test-owned gate
    ppt = row.prevention_proving_test
    if not ppt or ppt in ("", "n/a"):
        return [f"{row.hazard_id}: C-5-undecidable -- no prevention_proving_test to inspect"]
    test_rel = ppt.split("::")[0]
    test_func = ppt.split("::")[-1]
    test_path = repo_root / test_rel
    if not test_path.exists():
        return [f"{row.hazard_id}: C-5-undecidable -- prevention test file not found: {test_rel}"]
    try:
        tree = ast.parse(test_path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"{row.hazard_id}: C-5-undecidable -- SyntaxError in prevention test: {exc}"]
    fnode = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == test_func:
            fnode = n
            break
    if fnode is None:
        return [f"{row.hazard_id}: C-5-undecidable -- prevention test function {test_func} "
                f"not found in {test_rel}"]
    calls_predicate_directly = False
    drives_entrypoint = False
    for n in ast.walk(fnode):
        if isinstance(n, ast.Call):
            # direct bare-predicate call: synthcheck.should_block(...) or should_block(...)
            if isinstance(n.func, ast.Attribute) and n.func.attr == func:
                calls_predicate_directly = True
            if isinstance(n.func, ast.Name) and n.func.id == func:
                calls_predicate_directly = True
            # entrypoint: a subprocess run, or a call to main()
            if isinstance(n.func, ast.Attribute) and n.func.attr in ("run", "Popen", "check_output", "main"):
                drives_entrypoint = True
            if isinstance(n.func, ast.Name) and n.func.id == "main":
                drives_entrypoint = True
    if calls_predicate_directly:
        out.append(f"{row.hazard_id}: C-5(b) -- prevention test calls the bare predicate "
                   f"'{func}' and owns the gating branch itself; the suppression must be "
                   f"reached by driving the production entrypoint (subprocess/main()), not "
                   f"a test-local if (the test-owned gate bites circularly)")
        return out
    if not drives_entrypoint:
        out.append(f"{row.hazard_id}: C-5(b) -- prevention test does not drive the production "
                   f"entrypoint (no subprocess run of the module nor main() call detected); "
                   f"cannot confirm suppression flows through production code")
        return out
    # (c) holds by construction: mitigating_check is the symbol the neuter rewrites.
    return out


def _assert_freshness_decl(repo_root: Path, row) -> list[str]:
    iv = row.revalidation_interval_days
    if iv is None:
        return [f"{row.hazard_id}: green row missing revalidation_interval_days"]
    cap = 7 if row.refusal_critical else 90
    if iv < 1 or iv > cap:
        return [f"{row.hazard_id}: revalidation_interval_days {iv} out of bounds (max {cap})"]
    return []


def validate_green_row(repo_root: Path, row) -> list[str]:
    violations: list[str] = []
    violations += _assert_importable(repo_root, row)
    violations += _assert_binding_identity(repo_root, row)  # NEW (A.4)
    violations += _assert_collectible(repo_root, row)
    violations += _assert_return_contract(repo_root, row)   # NEW (A.3)
    violations += _assert_bite(repo_root, row)
    if not violations:
        violations += _assert_neuter_probe(repo_root, row)
        violations += _assert_prevents(repo_root, row)   # A.6 (step 4b)
    violations += _assert_wiring(repo_root, row)
    violations += _assert_gate_mode(row)               # A.7
    violations += _assert_distance(row)                # A.8 (step 5)
    violations += _assert_strength_layer(repo_root, row)
    violations += _assert_freshness_decl(repo_root, row)
    return violations
