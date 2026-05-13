"""Profile-mode toggle (plan/18 § 18.17.5, Q-RT4).

Phase 3 §3-Q4 introduced a 3-way switch for the runtime profiler:

``off``
    Probes skip recording entirely. Per-stage ``perf_counter_ns``
    pair costs ~200 ns each, so disabling them keeps the hot path
    untouched for production runs.

``explicit``
    Probes only fire when a caller asks (``trsim profile``). The
    pipeline ships them in place so toggling on does not require
    re-instantiation, but they remain dormant for ``trsim run``.

``live``
    Probes fire on every frame, populating the FrameProfiler in
    real time. Eats the ~200 ns/stage overhead in exchange for a
    rolling histogram in the Profiler panel.

This module ships the :class:`ProfileMode` enum + the default that
both CLI commands and the TOML ``[profiling] mode = "..."`` field
agree on. Pipeline / probe wiring lives in :mod:`workbench.app`.
"""

from __future__ import annotations

from enum import StrEnum


class ProfileMode(StrEnum):
    """Runtime profiling toggle (plan/18 § 18.17.5)."""

    OFF = "off"
    EXPLICIT = "explicit"
    LIVE = "live"


DEFAULT_PROFILE_MODE: ProfileMode = ProfileMode.OFF
"""Default for production ``trsim run``: zero probe overhead."""


PROFILE_MODES_IN_DISPLAY_ORDER: tuple[ProfileMode, ...] = (
    ProfileMode.OFF,
    ProfileMode.EXPLICIT,
    ProfileMode.LIVE,
)
"""Order the Profiler panel + CLI ``--help`` show the options.

Matches plan/18 § 18.17.5 — increasing intrusiveness.
"""


def parse_profile_mode(value: str) -> ProfileMode:
    """Case-insensitive ``ProfileMode`` lookup.

    Args:
        value: User-supplied string (CLI flag, TOML scalar).

    Returns:
        The matching :class:`ProfileMode`.

    Raises:
        ValueError: ``value`` is not one of ``off`` / ``explicit`` /
            ``live`` (case-insensitive).
    """
    normalised = value.strip().lower()
    for mode in PROFILE_MODES_IN_DISPLAY_ORDER:
        if mode.value == normalised:
            return mode
    allowed = ", ".join(mode.value for mode in PROFILE_MODES_IN_DISPLAY_ORDER)
    msg = f"unknown profile mode {value!r}; expected one of {allowed}"
    raise ValueError(msg)
