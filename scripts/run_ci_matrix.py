"""KEEL v3.4 Phase 2b: local CI-matrix runner. Runs tests/kit under each required
Python version. Fails CLOSED on a missing/version-mismatched interpreter -- never
a silent skip (environment contract). Used in real CI; at the local gate the
STATIC check_ci_matrix_declared is the green basis, not this runner."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

REQUIRED = ("3.11", "3.12", "3.13")
KIT = Path(__file__).resolve().parents[1]


def _interpreter_for(version: str) -> "list[str] | None":
    # Windows py launcher: `py -3.11 -V`; fall back to a bare `pythonX.Y`.
    for cmd in (["py", f"-{version}"], [f"python{version}"]):
        try:
            r = subprocess.run(cmd + ["-c", "import sys;print('.'.join(map(str,sys.version_info[:2])))"],
                               capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip() == version:
                return cmd
        except (OSError, FileNotFoundError):
            continue
    return None


def main() -> int:
    failures = []
    for version in REQUIRED:
        interp = _interpreter_for(version)
        if interp is None:
            print(f"[FAIL] Python {version} interpreter absent -- environment contract violated (fails closed)")
            failures.append(version)
            continue
        print(f"[RUN]  Python {version}: {interp} -m pytest tests/kit")
        r = subprocess.run(interp + ["-m", "pytest", "tests/kit"], cwd=str(KIT))
        if r.returncode != 0:
            failures.append(version)
    if failures:
        print(f"\nCI matrix FAILED for: {', '.join(failures)}")
        return 1
    print("\nCI matrix OK on all required versions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
