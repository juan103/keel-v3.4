# Reachability

External dependencies the project requires at execution time. Each block declares a typed probe; preflight runs every probe and refuses to OTS-stamp (or to advance Phase 1) if any fail.

(v3.3) Probe scoping: `python preflight.py --strict` (ratification, pre-stamp) runs probes live and blocks on failure. Plain `python preflight.py` (session mode) accepts a cached pass younger than 24h and degrades live failures to warnings, so offline sessions and commits are not blocked by network state. Structural errors in this file block in both modes.

This file ships as a template with examples for the four v3 probe types. Replace the example blocks with your project's actual dependencies before starting Phase 1, OR delete this file entirely if your project has no external dependencies.

Per ADR-0008: probes are typed (`https_tls`, `http_status`, `dns`, `script`). Inline shell strings are forbidden. `script` is a bounded escape hatch with five mandatory boundary rules — see `scripts/probes/README.md`.

Credentials never appear in this file. Use `**Auth env:**` to name an environment variable that holds the credential. Preflight fails loudly if the env var is unset.

**v3.4 build project declaration:** This project has no external dependencies (per design §4: "reachability probes for the kit itself ... out of scope (it has no external deps)"). No probes are declared below.
