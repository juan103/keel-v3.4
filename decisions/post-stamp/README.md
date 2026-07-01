# Post-stamp ADRs

ADRs added *after* the project's commitment-stamp event (e.g., OpenTimestamps stamp) live in this subdirectory. The pre-stamp ADRs in the parent `decisions/` directory are part of the stamped bundle and are immutable; post-stamp ADRs are not.

This subdirectory is optional — only relevant for projects that use a cryptographic commitment artifact like OpenTimestamps. Projects without one can ignore this directory; it ships empty (`.gitkeep` only) so the convention is visible without forcing it.
