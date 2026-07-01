# Environment

**Optional template.** Required only for projects that depend on cryptographic or execution tooling whose portability is not trivial — for example: OpenTimestamps (`ots stamp` / `ots verify`), GPG signing, hardware-token attestation, custom JIT compilers. If your project just needs Python and standard libraries, you do not need this file.

The friction this template addresses, from `beliefwire`: a portability problem (Python 3.13 + OpenSSL 3 + python-bitcoinlib transitive dependency) wasn't discovered until 90 minutes into the OTS-stamp procedure. By then, the project's pre-registration framing was already committed in conversation. This file gives that class of friction a place to live BEFORE the stamp procedure starts.

## Pre-stamp tooling checklist

For each cryptographic or execution-tooling dependency:

- [ ] `<tool> --version` runs end-to-end on the target machine and prints a version.
- [ ] The tool's expected operations (stamp, verify, upgrade, sign, etc.) all run without unhandled exceptions.
- [ ] Any wrapper or workaround needed to make the tool importable on this environment is documented in the "Workarounds" section below, with explicit boundary (what the wrapper does, what it does NOT change about the stamped artifact).

Run each item on the same machine where the actual stamp / sign / verify will happen, not on a different OS or VM.

### Example dependencies (replace with your project's real ones)

#### OpenTimestamps (`ots`)
- [ ] `ots --version` runs (or wrapper equivalent — see workarounds).
- [ ] `ots stamp <file>` produces a `.ots`.
- [ ] `ots verify <.ots>` returns exit code consistent with the stamp's age (1 acceptable for fresh stamps).

#### GPG (`gpg`)
- [ ] `gpg --version` runs.
- [ ] Signing key available at `<keyid>`.
- [ ] `gpg --sign --detach-sign <file>` produces a `.sig`.

## Workarounds

[Document any project-side wrapper or environment patch needed to make tooling work on the target environment. Each wrapper's existence and boundary go here, NOT in the OTS-stamped bundle. Wrappers are reproducibility aids, not part of the pre-registered analytical commitment.]

### Example: Python 3.13 + OpenSSL 3 + python-bitcoinlib (from `beliefwire`)

- **Wrapper:** `scripts/run_ots.py` stubs `bitcoin.core.key` in `sys.modules` BEFORE the otsclient import chain reaches it.
- **Why:** python-bitcoinlib's transitive load fails on OpenSSL 3 (legacy `BN_add` symbol). otsclient does not actually use the Bitcoin signing functionality this load enables.
- **Boundary:** `run_ots.py` is NOT in the stamped bundle. Removing it requires upstream python-bitcoinlib fix or otsclient dropping the dependency.
- **Affected operations:** stamp, verify, upgrade, info — all work through the wrapper. Bitcoin-signing operations would NOT work but are not exercised by stamp/verify/upgrade.

(Replace with your project's real workarounds, or delete this section.)
