"""Physics Lab parameter metadata (PL-9.1c, plan/19 § 19.5.5).

The ``@physics_param`` decorator + :class:`PhysicsParam` dataclass let
a function or simulator class declare which scalar parameters it
exposes for interactive control. The Parameters pane in the Physics
Lab workspace consumes the metadata and auto-generates the matching
sliders + readouts.

plan/19 § 19.5.5 specifies the slider-scale conventions used here:

============================ ============== ===================
parameter kind               recommended    examples
                             scale
============================ ============== ===================
Range / freq / time / power  log            ``1..100000 m``
RCS                          log            ``0.001..1000 m^2``
Angle / ratio (0..1)         linear         ``restitution``
Mass / distance (narrow)     linear         ``ball mass 0.1..10``
Integer counts               (caller picks) ``N receivers``
Signed                       linear         ``velocity -20..20``
Can be zero                  linear         ``initial offset``
============================ ============== ===================

Usage:

.. code-block:: python

    @physics_param("restitution", min_value=0.0, max_value=1.0)
    @physics_param("mass_kg", min_value=0.1, max_value=10.0, scale="log")
    def simulate(restitution, mass_kg): ...

    params = get_physics_params(simulate)
    # (PhysicsParam('restitution', ...), PhysicsParam('mass_kg', ...))

The decorator stacks bottom-up the standard Python way; the helper
``insert(0, param)`` reverses the application order so the returned
tuple is in **source-line order** — what the human reader expects.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeVar

# All sliders use the same tick resolution. 100 ticks = 1 % step in a
# linear [0,1] range; for log ranges spanning N decades it gives
# ``N/100`` decades per tick — good enough for interactive browsing.
SLIDER_TICK_RESOLUTION: int = 100

ParameterScale = Literal["linear", "log"]
_PARAMS_ATTR: str = "__physics_params__"

F = TypeVar("F", bound=Callable[..., object])


@dataclass(frozen=True, slots=True)
class PhysicsParam:
    """One named scalar parameter exposed to the Parameters pane.

    Attributes:
        name: Identifier (matches the function arg / setter name).
        min_value: Lower bound of the slider range.
        max_value: Upper bound (must be ``> min_value``).
        scale: ``"linear"`` (default) or ``"log"``. ``"log"`` requires
            ``min_value > 0``.
        unit: Optional unit string for the readout label (e.g. ``"m"``,
            ``"m/s"``, ``"-"``).
        default: Slider initial position. Falls back to ``min_value``
            for linear scales and to the geometric mean for log
            scales when ``None``.
        description: Free-form tooltip text for the slider.

    Raises:
        ValueError: For empty ``name``, non-increasing range, log
            scale with non-positive ``min_value``, or ``default``
            outside ``[min_value, max_value]``.
    """

    name: str
    min_value: float
    max_value: float
    scale: ParameterScale = "linear"
    unit: str = ""
    default: float | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            msg = "PhysicsParam.name must be non-empty"
            raise ValueError(msg)
        if self.min_value >= self.max_value:
            msg = (
                f"PhysicsParam {self.name!r}: min_value must be < max_value "
                f"(got min={self.min_value}, max={self.max_value})"
            )
            raise ValueError(msg)
        if self.scale == "log" and self.min_value <= 0.0:
            msg = (
                f"PhysicsParam {self.name!r}: log scale requires "
                f"min_value > 0 (got {self.min_value})"
            )
            raise ValueError(msg)
        if self.default is not None and not (self.min_value <= self.default <= self.max_value):
            msg = (
                f"PhysicsParam {self.name!r}: default {self.default} outside "
                f"[{self.min_value}, {self.max_value}]"
            )
            raise ValueError(msg)


def physics_param(
    name: str,
    *,
    min_value: float,
    max_value: float,
    scale: ParameterScale = "linear",
    unit: str = "",
    default: float | None = None,
    description: str = "",
) -> Callable[[F], F]:
    """Attach a :class:`PhysicsParam` to a function as introspectable metadata.

    Stacked decorators preserve **source line order** in the
    accumulated tuple — ``physics_param`` closest to ``def`` (i.e. the
    bottom-most decorator written by the user) appears last.

    The function itself is returned unchanged; the decorator only
    side-effects an ``__physics_params__`` list attribute.
    """
    param = PhysicsParam(
        name=name,
        min_value=min_value,
        max_value=max_value,
        scale=scale,
        unit=unit,
        default=default,
        description=description,
    )

    def wrap(func: F) -> F:
        existing = getattr(func, _PARAMS_ATTR, None)
        if existing is None:
            params: list[PhysicsParam] = []
            # Functions are mutable; setattr works without descriptor games.
            setattr(func, _PARAMS_ATTR, params)
        else:
            params = existing
        # Newer (outer) decorator runs after inner; prepend so the final
        # tuple ends up in user-source order [top, ..., bottom].
        params.insert(0, param)
        return func

    return wrap


def get_physics_params(func: Callable[..., object]) -> tuple[PhysicsParam, ...]:
    """Return the physics-param metadata attached to ``func`` (or ``()``)."""
    return tuple(getattr(func, _PARAMS_ATTR, ()))


# ---------------------------------------------------------------------
# Bouncing Ball parameter specs
# ---------------------------------------------------------------------


@physics_param(
    "gravity_m_s2",
    min_value=1.0,
    max_value=30.0,
    scale="linear",
    unit="m/s^2",
    default=9.81,
    description="Constant downward acceleration acting on the ball.",
)
@physics_param(
    "restitution",
    min_value=0.0,
    max_value=1.0,
    scale="linear",
    unit="-",
    default=0.70,
    description=(
        "Coefficient of restitution on ground impact. 1 = elastic, 0 = stick on first impact."
    ),
)
@physics_param(
    "initial_height_m",
    min_value=0.1,
    max_value=50.0,
    scale="log",
    unit="m",
    default=5.0,
    description="Initial vertical position above the ground at t=0.",
)
@physics_param(
    "initial_velocity_m_s",
    min_value=-20.0,
    max_value=20.0,
    scale="linear",
    unit="m/s",
    default=0.0,
    description="Initial vertical velocity at t=0; positive = upward.",
)
@physics_param(
    "drag_coefficient_k",
    min_value=0.0,
    max_value=1.0,
    scale="linear",
    unit="1/m",
    default=0.0,
    description=(
        "Air-drag coefficient in F_drag/m = -k * v * |v|. Default 0 = "
        "PL-D vanilla bouncing; values up to ~0.5 model realistic "
        "low-mass spheres at sea-level air density."
    ),
)
def _bouncing_ball_param_marker() -> None:
    """Marker function carrying the Bouncing Ball ``@physics_param`` stack.

    Only its ``__physics_params__`` attribute is consumed; the body is
    never executed.
    """


BOUNCING_BALL_PARAM_SPECS: tuple[PhysicsParam, ...] = get_physics_params(
    _bouncing_ball_param_marker
)
