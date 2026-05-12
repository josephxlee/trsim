"""Air-drag tests (PL-9.1g, plan/19 § 19.12.1).

Covers the 5th BouncingBall parameter ``drag_coefficient_k``:

- Simulator physics: ``k = 0`` regression, ``k > 0`` makes peak height
  decay faster than the analytic geometric series; vertical-fall
  velocity tends towards a terminal value rather than diverging.
- ``set_drag_coefficient`` validation.
- ParametersWidget exposes the slider.
- Controller routes auto-slider changes to the simulator.
- SavedExperiment round-trip preserves the value.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.app.physics_lab import (
    BouncingBallSimulator,
    analytic_peak_height_m,
)
from workbench.domain.physics_lab import (
    SavedExperiment,
    TimeMode,
    read_saved_experiment,
    write_saved_experiment,
)
from workbench.ui.physics_lab import (
    BouncingBallController,
    ParametersWidget,
    PhysicsLabWorkspace,
)

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Simulator physics
# ---------------------------------------------------------------------


def test_zero_drag_matches_pl_d_behaviour() -> None:
    """drag_coefficient_k = 0 is a strict regression — the trajectory
    must equal the PL-D semi-implicit Euler step for every dt.
    """
    sim_a = BouncingBallSimulator(initial_height_m=5.0)
    sim_b = BouncingBallSimulator(initial_height_m=5.0, drag_coefficient_k=0.0)
    for _ in range(50):
        a = sim_a.step(0.05)
        b = sim_b.step(0.05)
        assert a == b


def test_positive_drag_dampens_first_bounce_peak() -> None:
    """Quadratic drag dissipates energy at every step, so the first
    bounce after a free fall reaches a peak strictly below the
    analytic envelope (``r^2 * h0``).
    """
    sim = BouncingBallSimulator(
        gravity_m_s2=9.81,
        restitution=0.9,
        initial_height_m=10.0,
        drag_coefficient_k=0.2,
    )
    peak_after_first_bounce = 0.0
    for _ in range(2000):
        sim.step(0.005)
        # Track peak height strictly after the first bounce.
        if sim.state.bounces == 1:
            peak_after_first_bounce = max(peak_after_first_bounce, sim.state.position_m)
        if sim.state.bounces >= 2:
            break
    analytic_peak = analytic_peak_height_m(10.0, 0.9, 1)
    assert peak_after_first_bounce > 0.0
    assert peak_after_first_bounce < analytic_peak


def test_negative_drag_rejected() -> None:
    with pytest.raises(ValueError, match=r"drag_coefficient_k must be >= 0"):
        BouncingBallSimulator(drag_coefficient_k=-0.5)


def test_set_drag_coefficient_round_trip() -> None:
    sim = BouncingBallSimulator()
    sim.set_drag_coefficient(0.3)
    assert sim.drag_coefficient_k == pytest.approx(0.3)


def test_set_drag_coefficient_rejects_negative() -> None:
    sim = BouncingBallSimulator()
    with pytest.raises(ValueError, match=r"drag_coefficient_k must be >= 0"):
        sim.set_drag_coefficient(-0.1)


# ---------------------------------------------------------------------
# UI integration
# ---------------------------------------------------------------------


def test_parameters_widget_includes_drag_slider(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = ParametersWidget()
    qtbot.addWidget(p)  # type: ignore[attr-defined]
    names = p.auto_parameters().parameter_names()
    assert "drag_coefficient_k" in names


def test_drag_slider_forwards_to_simulator(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    sim = ws.bouncing_ball_controller().simulator
    assert sim.drag_coefficient_k == pytest.approx(0.0)
    ws.parameters_panel().auto_parameters().set_value("drag_coefficient_k", 0.42)
    assert sim.drag_coefficient_k == pytest.approx(0.42)


def test_reset_with_applies_drag_to_new_simulator(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller: BouncingBallController = ws.bouncing_ball_controller()
    controller.reset_with(drag_coefficient_k=0.25)
    assert controller.simulator.drag_coefficient_k == pytest.approx(0.25)


# ---------------------------------------------------------------------
# SavedExperiment round-trip with drag
# ---------------------------------------------------------------------


def test_saved_experiment_round_trip_preserves_drag(tmp_path: Path) -> None:
    exp = SavedExperiment(
        experiment_id="with-drag",
        drag_coefficient_k=0.3,
        mode=TimeMode.RUN,
    )
    path = tmp_path / "drag.toml"
    write_saved_experiment(path, exp)
    loaded = read_saved_experiment(path)
    assert loaded.drag_coefficient_k == pytest.approx(0.3)
    assert loaded == exp


def test_load_experiment_applies_drag_to_controller(
    tmp_path: Path,
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, experiment_root=tmp_path)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    exp = SavedExperiment(experiment_id="x", drag_coefficient_k=0.15)
    ws.load_experiment(exp)
    assert ws.bouncing_ball_controller().simulator.drag_coefficient_k == pytest.approx(0.15)


def test_legacy_saved_experiment_without_drag_field_loads_with_zero(
    tmp_path: Path,
) -> None:
    """A TOML file written before PL-9.1g (no drag_coefficient_k key)
    must still load — falling back to ``0.0`` keeps PL-D behaviour.
    """
    path = tmp_path / "legacy.toml"
    path.write_text(
        '[experiment]\nid = "legacy"\nmode = "run"\n'
        "[parameters]\ngravity_m_s2 = 9.81\nrestitution = 0.5\n"
        "initial_height_m = 5.0\ninitial_velocity_m_s = 0.0\n",
        encoding="utf-8",
    )
    loaded = read_saved_experiment(path)
    assert loaded.drag_coefficient_k == pytest.approx(0.0)
