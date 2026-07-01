# freshness-config.md -- revalidation cadence for the kit's own checks (v3.4)

Closes hz-green-rotting: every load-bearing check declares a revalidation
interval; `check_falsifier_freshness` fails (under --strict) when a check's
last recorded pass is older than its interval or predates the current tree.
Intervals are schema-bounded: refusal-critical <= 7 days, others <= 90.

| check | interval_days | refusal_critical |
|---|---|---|
| check_adr_immutability | 7 | true |
| check_falsifier_consistency | 7 | true |
| check_reachability_probes_pass | 7 | true |
| check_bug_log_exists | 30 | false |
| check_paradigm_declared | 90 | false |
| check_hazard_coverage | 7 | true |
| check_adr_index | 30 | false |
| check_first_outcome_log_integrity | 7 | true |
| check_hooks_installed | 7 | true |

**Note (M4):** `check_first_outcome_log_integrity` is currently vacuous until
`tests/.first-outcome-log.json` has entries — Phase 1b must not mark
hz-vacuous-test green on a falsifier that has never had anything to bite.
