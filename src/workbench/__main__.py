"""TRsim CLI entry point — ``python -m workbench`` or ``trsim``.

Phase 3.7 — delegates to :mod:`workbench.cli.main`. The ``main``
re-export is what ``pyproject.toml [project.scripts] trsim``
points at.
"""

from __future__ import annotations

import sys

from workbench.cli.main import main

__all__ = ["main"]

if __name__ == "__main__":
    sys.exit(main())
