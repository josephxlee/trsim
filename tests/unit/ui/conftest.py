"""Qt test fixtures (Phase 4.1).

Forces the offscreen QPA platform so widget tests run headless on
local + CI (Linux runner without libEGL.so.1, Windows without an
attached display, etc.). Honours an existing ``QT_QPA_PLATFORM`` if
the developer wants to override (e.g. ``minimal`` for debugging).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
