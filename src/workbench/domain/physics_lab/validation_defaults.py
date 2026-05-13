"""Validation Bench default field mapping (Phase 9 M3).

The generalised Validation Bench layer (M1,
:mod:`workbench.app.physics_lab.validation_runner`) needs to know which
keys in the model's output state dict map to the "x" and "y" axes of
the measurement. The :class:`PhysicsModelProtocol` itself does not
carry that metadata — the Validation Bench picks reasonable defaults
per model so the user can drop a measured dataset onto any registered
physics model without supplying a column selector first.

Returning ``None`` means "no default known"; the workspace surfaces a
status-bar hint in that case so the user can supply column names
explicitly in a follow-up cycle (e.g. via a future Validation Bench
panel).
"""

from __future__ import annotations

from workbench.sdk.protocols import PhysicsModelProtocol

# Built-in defaults (PL-9.3b + PL-D model names). Keep this map tight
# — registry-style autoload is a follow-up; for now the three first-
# party models cover the entire built-in Library.
_DEFAULT_FIELDS_BY_NAME: dict[str, tuple[str, str]] = {
    "Bouncing Ball": ("time_s", "position_m"),
    "Gravity Only (analytic)": ("time_s", "position_m"),
    "Free-Space Path Loss": ("range_m", "loss_db"),
}


def default_validation_fields(model: PhysicsModelProtocol) -> tuple[str, str] | None:
    """Return ``(x_field, y_field)`` for ``model`` or ``None`` if unknown.

    Looked up by :attr:`PhysicsModelProtocol.name`. Custom (plug-in)
    models will return ``None`` until the user / packager supplies an
    explicit mapping; the workspace surfaces a hint in the status bar
    when the lookup misses.
    """
    return _DEFAULT_FIELDS_BY_NAME.get(model.name)
