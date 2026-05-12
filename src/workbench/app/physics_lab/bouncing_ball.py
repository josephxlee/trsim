"""Bouncing Ball simulator — Physics Lab first interactive demo (PL-D + PL-E).

Vertical 1-D dynamics, no spin, no horizontal motion. The ball falls
under constant gravity, bounces inelastically off a fixed ground at
``y = 0``, and loses ``(1 - restitution)`` of its speed at each
collision. plan/19 § 19.12.1 frames it as the canonical first demo:
small, fully understood, restitution slider drives the visible
behaviour.

Closed-form invariants the analytic-reference pane can quote:

- Peak height after first bounce: ``h1 = restitution^2 * h0``.
- Time to first impact from height ``h0`` at rest: ``sqrt(2 * h0 / g)``.
- Total displacement over a long horizon converges geometrically.

The simulator itself uses a semi-implicit Euler step so energy stays
bounded under coarse timesteps (the explicit Euler version drifts
upward each bounce).

References:

- plan/19 § 19.12.1 — Bouncing Ball demo scenario.
- Knott / Skolnik chapters on basic dynamics for the analytic
  invariants quoted above.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

# Earth-surface gravity; can be replaced by the user later (Phase
# 9.x will read this from a `@physics_param` slider).
_DEFAULT_GRAVITY_M_S2: float = 9.81

# Type of a user-supplied step replacement (PL-E Code edit mode):
# ``step_fn(self, dt_s) -> None`` runs against the simulator
# instance directly (so the user code reads / writes ``self._state``
# the same way the built-in step does).
StepFn = Callable[["BouncingBallSimulator", float], None]


@dataclass(frozen=True, slots=True)
class BouncingBallState:
    """One time-sample of the Bouncing Ball trajectory.

    Attributes:
        time_s: Elapsed simulation time in seconds.
        position_m: Vertical position; ``0.0`` = ground.
        velocity_m_s: Vertical velocity; positive = upward.
        bounces: How many ground impacts have occurred so far.
    """

    time_s: float
    position_m: float
    velocity_m_s: float
    bounces: int = 0


class BouncingBallSimulator:
    """Stateful Bouncing Ball stepper.

    Attributes:
        gravity_m_s2: Constant downward acceleration (positive value).
        restitution: Coefficient of restitution in ``[0, 1]``. ``1`` =
            perfectly elastic (forever bouncing), ``0`` = stick to
            ground on first impact.
        initial_height_m: ``y(t=0)``. Must be ``>= 0``.
        initial_velocity_m_s: ``v(t=0)``. Default 0 = drop from rest.

    Raises:
        ValueError: For non-positive gravity, restitution outside
            ``[0, 1]``, negative initial height.
    """

    def __init__(
        self,
        *,
        gravity_m_s2: float = _DEFAULT_GRAVITY_M_S2,
        restitution: float = 0.7,
        initial_height_m: float = 5.0,
        initial_velocity_m_s: float = 0.0,
    ) -> None:
        if gravity_m_s2 <= 0.0:
            msg = f"gravity_m_s2 must be > 0, got {gravity_m_s2}"
            raise ValueError(msg)
        if not 0.0 <= restitution <= 1.0:
            msg = f"restitution must be in [0, 1], got {restitution}"
            raise ValueError(msg)
        if initial_height_m < 0.0:
            msg = f"initial_height_m must be >= 0, got {initial_height_m}"
            raise ValueError(msg)

        self.gravity_m_s2 = gravity_m_s2
        self.restitution = restitution
        self.initial_height_m = initial_height_m
        self.initial_velocity_m_s = initial_velocity_m_s

        self._state = BouncingBallState(
            time_s=0.0,
            position_m=initial_height_m,
            velocity_m_s=initial_velocity_m_s,
            bounces=0,
        )
        # PL-E — user-supplied step override. None means "use the
        # built-in semi-implicit Euler step". The Code panel's Save &
        # Reload action plugs a new function in here.
        self._step_override: StepFn | None = None

    # ------------------------------------------------------------------
    # State surface
    # ------------------------------------------------------------------

    @property
    def state(self) -> BouncingBallState:
        return self._state

    def set_restitution(self, value: float) -> None:
        """Update the restitution mid-run (Parameters pane slider)."""
        if not 0.0 <= value <= 1.0:
            msg = f"restitution must be in [0, 1], got {value}"
            raise ValueError(msg)
        self.restitution = value

    def reset(self) -> BouncingBallState:
        """Reset to the constructor-supplied initial state.

        Does **not** clear ``_step_override`` — a custom step survives
        a reset so the user can iterate without re-uploading code.
        Use :meth:`set_step_override(None)` to fall back to the
        built-in semi-implicit Euler.
        """
        self._state = BouncingBallState(
            time_s=0.0,
            position_m=self.initial_height_m,
            velocity_m_s=self.initial_velocity_m_s,
            bounces=0,
        )
        return self._state

    def set_step_override(self, step_fn: StepFn | None) -> None:
        """Inject (or remove) a user-supplied step function (PL-E).

        ``step_fn(simulator, dt_s)`` reads / writes
        ``simulator._state`` directly. ``None`` restores the
        built-in step.
        """
        self._step_override = step_fn

    @property
    def has_step_override(self) -> bool:
        return self._step_override is not None

    def update_state(self, new_state: BouncingBallState) -> None:
        """State setter used by step overrides (and tests).

        Hides the private ``_state`` attribute behind a public hook so
        downstream code can apply a fresh state without poking at
        ``sim._state`` directly.
        """
        self._state = new_state

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self, dt_s: float) -> BouncingBallState:
        """Advance ``dt_s`` seconds with a semi-implicit Euler update.

        Order matters: velocity update first (with ``-g * dt``),
        position next (with the *new* velocity). This is the standard
        symplectic 1st-order scheme — energy stays bounded under
        coarse ``dt`` rather than drifting upward.

        Ground contact (``y <= 0``): position is clamped to 0, the
        sign of velocity flips, and its magnitude scales by
        ``restitution``. A bounce counter increments. Sub-mm-per-sec
        residual velocity (``|v| < 1e-3``) collapses to 0 so the ball
        does not jitter forever.

        PL-E: when :meth:`set_step_override` was called with a
        callable, ``step`` defers to it instead of running the
        built-in formula. The override receives ``(self, dt_s)`` and
        is expected to mutate ``self._state`` (typically through
        :meth:`update_state`).
        """
        if dt_s <= 0.0:
            msg = f"dt_s must be > 0, got {dt_s}"
            raise ValueError(msg)

        if self._step_override is not None:
            self._step_override(self, dt_s)
            return self._state

        s = self._state
        new_v = s.velocity_m_s - self.gravity_m_s2 * dt_s
        new_y = s.position_m + new_v * dt_s
        new_bounces = s.bounces

        if new_y <= 0.0:
            new_y = 0.0
            new_v = -new_v * self.restitution
            if abs(new_v) < 1e-3:
                new_v = 0.0
            new_bounces += 1

        self._state = BouncingBallState(
            time_s=s.time_s + dt_s,
            position_m=new_y,
            velocity_m_s=new_v,
            bounces=new_bounces,
        )
        return self._state


def analytic_peak_height_m(initial_height_m: float, restitution: float, bounce: int) -> float:
    """Closed-form peak height after ``bounce`` impacts.

    ``h_n = restitution^(2 n) * h_0``. ``bounce = 0`` returns ``h_0``.
    Demonstrates the geometric decay the simulator reproduces; the
    Compare-mode demo overlays this curve on the simulated peaks.
    """
    if initial_height_m < 0.0:
        msg = f"initial_height_m must be >= 0, got {initial_height_m}"
        raise ValueError(msg)
    if not 0.0 <= restitution <= 1.0:
        msg = f"restitution must be in [0, 1], got {restitution}"
        raise ValueError(msg)
    if bounce < 0:
        msg = f"bounce must be >= 0, got {bounce}"
        raise ValueError(msg)
    return initial_height_m * (restitution ** (2 * bounce))
