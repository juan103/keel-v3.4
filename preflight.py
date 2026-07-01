"""
Preflight checks. Run this before any work session.

Rules:
- Each check is a function that raises AssertionError on failure.
- Checks accumulate as phases progress — old phases' invariants stay here.
- This file is updated when a phase introduces a new invariant the system must preserve.
- Prefer code that runs over prose in CLAUDE.md asking the agent to remember a rule.

v3.3 modes:
- (no flags)     session mode: all checks; reachability probes use a cached
                 pass (<24h) and degrade to warnings on failure, so offline
                 sessions and commits are not blocked by network state.
- --strict       ratification mode: reachability probes run live and failures
                 FAIL. Run before ratifying any gate and before stamping.
- --compliance   print the CLAUDE.md §0 compliance block, generated
                 mechanically from files on disk, and exit. This replaces the
                 v3.2 procedure where the agent assembled the block by hand
                 (§6 applied to §0: the hand-assembled block could drift or be
                 reconstructed from conversation memory instead of the files).
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import freshness
from hazard_coverage import check_hazard_coverage as _check_hazard_coverage
from log_integrity import detect_first_outcome_log_tampering


# v3.1: reconfigure stdout/stderr to utf-8 so advisory messages containing
# non-ASCII characters (e.g. "->", "≥", "§") don't crash on Windows cp1252
# consoles. `reconfigure` exists on TextIOWrapper since Python 3.7; guard
# defensively in case the stream is detached or wrapped.
for _stream in (sys.stdout, sys.stderr):
    _reconf = getattr(_stream, "reconfigure", None)
    if _reconf is not None:
        try:
            _reconf(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

ROOT = Path(__file__).parent

# v3.3: set by main() from --strict. Session mode (False) is the default.
STRICT = False

# v3.4: tracks checks that ran but issued a [WARN] this session.
# The runner records a fresh pass iff the check ran, did NOT warn, and did NOT raise.
_WARNED: set[str] = set()


def _current_head():
    import subprocess
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                           text=True, check=True, encoding="utf-8", errors="replace")
        return r.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no-git"

REACHABILITY_CACHE = ROOT / ".reachability-cache.json"
REACHABILITY_CACHE_MAX_AGE_S = 24 * 3600


def check_project_structure():
    """The expected scaffolding exists."""
    required = [
        ROOT / "CLAUDE.md",
        ROOT / "goals" / "GOALS.md",
        ROOT / "decisions",
        ROOT / "tests",
        ROOT / "kit-friction.md",
    ]
    missing = [p for p in required if not p.exists()]
    assert not missing, f"Missing required paths: {missing}"


def check_decisions_have_template():
    """The ADR template exists so new decisions can use it."""
    assert (ROOT / "decisions" / "0000-template.md").exists(), \
        "decisions/0000-template.md missing -- new ADRs have no template to follow"


def check_non_determinism_policy_exists():
    """Every project must have a policy on testing non-deterministic output."""
    assert (ROOT / "decisions" / "0001-non-deterministic-testing.md").exists(), \
        "decisions/0001-non-deterministic-testing.md missing -- testing policy unset"


def check_active_phase_exists():
    """At least one phase folder exists with a REQUIREMENTS.md."""
    phase_dirs = sorted(ROOT.glob("goals/phase_*"))
    assert phase_dirs, "No phase folders found in goals/ -- project not initialized"
    latest = phase_dirs[-1]
    assert (latest / "REQUIREMENTS.md").exists(), \
        f"{latest} has no REQUIREMENTS.md"


def check_falsifier_declared():
    """GOALS.md must contain a Falsifier section that's been filled in."""
    goals = (ROOT / "goals" / "GOALS.md").read_text(encoding="utf-8")
    assert "## Falsifier" in goals, "GOALS.md has no Falsifier section"
    # Look for the placeholder text — if it's still there, falsifier wasn't written.
    falsifier_section = goals.split("## Falsifier")[1].split("##")[0]
    assert "[The single experiment" not in falsifier_section, \
        "GOALS.md Falsifier section is still the placeholder. Run the precheck prompt."


def check_falsifier_consistency():
    """Falsifier consistency check (v3.SPINE.A): Layer 1 structural validation +
    Layer 2 narrow GOALS.md prose scan against rejected_prose surface forms.

    Skips silently in Dimension 1 == precheck (no binding ADR in decisions/).
    """
    import binding
    errors = binding.check_falsifier_consistency(ROOT)
    assert not errors, "falsifier consistency:\n  " + "\n  ".join(errors)


def check_frame_validity_audit():
    """Frame validity audit check (Phase 3 M2): each frame_validity binding block
    must reference an existing audit_artifact, carry a non-empty author_verdict,
    and list at least one disposition.

    Skips silently when no frame_validity block is present in decisions/ (mirrors
    check_falsifier_consistency skip behavior so the gate stays green before any
    such block is added).
    """
    import binding
    problems: list[str] = []
    for adr in binding.find_binding_adrs(ROOT):
        try:
            blocks = binding.extract_keel_binding_blocks(adr)
        except ValueError as e:
            problems.append(str(e))
            continue
        for block in blocks:
            if block.get("type") != "frame_validity":
                continue
            block_id = block.get("id", "?")
            # Check 1: audit_artifact file must exist.
            artifact_str = block.get("audit_artifact", "")
            if artifact_str:
                artifact_path = ROOT / artifact_str
                if not artifact_path.exists():
                    problems.append(
                        f"{adr} [{block_id}]: audit_artifact not found: {artifact_str}"
                    )
            else:
                problems.append(
                    f"{adr} [{block_id}]: audit_artifact is missing or empty"
                )
            # Check 2: author_verdict must be a non-empty string.
            verdict = block.get("author_verdict", "")
            if not isinstance(verdict, str) or not verdict.strip():
                problems.append(
                    f"{adr} [{block_id}]: author_verdict is null or empty"
                )
            # Check 3: dispositions must be a non-empty list.
            dispositions = block.get("dispositions", [])
            if not isinstance(dispositions, list) or len(dispositions) == 0:
                problems.append(
                    f"{adr} [{block_id}]: dispositions is empty or missing"
                )
    assert not problems, "frame-validity audit:\n  " + "\n  ".join(problems)


def check_pre_stamp_review_exists():
    """Pre-stamp adversarial-review presence check (v3.SPINE.C). State-aware:
    skip in precheck, warn in pre_stamp, fail in post_stamp.
    """
    import assumptions
    status, message = assumptions.check_pre_stamp_review_exists(ROOT)
    if status == "warn":
        print(f"[WARN] check_pre_stamp_review_exists: {message}")
        return
    assert status != "fail", f"pre-stamp review missing: {message}"


def check_load_bearing_assumptions_closed_at_gate():
    """Refuse ratification when any assumption due at or before current_gate
    is still unverified (v3.SPINE.D). Plus an advisory backward-edit scan.
    """
    import assumptions
    errors = assumptions.check_load_bearing_assumptions_closed_at_gate(ROOT)
    warnings = assumptions.detect_backward_deadline_edits(ROOT)
    for w in warnings:
        print(f"[WARN] {w}")
    assert not errors, (
        "load-bearing assumptions not closed at current gate:\n  "
        + "\n  ".join(errors)
    )


def _read_reachability_cache() -> dict | None:
    try:
        data = json.loads(REACHABILITY_CACHE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _write_reachability_cache(ok: bool) -> None:
    try:
        REACHABILITY_CACHE.write_text(
            json.dumps({"timestamp": time.time(), "ok": ok}) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def check_reachability_probes_pass():
    """Run the probes declared in goals/reachability.md (v3.SPINE.B).
    Skips silently if the file does not exist or has no probes.

    v3.3 scoping: the v3 principle is "probes run at Gate 0, BEFORE any
    pre-registration is stamped" -- not "every commit needs the network".
    Failing preflight on probe failure in session mode meant an offline
    laptop could not commit at all (the pre-commit hook runs preflight).

    - strict mode (--strict, ratification/stamp): probes run live; any
      failure FAILS. Identical to the v3..v3.2 behavior.
    - session mode (default): a cached pass younger than 24h is accepted
      without network I/O. Otherwise probes run live; a pass refreshes the
      cache; failures are surfaced as [WARN] and do NOT fail preflight.
      They MUST pass at ratification (--strict).

    Structural errors in reachability.md (missing required fields, unknown
    probe Type) always FAIL in both modes -- they are file bugs, not
    network state.
    """
    import reachability
    if not (ROOT / "goals" / "reachability.md").exists():
        return
    try:
        probes = reachability.parse_reachability(ROOT)
    except ValueError as e:
        raise AssertionError(str(e)) from e
    if not probes:
        return

    if not STRICT:
        cache = _read_reachability_cache()
        if cache and cache.get("ok"):
            age = time.time() - float(cache.get("timestamp", 0))
            if 0 <= age < REACHABILITY_CACHE_MAX_AGE_S:
                print(
                    f"[NOTE] reachability: cached pass from {age / 3600:.1f}h "
                    f"ago accepted (session mode; --strict runs probes live)"
                )
                return

    errors = reachability.check_reachability_probes_pass(ROOT)
    if not errors:
        _write_reachability_cache(ok=True)
        return

    if STRICT:
        raise AssertionError(
            "reachability probes failed:\n  " + "\n  ".join(errors)
        )

    _write_reachability_cache(ok=False)
    _WARNED.add("check_reachability_probes_pass")
    for e in errors:
        print(f"[WARN] reachability: {e}")
    print(
        "[WARN] reachability probes failing in session mode -- not blocking "
        "this run, but they MUST pass at ratification: python preflight.py --strict"
    )


def check_bug_log_exists():
    """v3.2: BUGS.md exists, every entry's Status is a valid lifecycle state,
    and open bugs are surfaced as warnings at every session start.

    v3.3: entry-based parse. An entry with NO Status line used to pass
    silently (the v3.2 line-scanner only validated statuses it found);
    now it fails -- a bug entry without a lifecycle state is outside the
    §11 protocol.
    """
    bugs_path = ROOT / "BUGS.md"
    assert bugs_path.exists(), \
        "BUGS.md missing -- project bugs have no documented home (v3.2 bug protocol)"
    text = bugs_path.read_text(encoding="utf-8")
    valid = {"open", "diagnosed", "fixed", "wontfix"}
    bad = []
    open_bugs = []
    headers = list(re.finditer(r"^###\s+(BUG-\d+)", text, re.MULTILINE))
    for i, m in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[m.end():end]
        sm = re.search(r"^-\s+\*\*Status:\*\*\s*(\S+)", body, re.MULTILINE)
        if sm is None:
            bad.append(
                f"{m.group(1)}: missing Status line "
                f"(every BUGS.md entry needs one of: {', '.join(sorted(valid))})"
            )
            continue
        status = sm.group(1).strip().lower()
        if status not in valid:
            bad.append(f"{m.group(1)}: invalid status '{status}'")
        elif status == "open":
            open_bugs.append(m.group(1))
    assert not bad, \
        "BUGS.md invalid entries (use open/diagnosed/fixed/wontfix):\n  " \
        + "\n  ".join(bad)
    if open_bugs:
        print(f"[WARN] check_bug_log_exists: open bugs: {', '.join(open_bugs)}")


def check_paradigm_declared():
    """v3.2: goals/PARADIGM.md exists and the Paradigm section has been
    filled in (the paradigm fork is decided once, at project start).
    """
    paradigm_path = ROOT / "goals" / "PARADIGM.md"
    assert paradigm_path.exists(), \
        "goals/PARADIGM.md missing -- preferred paradigm undeclared (v3.2)"
    text = paradigm_path.read_text(encoding="utf-8")
    assert "## Paradigm" in text, "goals/PARADIGM.md has no '## Paradigm' section"
    section = text.split("## Paradigm")[1].split("##")[0]
    assert "[Declare the preferred paradigm" not in section, \
        "goals/PARADIGM.md Paradigm section is still the placeholder. Declare it."


def check_kit_version_declared():
    """v3.4 Phase 2b (hz-kit-not-versioned): the kit declares a machine-readable
    version in VERSION that matches CLAUDE.md's '**KEEL kit version: X**' line."""
    import re as _re
    vpath = ROOT / "VERSION"
    assert vpath.exists(), "VERSION file missing -- kit version not machine-readable (hz-kit-not-versioned)"
    version = vpath.read_text(encoding="utf-8").strip()
    assert version and not version.startswith("[") and version.lower() != "tbd", \
        f"VERSION is a placeholder/empty: {version!r}"
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    m = _re.search(r"\*\*KEEL kit version:\s*([0-9][0-9.]*)\*\*", claude)
    assert m, "CLAUDE.md has no '**KEEL kit version: X**' declaration to cross-check"
    assert m.group(1) == version, \
        f"VERSION ({version}) disagrees with CLAUDE.md ({m.group(1)})"


def check_ci_matrix_declared():
    """v3.4 Phase 2b (hz-no-ci-matrix): a CI workflow defines the Windows x
    3.11/3.12/3.13 matrix with no continue-on-error and a release/push trigger.
    Tolerant token scan (no yaml dependency); the workflow DEFINITION is the
    green basis -- run_ci_matrix.py is the real-CI runner, not the local gate."""
    wf = ROOT / ".github" / "workflows" / "kit-ci.yml"
    assert wf.exists(), "no .github/workflows/kit-ci.yml -- CI matrix undeclared (hz-no-ci-matrix)"
    text = wf.read_text(encoding="utf-8")
    missing = [v for v in ("3.11", "3.12", "3.13") if v not in text]
    assert not missing, f"kit-ci.yml omits Python version(s): {', '.join(missing)}"
    assert "windows-latest" in text, "kit-ci.yml has no windows-latest runner"
    import re as _re
    assert _re.search(r"(?m)^\s*(push|pull_request|release)\s*:", text), \
        "kit-ci.yml has no push/pull_request/release trigger"
    assert "continue-on-error" not in text, \
        "kit-ci.yml carries continue-on-error -- a failing matrix leg would not block"


def check_adr_immutability():
    """v3.3: accepted ADRs must not have changed since their acceptance
    commit, outside the legitimately-mutable parts (the `## Errata` section
    and the `**Status:**` line's accepted->superseded transition).

    CLAUDE.md §7 declared this rule since v2; until v3.3 it was prose-only
    -- the single most load-bearing rule in the kit (binding metadata,
    stamping, and the fork protocol all rest on ADR immutability) had no
    mechanical guard. Skips silently when the project is not a git repo.
    """
    import adr_guard
    errors = adr_guard.detect_adr_mutations(ROOT)
    assert not errors, (
        "accepted ADRs mutated since acceptance (CLAUDE.md §7):\n  "
        + "\n  ".join(errors)
    )


def check_hazard_coverage():
    """v3.4: hazard-coverage spine — audit pin + no-orphan/no-downgrade +
    red-state/baseline discipline (refusal-critical rows must be on the
    Phase-0 pending baseline while pending; green rows must have a wired
    falsifier before the Phase-1 green-row assertions land)."""
    try:
        errors = _check_hazard_coverage(ROOT)
    except (FileNotFoundError, ValueError) as exc:
        raise AssertionError(
            f"hazard coverage: missing or malformed artifact -- {exc}"
        ) from exc
    assert not errors, (
        "hazard coverage violations:\n  " + "\n  ".join(errors)
    )


def emit_adr_index(repo_root=ROOT):
    """v3.4: one line per ADR (the section-0 emitter pattern applied to
    orientation). Reading this index replaces reading every ADR each session
    (hz-orientation-cost). Format: ADR-NNNN  [Status]  <title>."""
    import re as _re
    decisions = repo_root / "decisions"
    if not decisions.is_dir():
        print("(no decisions/ directory)")
        return
    for md in sorted(p for p in decisions.rglob("*.md") if _re.match(r"\d{4}-", p.name)):
        num = md.name[:4]
        text = md.read_text(encoding="utf-8")
        status_m = _re.search(r"^\*\*Status:\*\*\s*(.+?)\s*$", text, _re.M)
        title_m = _re.search(r"^#\s+(.+)$", text, _re.M)
        status = (status_m.group(1).strip() if status_m else "?")[:24]
        title = (title_m.group(1).strip() if title_m else md.stem)
        print(f"ADR-{num}  [{status}]  {title}")


def check_adr_index():
    """v4 (falsifier_strength: full, falsifier_layer: post_hoc):
    fails if any decisions/**/NNNN-*.md is absent from the emitted index."""
    import io, re as _re, contextlib
    decisions = ROOT / "decisions"
    expected = {p.name[:4] for p in decisions.rglob("*.md") if _re.match(r"\d{4}-", p.name)} if decisions.is_dir() else set()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        emit_adr_index(ROOT)
    emitted = set(_re.findall(r"ADR-(\d{4})", buf.getvalue()))
    missing = sorted(expected - emitted)
    assert not missing, f"ADR index omits: {', '.join('ADR-'+m for m in missing)}"


def check_first_outcome_log_integrity():
    """v4 (partial/post_hoc): tamper-evidence on the red-green log (hz-vacuous-test)."""
    errors = detect_first_outcome_log_tampering(ROOT)
    assert not errors, "first-outcome log tampering:\n  " + "\n  ".join(errors)


def check_author_fill_contamination():
    """v3.4 Phase 2a: every runtime_role=author field with a value must carry a
    valid attestation token (v_final). raises on any unattested/forged author-fill.
    Conformance-level; the green is gated on a live commitment-lock + owner
    attestation (deferred), so this check today fails-closed only on real fixtures
    and is vacuous-pass on a kit with no author fields (the row is conditional)."""
    import runtime_roles, attest, json as _json
    strict = STRICT
    fields = runtime_roles.load_sidecar(ROOT)
    log = {}
    lp = ROOT / "goals" / ".attest-log.json"
    if lp.exists():
        log = _json.loads(lp.read_text(encoding="utf-8"))
    tokens = log.get("tokens", [])
    registry = {}
    rp = ROOT / "goals" / ".attest-keys.json"
    if rp.exists():
        registry = _json.loads(rp.read_text(encoding="utf-8"))
    secrets = {}
    sp = ROOT / "goals" / ".attest-secrets.json"
    if sp.exists():
        secrets = _json.loads(sp.read_text(encoding="utf-8"))
    problems = []
    for f in fields:
        if f.get("role") != "author":
            continue
        try:
            value = runtime_roles.extract_value(ROOT, f["artifact"], f["locator"])
        except ValueError as e:
            problems.append(f"{f['artifact']}::{f['field']}: locator error: {e}")
            continue
        if not value:
            continue
        matching = [t for t in tokens
                    if t.get("artifact") == f["artifact"] and t.get("field") == f["field"]]
        if not matching:
            problems.append(f"{f['artifact']}::{f['field']}: no-token (unattested author-fill)")
            continue
        tok = matching[-1]  # most-recent record only
        secret = secrets.get(tok.get("actor"))
        errs, adv = attest.verify_token(
            tok, f["artifact"], f["field"], value, registry, secret,
            lambda ts: attest._is_ancestor(ROOT, ts))
        if errs:
            problems.append(f"{f['artifact']}::{f['field']}: {errs[0]}")
        elif "hmac-unverified-secret-absent" in adv:
            if strict:
                problems.append(
                    f"{f['artifact']}::{f['field']}: hmac-unverifiable-secret-absent (strict)")
            else:
                print(f"[WARN] check_author_fill_contamination: HMAC unverified (secret absent) for {f['artifact']}::{f['field']}")
                _WARNED.add("check_author_fill_contamination")
    # Conditional-deferred check: if hz-runtime-role-unannotated is conditional, the
    # deferred-green discipline applies -- no-token (unattested) problems WARN (not block),
    # but real forgeries (value-changed, forged-hmac, malformed, bad-provenance, etc.) FAIL.
    try:
        from hazard_coverage import parse_matrix
        _hz_row = next(
            (r for r in parse_matrix(ROOT) if r.hazard_id == "hz-runtime-role-unannotated"),
            None)
        _conditional = bool(_hz_row) and _hz_row.status == "conditional"
    except (FileNotFoundError, ValueError):
        _conditional = False
    if _conditional:
        soft = [p for p in problems if "no-token" in p]
        hard = [p for p in problems if "no-token" not in p]
        for p in soft:
            print(
                "[WARN] check_author_fill_contamination: author-fill fence declared, "
                "green deferred (conditional): " + p)
            _WARNED.add("check_author_fill_contamination")
        assert not hard, "author-fill contamination:\n  " + "\n  ".join(hard)
    else:
        assert not problems, "author-fill contamination:\n  " + "\n  ".join(problems)


def check_hooks_installed():
    """v4 (partial/post_hoc): assert .claude/settings.json wires the
    SessionStart compliance hook and the PreToolUse accepted-ADR guard
    (converts the A-hooks-installed assumption into a falsifier). Session
    mode WARNs; --strict FAILs. The runtime-firing half is the hook-firing
    smoke test in tests/kit/test_hooks_installed.py (execution_time)."""
    settings = ROOT / ".claude" / "settings.json"
    problems = []
    if not settings.exists():
        problems.append(".claude/settings.json not installed (run install_hooks.sh)")
    else:
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append(f".claude/settings.json is not valid JSON: {e}")
            data = {}
        hooks = (data.get("hooks") or {})
        ss_cmds = [h.get("command", "") for grp in hooks.get("SessionStart", [])
                   for h in (grp.get("hooks") or [])]
        if not any("preflight.py --compliance" in c for c in ss_cmds):
            problems.append("SessionStart hook does not run 'preflight.py --compliance'")
        pt_groups = hooks.get("PreToolUse", [])
        pt_ok = any(
            ("Edit" in (grp.get("matcher", "")) or "Write" in (grp.get("matcher", "")))
            and any("protect_adrs.py" in h.get("command", "") for h in (grp.get("hooks") or []))
            for grp in pt_groups)
        if not pt_ok:
            problems.append("PreToolUse hook does not guard accepted ADRs (protect_adrs.py on Edit|Write)")
    if problems:
        msg = "hooks not installed/wired:\n  " + "\n  ".join(problems)
        if STRICT:
            raise AssertionError(msg)
        _WARNED.add("check_hooks_installed")
        print(f"[WARN] check_hooks_installed: {msg}")


def check_pilot_phase():
    """v3.4 Phase 3 M3 (hz-pilot-phase-unexpressible): at ship time every
    pilot_phase binding block must be pilot_pending with no stale/malformed
    run record (detect-don-t-pretend -- the gate fires post-release over real
    elapsed time, never at ship time). Skips silently when no pilot_phase block
    is present in decisions/."""
    import binding
    import pilot as _pilot
    pilot_blocks: list[dict] = []
    for adr in binding.find_binding_adrs(ROOT):
        try:
            blocks = binding.extract_keel_binding_blocks(adr)
        except ValueError:
            continue
        for block in blocks:
            if block.get("type") == "pilot_phase":
                pilot_blocks.append(block)
    if not pilot_blocks:
        return  # skip-clean: no pilot_phase block in decisions/
    problems: list[str] = []
    for block in pilot_blocks:
        block_id = block.get("id", "?")
        # Ship-time assertion: status MUST be pilot_pending.
        status = block.get("status")
        if status != "pilot_pending":
            problems.append(
                f"{block_id}: expected pilot_pending at ship time, got {status!r} "
                f"(the gate fires post-release; never claim pilot_pass at ship time)"
            )
        # If a run record exists, validate it (fail closed).
        rp = _pilot.record_path(ROOT, block)
        if rp.exists():
            errs = _pilot.check_pilot_record(ROOT, block)
            problems.extend(errs)
    assert not problems, "pilot-phase check:\n  " + "\n  ".join(problems)


def check_commitment_lock():
    """v3.4 Phase 3 M1 (hz-runtime-role-unannotated precondition #1): the locked
    surface (preflight_sha, registered_checks, goals_sections, refusal_critical_rows,
    attest_keys_sha, runtime_roles_sha) must match the committed snapshot in
    goals/.commitment-lock.json.  Refusal-critical divergences always fail (GP-5);
    non-critical divergences require an accepted lock-override ADR."""
    import commitment_lock
    problems = commitment_lock.check_commitment_lock_impl(ROOT)
    assert not problems, "commitment lock:\n  " + "\n  ".join(problems)


def check_falsifier_freshness():
    """v4: per-check revalidation freshness (hz-green-rotting). Session WARNs;
    --strict FAILs. Records are written by the runner on each check's pass.

    Causal self-healing: this check reads PRIOR-run records. On the FIRST
    preflight run after this feature is added there are no records yet, so it
    WARNs (session) or FAILs (--strict). On the SECOND run, records exist and
    HEAD matches, so no violation fires. Any commit changes HEAD; the cached
    records from the pre-commit run then have a stale head. To recover:
    run 'py preflight.py' once (refreshes .checks-cache.json to the committed
    HEAD), then 'py preflight.py --strict' passes cleanly."""
    errors = freshness.check_falsifier_freshness_impl(ROOT, STRICT, time.time(), _current_head())
    if errors:
        msg = "stale/unrecorded checks:\n  " + "\n  ".join(errors)
        if STRICT:
            raise AssertionError(msg)
        _WARNED.add("check_falsifier_freshness")
        print(f"[WARN] check_falsifier_freshness: {msg}")


# Add new checks here as the project grows.
# Each phase's invariants accumulate. Do not remove old checks unless a
# decision (ADR) explicitly supersedes them.


# ---------------------------------------------------------------------------
# v3.3: --compliance — mechanical CLAUDE.md §0 block
# ---------------------------------------------------------------------------


def _first_paragraph(section: str) -> str | None:
    """First non-empty paragraph of a section body (blank-line delimited)."""
    for para in re.split(r"\n\s*\n", section):
        para = para.strip()
        if para:
            return para
    return None


def _find_falsifier_test() -> str | None:
    """Locate the executable falsifier check.

    Preference order:
    1. A behavioral keel-binding block's `test` field (the binding ADR names
       the test path explicitly).
    2. A `def test_*falsifier*` function in tests/test_*.py.
    """
    import binding
    for adr in binding.find_binding_adrs(ROOT):
        try:
            blocks = binding.extract_keel_binding_blocks(adr)
        except ValueError:
            continue
        for block in blocks:
            test = block.get("test")
            if block.get("type") == "behavioral" and isinstance(test, str) and test.strip():
                return test.strip()
    for tf in sorted(ROOT.glob("tests/test_*.py")):
        try:
            text = tf.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        m = re.search(r"^\s*def\s+(test_\w*falsifier\w*)\s*\(", text, re.MULTILINE)
        if m:
            return f"tests/{tf.name}::{m.group(1)}"
    return None


def _format_binding_block(adr: Path, block: dict) -> str:
    rel = adr.relative_to(ROOT).as_posix()
    parts = [f"id={block.get('id', '?')}", f"type={block.get('type', '?')}"]
    if block.get("type") == "statistical_inference":
        for field in ("statistic", "null", "alpha", "p_value"):
            parts.append(f"{field}={block.get(field, '?')}")
    elif block.get("type") == "behavioral":
        for field in ("behavior", "test"):
            parts.append(f"{field}={block.get(field, '?')}")
    return f"{rel}: " + " ".join(str(p) for p in parts)


def emit_compliance_block():
    """Print the §0 compliance block, generated from files on disk.

    The agent's §0 duty in v3.3 is: run this, paste the output verbatim,
    and add the one-line read confirmation. The content can no longer
    drift from the files or be reconstructed from conversation memory.
    """
    import binding
    import state

    print("COMPLIANCE (mechanical, generated by preflight.py --compliance):")

    try:
        st = state.detect(ROOT)
        print(
            f"  State: {st['dimension_1']}; current gate {st['current_gate']}; "
            f"active phase {st['active_phase']}"
        )
    except Exception as e:  # state detection must never block the block
        print(f"  State: detection failed ({type(e).__name__}: {e})")

    goals_path = ROOT / "goals" / "GOALS.md"
    if not goals_path.exists():
        print("  The project is in Phase 0 -- no GOALS yet.")
        return

    goals_text = goals_path.read_text(encoding="utf-8")
    section = binding._extract_section(goals_text, "Falsifier")
    if section is None:
        print(
            "  Falsifier (GOALS.md prose): MISSING -- GOALS.md has no "
            "## Falsifier section. Fix this before any work proceeds."
        )
    else:
        para = _first_paragraph(section)
        if para is None:
            print(
                "  Falsifier (GOALS.md prose): EMPTY -- the ## Falsifier "
                "section has no content. Fix this before any work proceeds."
            )
        else:
            lines = para.splitlines()
            print(f"  Falsifier (GOALS.md prose): {lines[0]}")
            for ln in lines[1:]:
                print(f"    {ln.strip()}")
            if "[The single experiment" in section:
                print(
                    "    (STILL THE PLACEHOLDER -- run the precheck prompt "
                    "before any work proceeds)"
                )

    adrs = binding.find_binding_adrs(ROOT)
    if not adrs:
        print("  Binding metadata: no binding ADR yet")
    else:
        for adr in adrs:
            try:
                blocks = binding.extract_keel_binding_blocks(adr)
            except ValueError as e:
                print(f"  Binding metadata: PARSE ERROR -- {e}")
                continue
            for block in blocks:
                print(f"  Binding metadata: {_format_binding_block(adr, block)}")

    falsifier_test = _find_falsifier_test()
    print(f"  Executable check at: {falsifier_test or 'not yet implemented'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="KEEL preflight checks (v3.3)")
    parser.add_argument(
        "--compliance",
        action="store_true",
        help="print the CLAUDE.md §0 compliance block from files on disk and exit",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "ratification mode: reachability probes run live and failures "
            "FAIL (session mode caches passes for 24h and warns on failure)"
        ),
    )
    parser.add_argument("--adr-index", action="store_true",
                        help="emit one line per ADR (orientation index) and exit")
    args = parser.parse_args(argv)

    global STRICT
    STRICT = args.strict
    _WARNED.clear()

    if args.compliance:
        emit_compliance_block()
        return

    if args.adr_index:
        emit_adr_index()
        return

    checks = [
        check_project_structure,
        check_decisions_have_template,
        check_non_determinism_policy_exists,
        check_active_phase_exists,
        check_falsifier_declared,
        check_falsifier_consistency,
        check_frame_validity_audit,
        check_pre_stamp_review_exists,
        check_load_bearing_assumptions_closed_at_gate,
        check_reachability_probes_pass,
        check_bug_log_exists,
        check_paradigm_declared,
        check_kit_version_declared,
        check_ci_matrix_declared,
        check_adr_immutability,
        check_hazard_coverage,
        check_adr_index,
        check_first_outcome_log_integrity,
        check_hooks_installed,
        check_author_fill_contamination,
        check_commitment_lock,
        check_pilot_phase,
        check_falsifier_freshness,
    ]

    _head_cache = _current_head()
    failed = []
    for check in checks:
        try:
            check()
            print(f"[OK]   {check.__name__}")
            # Record a fresh pass iff: ran this session, did NOT warn, and is not
            # check_falsifier_freshness (which reads prior-run records, not its own).
            if check.__name__ != "check_falsifier_freshness" and check.__name__ not in _WARNED:
                freshness.record_pass(ROOT, check.__name__, _head_cache)
        except AssertionError as e:
            print(f"[FAIL] {check.__name__}: {e}")
            failed.append(check.__name__)
            freshness.invalidate(ROOT, check.__name__)

    if failed:
        print(f"\nPreflight FAILED: {len(failed)} check(s) failed")
        sys.exit(1)
    else:
        print("\nPreflight OK" + (" (strict)" if STRICT else ""))


if __name__ == "__main__":
    main()
