"""TRsim CLI entry point — `python -m workbench` or `trsim`.

Currently a stub for Phase 0.4. UI / scenario commands come in Phase 4+.
"""

from __future__ import annotations

import sys

from workbench import __version__


def main() -> int:
    """Run TRsim CLI.

    Returns:
        Exit code (0 = success).
    """
    print(f"TRsim v{__version__}")
    print("(Phase 0.4 — minimal entry point. UI in Phase 4.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
