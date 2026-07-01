# ADR-0006: Kit External Validation Pilot (Commitment-12)

**Status:** accepted
**Date:** 2026-06-28

## Context

v3.4 declares its external-validation falsifier as a pilot_phase gate. The kit must be
validated against at least one real non-self-authored KEEL project before its
refusal-critical checks can be considered externally validated. At ship time the gate is
pilot_pending; it cannot be green until real usage evidence is collected over elapsed time
post-release.

The load-bearing assumptions ledger (goals/load-bearing-assumptions.md SS8) names the
Commitment-12 pilot gate as the resolution point for the external-validation monoculture
risk (hz-external-validation-monoculture). The deadline "2026-12-31" is that concrete
date.

The hazard hz-pilot-phase-unexpressible existed because the pilot_phase shape had no
machine-readable binding type; this ADR supplies the binding, making the hazard expressible
and greening the non-critical matrix row.

## Options considered

1. Defer external-validation entirely -- never build a gate for it; accept ongoing monoculture risk.
2. Declare the gate now as pilot_pending + record the binding ADR; the gate fires
   post-release over real elapsed time, never at ship time.
3. Claim pilot_pass without evidence (dishonest green).

## Decision

Option 2: declare a pilot_phase gate with deadline 2026-12-31 and eligible_count=1. At
ship time the status is pilot_pending. The gate may only be promoted to pilot_pass when at
least one real non-self-authored KEEL project has exercised the refusal-critical checks in
anger and a run record is filed at goals/pilot-records/falsifier-kit-external-validation.json.

```keel-binding
type = "pilot_phase"
id = "falsifier.kit-external-validation"
gate_thresholds = { deadline = "2026-12-31", eligible_count = 1 }
eligibility = "a real non-self-authored KEEL project that exercised the refusal-critical checks in anger"
dispositions = ["pilot_pass", "pilot_fail_falsifier", "pilot_fail_unused", "extend"]
status = "pilot_pending"
```

## Consequences

The hz-pilot-phase-unexpressible hazard row is greened (non-critical, post_hoc) because
the binding is now expressed and mechanically checked by preflight.check_pilot_phase.
The refusal-critical headline stays 0 of 7 (pilot_phase is non-critical). The gate cannot
fire at ship time; pilot evaluation runs post-release. A run record that is missing, stale,
or malformed fails closed (detect-don-t-pretend). The preflight check skips silently when
no pilot_phase block is present, so projects without a pilot commitment are unaffected.
