# Upgrading the KEEL kit

The kit version is recorded in `VERSION` (machine-readable) and `CLAUDE.md`
(prose). `check_kit_version_declared` (preflight) fails if `VERSION` is missing,
a placeholder, or disagrees with CLAUDE.md.

## v3.3 -> v3.4

v3.4 *models* the 13 hazards the v3.3 Atlas self-audit found and wires an
in-boundary falsifier for each, under the kit's own self-hosting discipline — but
it does not claim to have *closed* them. Its ratified headline is **0 of 7
refusal-critical hazards executably closed**; the rest are `conditional`/`pending`
with falsifiable exit conditions, or `accepted-risk` (see `goals/hazard-coverage.md`
and `goals/honesty-ledger.md`). Notable additions: the green-row assertion engine
(`green_rows.py`) and the hazard-coverage matrix (`goals/hazard-coverage.md`);
`runtime_role` + `attest.py` author-fill fencing (Phase 2a). See
`CHANGELOG-v3.3.md` for the v3.2->v3.3 step and the v3.4 design under
`docs/superpowers/specs/`.

No breaking changes to existing project layouts; v3.4 is additive. Projects
built under v3.3 keep working; adopt the new checks by copying the v3.4 kit
files and re-running `preflight.py`.
