# Upgrading the KEEL kit

The kit version is recorded in `VERSION` (machine-readable) and `CLAUDE.md`
(prose). `check_kit_version_declared` (preflight) fails if `VERSION` is missing,
a placeholder, or disagrees with CLAUDE.md.

## v3.3 -> v3.4

v3.4 closes the 13 hazards the v3.3 Atlas self-audit found, under the kit's own
self-hosting discipline. Notable additions: the green-row assertion engine
(`green_rows.py`) and the hazard-coverage matrix (`goals/hazard-coverage.md`);
`runtime_role` + `attest.py` author-fill fencing (Phase 2a). See
`CHANGELOG-v3.3.md` for the v3.2->v3.3 step and the v3.4 design under
`docs/superpowers/specs/`.

No breaking changes to existing project layouts; v3.4 is additive. Projects
built under v3.3 keep working; adopt the new checks by copying the v3.4 kit
files and re-running `preflight.py`.
