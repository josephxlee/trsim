"""Physics Lab time modes (PL-9.1e, plan/19 § 19.6).

Four mutually-exclusive modes drive how the Time controls and the
Visualisation pane behave:

============ ==================================================
mode         behaviour
============ ==================================================
``static``   Time is frozen. Transport disabled. Plot shows the
             initial state only — used for ``free-space-loss``-
             style sanity checks where no trajectory exists.
``run``      Single trajectory in real-time. Play / Pause / Stop
             / step / slider all active. PL-D default.
``compare``  Two simulations side by side — usually the simulated
             curve overlaid with an analytic reference (Bouncing
             Ball: ``analytic_peak_height_m`` marker per bounce).
``sweep``    A parameter range fans out into N independent
             trajectories shown together as overlay curves.
============ ==================================================

The enum lives in the domain layer because both the App-layer
controller and the UI-layer mode combo need to agree on the four
string values without importing each other.
"""

from __future__ import annotations

from enum import StrEnum


class TimeMode(StrEnum):
    """The four Physics Lab time modes (plan/19 § 19.6)."""

    STATIC = "static"
    RUN = "run"
    COMPARE = "compare"
    SWEEP = "sweep"


# Convenience tuple for the UI combo to iterate in display order.
TIME_MODES_IN_DISPLAY_ORDER: tuple[TimeMode, ...] = (
    TimeMode.STATIC,
    TimeMode.RUN,
    TimeMode.COMPARE,
    TimeMode.SWEEP,
)
