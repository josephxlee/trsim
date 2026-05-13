"""``default_validation_fields`` lookup tests (Phase 9 M3, plan/19 § 19.7.5+)."""

from __future__ import annotations

from workbench.app.physics_lab import (
    BouncingBallModel,
    FreeSpaceLossModel,
    GravityOnlyModel,
)
from workbench.domain.physics_lab import default_validation_fields


def test_defaults_bouncing_ball() -> None:
    assert default_validation_fields(BouncingBallModel()) == ("time_s", "position_m")


def test_defaults_gravity_only() -> None:
    assert default_validation_fields(GravityOnlyModel()) == ("time_s", "position_m")


def test_defaults_free_space_loss() -> None:
    assert default_validation_fields(FreeSpaceLossModel()) == ("range_m", "loss_db")


def test_defaults_unknown_model_returns_none() -> None:
    class UnknownModel:
        name = "Some Custom Plugin"
        category = "dynamics"
        time_mode = "dynamic"
        visualization = "2d"

        @property
        def parameters(self) -> tuple[()]:
            return ()

        def compute(self, state, params, dt_s):  # type: ignore[no-untyped-def]
            return {"y": 0.0}

    assert default_validation_fields(UnknownModel()) is None  # type: ignore[arg-type]
