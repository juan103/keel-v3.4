"""Builds a throwaway fixture kit so the green-row engine can be tested
against synthetic green rows without touching the real matrix."""
import shutil
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]  # keel_v3.4/

_MATRIX_HEADER = (
    "| hazard_id | audit_hazard_ref | refusal_critical | mitigating_check | "
    "check_return_contract | "
    "falsifier_strength | falsifier_layer | proving_test_negative | "
    "proving_test_positive | prevention_proving_test | prevention_observation | "
    "exercise_scenario | wired_into | gate_mode | "
    "revalidation_interval_days | status | silent_path_defense_distance | "
    "substantive_residue | roadmap_defense_distance | independence_basis | notes |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")


def build_fixture(tmp_path, *, check_body, neg_body, pos_body,
                  refusal_critical=False, layer="post_hoc",
                  strength="full", interval=7, wired="ci",
                  hazard_id="hz-synth", audit_ref="n/a",
                  roadmap_defense_distance=1, independence_basis="n/a",
                  check_return_contract="findings_list",
                  prevention_proving_test="n/a",
                  prevention_observation="n/a",
                  gate_mode="n/a",
                  check_module_src=None,
                  synth_test_src=None,
                  prevention_test_body=None,
                  preflight_src=None,
                  silent_path_defense_distance=None):
    """Build a synthetic fixture root.
    - check_module_src: full synthcheck.py source (overrides check_body)
    - synth_test_src: full tests/test_synth.py source (overrides neg_body/pos_body);
      use for zero-arg / ROOT-global / monkeypatch-driven proving tests.
    - prevention_test_body: if provided, writes tests/test_prevention.py
    - preflight_src: if provided, writes preflight.py in the fixture root
    """
    root = tmp_path / "fix"
    (root / "goals").mkdir(parents=True)
    (root / "tests").mkdir()
    shutil.copy(REAL / "goals" / "audit-v3.3.md", root / "goals" / "audit-v3.3.md")
    shutil.copy(REAL / "goals" / ".audit-lock.json", root / "goals" / ".audit-lock.json")
    shutil.copy(REAL / "goals" / ".pending-baseline.json", root / "goals" / ".pending-baseline.json")
    if check_module_src is not None:
        (root / "synthcheck.py").write_text(check_module_src, encoding="utf-8")
    else:
        (root / "synthcheck.py").write_text(
            f"def synth_check(repo_root):\n{_indent(check_body)}\n", encoding="utf-8")
    if synth_test_src is not None:
        (root / "tests" / "test_synth.py").write_text(synth_test_src, encoding="utf-8")
    else:
        (root / "tests" / "test_synth.py").write_text(
            "import sys; from pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
            "from synthcheck import synth_check\n"
            f"def test_neg():\n{_indent(neg_body)}\n"
            f"def test_pos():\n{_indent(pos_body)}\n", encoding="utf-8")
    if prevention_test_body is not None:
        (root / "tests" / "test_prevention.py").write_text(
            prevention_test_body, encoding="utf-8")
    if preflight_src is not None:
        (root / "preflight.py").write_text(preflight_src, encoding="utf-8")
    rc = "true" if refusal_critical else "false"
    if silent_path_defense_distance is None:
        spdd = "1" if refusal_critical else "n/a"
    else:
        spdd = str(silent_path_defense_distance)
    row = (f"| {hazard_id} | {audit_ref} | {rc} | synthcheck.synth_check | "
           f"{check_return_contract} | "
           f"{strength} | {layer} | tests/test_synth.py::test_neg | "
           f"tests/test_synth.py::test_pos | {prevention_proving_test} | {prevention_observation} | "
           f"n/a | {wired} | {gate_mode} | {interval} | green | "
           f"{spdd} | n/a | {roadmap_defense_distance} | {independence_basis} | synthetic |\n")
    (root / "goals" / "hazard-coverage.md").write_text(
        "# fixture\n\n" + _MATRIX_HEADER + row, encoding="utf-8")
    return root


def _indent(body):
    return "\n".join("    " + ln for ln in body.strip("\n").splitlines())
