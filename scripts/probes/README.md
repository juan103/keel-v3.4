# scripts/probes/

Escape-hatch directory for `script`-type reachability probes.

This directory ships empty. The kit does not provide example probes — escape hatches should be a last resort, not a default path. The four typed probes (`https_tls`, `http_status`, `dns`, plus `script` itself) cover most real cases.

## When to use a script probe

Only when the typed probe vocabulary cannot express what you need. Examples:
- ICMP ping (typed probes are HTTP/HTTPS/DNS-only).
- A gateway that requires a specific handshake protocol.
- A very narrow check (e.g., a TCP banner check on a non-HTTP port).

If the typed vocabulary is missing something common, file a kit-friction entry; v4 may add a new probe type. Friction-driven design rules.

## Boundary rules (ADR-0008)

The kit refuses to run a script probe unless ALL FIVE rules are satisfied:

1. **Explicit declaration.** The probe block in `goals/reachability.md` must include `**Script probe:** true` AND a non-empty `**Reason:**` field.
2. **Path under this directory.** The `**Path:**` field must resolve under `scripts/probes/`. The kit rejects any path containing `..` or any absolute path.
3. **Tracked by git.** `git ls-files --error-unmatch <path>` must exit 0. Untracked files do not run. Local edits to a tracked file ARE fine — "tracked" not "committed."
4. **Python only.** The kit invokes `$PYTHON_CMD <path>` (the same interpreter detected by the pre-commit hook). No shell. No other interpreters.
5. **Limited environment.** Only `PROBE_URL` (from `**URL:**` if present) and the env var named in `**Auth env:**` (if any) are passed through. No arbitrary env or argv.

## Exit code contract

Exit 0 = probe pass. Non-zero = probe fail. The kit does not interpret stdout/stderr by default — keep your script's exit code meaningful.

## Credentials

Same convention as typed probes: name the env var in `**Auth env:**` in `goals/reachability.md`. The kit reads it and passes it through to the script. Never write the credential value into this directory.
