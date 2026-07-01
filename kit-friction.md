# Kit Friction Log

Things the kit does badly, written down as they happen so the kit can evolve from real friction rather than imagined improvements.

## How to use

Whenever something in the kit causes friction — a rule that's wrong for this project, a step that wastes time, a check that fails for bad reasons, an instruction the agent can't follow — add an entry here. Don't silently work around it.

## Format

```
### YYYY-MM-DD — short title

**What happened:** Description of the friction. What rule, what step, what failed.

**What I did instead:** How I got past it (workaround, override, skip).

**What would have worked better:** Proposed change to the kit. May be wrong — that's fine, write it anyway.
```

## Entries

### 2026-XX-XX — example entry (delete this when adding your first real one)

**What happened:** The "test first, then code" rule made me stall on Phase 2 because I didn't know what shape the graph metric output would have until I ran it once.

**What I did instead:** Wrote a quick exploration script that computed the metric on the real graph and a random graph, saw the output shape, then went back and wrote the test based on what I'd learned.

**What would have worked better:** The kit should distinguish between "exploratory" requirements (where I'm finding out what the answer looks like) and "verification" requirements (where I know what should happen). Exploratory requirements need a different cycle: probe → observe → write test → harden into requirement. ADR-0001 partially addresses this with the `EXPLORATORY` marker, but the work cycle in CLAUDE.md doesn't reflect it. Consider adding a Phase 0 sub-cycle for exploration.

### 2026-06-27 — neuter-probe: v1 partial (single-mutation, no equivalent-mutant detection)

**What happened:** The neuter-probe (assertion 3b in the green-row engine, implementing spec §5.3's mutation probe) is a v1 partial. It applies exactly one mutation: it replaces the named check function's body with `return []` (the "neuter" mutation), then requires the negative proving test to FAIL against that neutered copy. This catches negative tests that are fully vacuous — they don't depend on the check at all (e.g., `assert 1 == 1`). It does NOT catch subtler partial-vacuity: a negative test that depends on only part of the check's logic, or one that exercises a path the neuter mutation doesn't affect. Equivalent-mutant detection (the case where the check already returns `[]` on the negative-test input so neutering changes nothing) is also not implemented.

**What I did instead:** Implemented the single-mutation neuter probe and documented this as a v1 partial. Full operator-set mutation adequacy is deferred to a later hardening task.

**What would have worked better:** A richer mutation set (operator substitution, branch flipping, return-value negation) would catch more partial-vacuity cases. The equivalent-mutant edge (where the check already returns `[]` on the escape input, making the neuter mutation trivially survived for a different reason) should be detected and reported separately rather than silently flagged as vacuous. These are out of scope for v1.

**Implementation note:** The probe runs against a temporary COPY of the repo with the check's source file overwritten by the neutered version (`shutil.copytree` + `write_text`), using `cwd=<copy>` for the subprocess. A PYTHONPATH-shadow approach does not work: `python -m pytest` inserts `cwd` (`''`) at `sys.path[0]`, and the fixture's `test_synth.py` also explicitly does `sys.path.insert(0, parents[1])` (= `cwd`), so the real un-neutered module always wins the import race over any PYTHONPATH entry. The copytree approach sidesteps this because both `cwd` and `parents[1]` resolve to the copy directory, whose `synthcheck.py` is already the neutered version.
