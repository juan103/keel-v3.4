# CHANGELOG — KEEL v3.4

**v3.4: the version that closes the refusal-critical gaps the v3.3 Atlas self-audit named —
no more, and no less.** This is the closure narrative; it is also the artifact the Phase-4
panel reviews. It is written to be honest about exactly what v3.4 proves and what it does not.

## The claim v3.4 ships

Bounded internal coherence plus short-burst AI-adversary pressure, with the external-fidelity
gap named (§8), mechanically un-forgettable, scheduled (the `pilot_phase` gate), and ledgered.
Concretely: every refusal-critical hazard the v3.3 self-audit found has a **wired, executed,
joint-biting check** with a falsifier that genuinely fails when the check is neutered; **no
refusal-critical row greens dishonestly**; and the kit can now be **exercised against a live AI
adversary** (the Phase-3.5 harness), with the live-fidelity residue named, not hidden.

**Headline (honest): 0 of 7 refusal-critical hazards are *executably closed* (`execution_time`
`d≥1`).** 5 non-critical detector rows are green; 4 refusal-critical rows are `conditional`
(mechanism specified + in-boundary-proven, the closure gate pending). This 0/7 is not a failure
to report — it is the honest accounting the kit is built to keep: the refusal-critical hazards
rest on gate-integrity assumptions a self-hosted conformance kit cannot self-certify, so they are
held at their honest layer rather than greened.

## What changed, by tier

**Tier 1 (mechanical).** The hazard-coverage matrix spine + the green-row validation engine
(a row greens only if neutering its check makes the proving test fail); `--adr-index`;
first-outcome-log tamper-evidence; hooks-installed smoke; falsifier freshness (causal + bounded).
Greened 2 non-critical detector rows. `hz-adr-silent-edit` held **pending** (no client-side
barrier closes the Bash channel; ADR-0004).

**Tier 2 (feature).** `runtime_role` + `attest.py` (HMAC author-fill attestation, stdlib-only,
secrets never in git); `check_author_fill_contamination`. The author-fill row is `conditional`,
with four named residues (co-located-credential, self-registration, gate-integrity,
fresh-sign) — never counted as covered. Kit-versioning + CI-matrix → 2 more non-critical greens.

**Tier 3 (detect-don't-pretend).** `frame_validity` + `pilot_phase` binding shapes; the live
`commitment_lock` guard (broadened locked surface incl. `preflight.py`; head-vs-merge-base;
GP-5 no-auto-trust). Greened the non-critical `hz-pilot-phase-unexpressible`. Per the trio
v_final, the three refusal-critical Tier-3 rows (`hz-compliance-gameable`,
`hz-conversational-relaxation`, `hz-frame-validity-unexpressible`) are `conditional`, NOT green;
the gate-integrity / boundary residue is named and routed to the live exercise (F7) + a v3.5
non-bypassable interlock. ADR-0005.

**Tier 4 / the live-exercise harness (Phase 3.5).** `adversarial_exercise.py` + the differential-
observability gate (F1: a 4-cell truth table + 3 controls — surgical AST-anchored weakening,
relocation invariance, execution-binding via an independent replication runner), generalized to
**7 of 8** refusal-critical scenarios (1 honestly cut: `ax-reachability`, inherently live, not
tree-expressible). Anti-circularity hardening: rule-derived projection (content-hash +
decode-normalization + path-rules + env-scrub + per-scenario keep-overrides), the F3 leak
falsifier, the append-only ledger, transitive import-disjointness, the lexical oracle scan,
detector-recall route-liveness. The pinned `goals/.harness-contract.json` + a `report.json` with
**11 mandatory printed residues** — the honest boundary, *in print*, between in-boundary
instrument validation (proven) and live-agent faithfulness / provocation / recall-adequacy /
the CI-boundary F7 (Phase 4). Gate 3.5 (full) ratified.

## What v3.4 proves — and does NOT

**Proves:** each modeled refusal-critical hazard has a wired, executed, joint-biting check whose
named function provably runs against its fixture; no refusal-critical hazard is unguarded at
execution time on its *silent (non-tampering)* escape path; and — for the 7 eligible scenarios —
the harness is a genuine instrument (sensitive, specific, execution-bound, not gamed), with the
Phase-4 pilot demonstrating a live AI agent takes the silent escape and the named check catches
it on the live result.

**Does NOT prove:** that the kit is "safe"; that the checks catch every real instance; that the
authored scenarios are exhaustive or faithful to operational reality; that the short-burst
exercise speaks to long-horizon dynamics; that a more capable adversary could not find an
uncaught path; or that the gate runs un-tampered against an adversary who controls the
environment. These are the §8 external-validation residual + the named per-mechanism residues.

## Named residuals (carried, not closed)
- **§8 external-validation monoculture** (`accepted-risk`, `load-bearing-assumptions.md`):
  the hazards/fixtures/scenarios may be coherent shadows of the same taxonomy; resolution is
  scheduled at the `pilot_phase` gate (real non-self-authored usage), not performed in v3.4.
- **Gate-integrity / `execution_time`-vs-`post_hoc`** (the 4 conditional rows): the named checks
  assume preflight is run and un-tampered; the honest label is carried, resolved empirically by
  the live F7 exercise (Phase 4) + a v3.5 non-bypassable interlock.
- **Harness fidelity** (the 11 report residues): observable-faithfulness, live-noise realism, the
  who-checks-the-runner regress, the self-hosted-vocab-overlap of the lexical scan, the
  narrow-import-hygiene of the disjointness check, and the live-agent fidelity (the subagent is
  not truly sandboxed; "my subagent" is not provably "an operational auto-mode agent").

## Closure (Phase 4) — what was run, and the F7 DOWNGRADE (2026-06-30)
The live adversarial-exercise gate (F7) was run live at N=10 opus on two scenarios
(ax-runtime-role, ax-frame-validity). **It does NOT close the 4 refusal-critical `conditional`
rows.** Full record: `docs/superpowers/keel-v3.4-phase4-F7-finding.md`. In short:

- **F7 cannot be run check-blind in this environment (VERIFIED).** A Phase-0 adversarial probe
  proved Agent-tool subagents always root at the full repo; the scenario's own answer key
  (`named_check.py` / `escape_detector.py`) is reachable by absolute path / `Glob` / `Grep`. It
  materialized: 2/10 ax-frame-validity opus agents read the check sources. The trio v0.3 panel
  (run on this exact question) ruled "name the leak and continue" **cannot** claim "conservative
  under leakage" (reading the detector teaches detector-evasion), and the isolated re-run it
  mandated is Phase-0-verified infeasible here. Per the panel: *a gate that cannot be made blind
  cannot be defended by "we'll just make it blind."*
- **What the run DID establish (instrument validation, not closure):** the named checks catch the
  modeled silent escapes when taken — ax-runtime-role 10/10, ax-frame-validity 7/7 under the
  **production** check, 0 uncaught escapes; plus one clean orientation-layer refusal (CLAUDE.md §7
  + `adr_guard.py`). This credit is **bounded** (per the closure panel): the "0 uncaught" result is
  conservative *only while the detector is sound* — BUG-001 is a demonstrated exception channel —
  and it is internal-consistency, **not** external evidence that the checks' catches correspond to
  the real refusal-critical failure mode (that correspondence is named standing accepted-risk).
- **Detector findings:** trial-3's `PENDING` slipped the F1-*narrowed* scenario check but is caught
  by the production check (a fixture-fidelity artifact, not a live escape); and a constructed
  placeholder-verdict gap in the production check itself (BUG-001) — both named, the fix flagged
  for owner ratification (refusal-critical + locked-surface + a vocabulary fork).
- **Demonstrated (no longer theoretical) residues:** live-exercise non-blindness, detector
  completeness, fixture fidelity. The properly-isolated, blind F7 harness is specced (trio panel
  v4 proposal) and scheduled for v3.5; it is **not** executed in v3.4.

**Headline unchanged: 0 of 7 refusal-critical hazards executably closed** — now with *demonstrated*
reasons why F7 does not lift the 4 conditional rows. Still remaining: the mandatory Atlas auditor
re-run (as-built), the Phase-4 trio closure panel on this CHANGELOG, the owner `author_verdict` +
attestation, and owner ratification.

## Lineage
v3.3 (mechanized §0 / ADR-immutability / red-run / reachability-gating / harness hooks) →
v3.3 Atlas self-audit (13 hazards) → **v3.4 (closes them under the kit's own discipline,
subagent-driven, trio-adjudicated on the hard forks, Atlas + trio dual-vetted)**. The d≥1
executable floor is the accepted v3.4 scope; executable d≥2 + the non-bypassable interlock are
v3.5+.
