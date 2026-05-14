"""Lab-B Validation Bench tests (PL-9.2c, plan/19 § 19.9.4).

Covers the controller's ``run_validation_from_dataset`` + the
workspace's auto-trigger on Measured-Data selection.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.domain.physics_lab import (
    ValidationMetrics,
    inspect_csv,
)
from workbench.ui.physics_lab import BouncingBallController, PhysicsLabWorkspace

pytestmark = pytest.mark.qt


def _write_synthetic_drop_csv(path: Path, *, gravity: float = 9.81, h0: float = 5.0) -> None:
    """Free-fall trajectory ``y = h0 - 0.5 * g * t^2`` until ground."""
    t = np.linspace(0.0, np.sqrt(2.0 * h0 / gravity), 50)
    y = np.maximum(0.0, h0 - 0.5 * gravity * t * t)
    rows = [f"{ti:.6f},{yi:.6f}" for ti, yi in zip(t, y, strict=True)]
    path.write_text("time_s,position_m\n" + "\n".join(rows) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------
# Controller path
# ---------------------------------------------------------------------


def test_run_validation_from_dataset_emits_metrics_signal(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    """Measured CSV matches the simulator-physics trajectory (same g,
    h0), so the RMSE is small and correlation is near 1."""
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_synthetic_drop_csv(csv_path)
    dataset = inspect_csv(csv_path)
    received: list[ValidationMetrics] = []
    ws.bouncing_ball_controller().validation_metrics_ready.connect(received.append)
    metrics = ws.bouncing_ball_controller().run_validation_from_dataset(dataset)
    assert isinstance(metrics, ValidationMetrics)
    assert received == [metrics]
    # The synthetic CSV used analytic free-fall (no bounce), so RMSE
    # should be tiny — the semi-implicit Euler ground-bounce kicks in
    # at the very last sample where y=0, but the bulk of the curve
    # matches well.
    assert metrics.rmse < 0.5
    assert metrics.pearson_correlation > 0.95


def test_validation_adds_two_overlay_curves(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_synthetic_drop_csv(csv_path)
    dataset = inspect_csv(csv_path)
    controller: BouncingBallController = ws.bouncing_ball_controller()
    controller.run_validation_from_dataset(dataset)
    overlays = ws.viz_panel().overlay_names()
    assert controller.VALIDATION_MEASURED_CURVE in overlays
    assert controller.VALIDATION_SIM_CURVE in overlays


def test_validation_does_not_perturb_live_history(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """The validation runs a fresh simulator; the controller's live
    history + cursor must stay at frame 0.
    """
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    csv_path = tmp_path / "drop.csv"
    _write_synthetic_drop_csv(csv_path)
    dataset = inspect_csv(csv_path)
    controller.run_validation_from_dataset(dataset)
    assert controller.current_frame_index == 0
    assert len(controller.history) == 1


def test_clear_validation_overlays_removes_both_curves(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_synthetic_drop_csv(csv_path)
    controller: BouncingBallController = ws.bouncing_ball_controller()
    controller.run_validation_from_dataset(inspect_csv(csv_path))
    controller.clear_validation_overlays()
    overlays = ws.viz_panel().overlay_names()
    assert controller.VALIDATION_MEASURED_CURVE not in overlays
    assert controller.VALIDATION_SIM_CURVE not in overlays


def test_validation_rejects_single_column_dataset(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "single.csv"
    csv_path.write_text("only\n1.0\n2.0\n", encoding="utf-8")
    dataset = inspect_csv(csv_path)
    with pytest.raises(ValueError, match=r"< 2 columns"):
        ws.bouncing_ball_controller().run_validation_from_dataset(dataset)


def test_validation_rejects_unknown_x_column(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_synthetic_drop_csv(csv_path)
    dataset = inspect_csv(csv_path)
    with pytest.raises(ValueError, match=r"x column 'unknown' not in"):
        ws.bouncing_ball_controller().run_validation_from_dataset(dataset, x_column="unknown")


def test_validation_falls_back_to_first_two_columns(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Dataset with non-default column names still works — first
    two columns get used.
    """
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    # Use generic names "t", "y" -> the controller picks first two.
    t = np.linspace(0.0, 1.0, 25)
    y = np.maximum(0.0, 5.0 - 0.5 * 9.81 * t * t)
    rows = [f"{ti:.6f},{yi:.6f}" for ti, yi in zip(t, y, strict=True)]
    csv_path.write_text("t,y\n" + "\n".join(rows) + "\n", encoding="utf-8")
    dataset = inspect_csv(csv_path)
    metrics = ws.bouncing_ball_controller().run_validation_from_dataset(dataset)
    assert metrics.n_samples > 0


# ---------------------------------------------------------------------
# Workspace auto-trigger
# ---------------------------------------------------------------------


def test_library_selection_auto_runs_validation(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    measured_root = tmp_path / "measured"
    measured_root.mkdir()
    _write_synthetic_drop_csv(measured_root / "drop.csv")
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured_root)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    # Pick the measured row -> auto-validate.
    cat = ws.library_panel().measured_category()
    label = cat.child(0).text(0)
    ws.library_panel().select_label(label)
    assert ws.last_validation_metrics() is not None


def test_workspace_validation_metric_displayed_in_status(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_synthetic_drop_csv(csv_path)
    dataset = inspect_csv(csv_path)
    ws.bouncing_ball_controller().run_validation_from_dataset(dataset)
    status_text = ws.time_controls().status_label().text()
    assert "RMSE" in status_text
    assert "corr" in status_text


def test_workspace_invalid_dataset_does_not_crash(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Selecting a 1-column dataset auto-runs validation, which raises
    ValueError inside the handler. The handler must swallow it so the
    workspace stays responsive.
    """
    measured_root = tmp_path / "measured"
    measured_root.mkdir()
    (measured_root / "single.csv").write_text("only\n1.0\n2.0\n", encoding="utf-8")
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured_root)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    cat = ws.library_panel().measured_category()
    label = cat.child(0).text(0)
    ws.library_panel().select_label(label)
    # No metric was produced.
    assert ws.last_validation_metrics() is None


def test_workspace_initializes_validation_state_none(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.last_validation_metrics() is None


# ---------------------------------------------------------------------
# M2 — generalized-layer parity regression
# ---------------------------------------------------------------------


def test_run_validation_matches_generalized_layer(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    """M2 refactor invariant: the controller's metrics match the result
    of calling :func:`run_validation_for_model` with a
    :class:`BouncingBallModel` directly.

    Guards against drift between the PL-9.2c GUI path and the
    Phase 9 M1 generalized validation layer.
    """
    from workbench.app.physics_lab import BouncingBallModel, run_validation_for_model

    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_synthetic_drop_csv(csv_path)
    dataset = inspect_csv(csv_path)

    controller = ws.bouncing_ball_controller()
    metrics_via_controller = controller.run_validation_from_dataset(dataset)

    sim = controller.simulator
    params = {
        "gravity_m_s2": sim.gravity_m_s2,
        "restitution": sim.restitution,
        "initial_height_m": sim.initial_height_m,
        "initial_velocity_m_s": sim.initial_velocity_m_s,
        "drag_coefficient_k": sim.drag_coefficient_k,
    }
    initial_state = {
        "position_m": sim.initial_height_m,
        "velocity_m_s": sim.initial_velocity_m_s,
        "bounces": 0,
    }
    measured = np.loadtxt(csv_path, delimiter=",", skiprows=1)
    direct_run = run_validation_for_model(
        BouncingBallModel(),
        params=params,
        measured_x=measured[:, 0],
        measured_y=measured[:, 1],
        y_field="position_m",
        initial_state=initial_state,
        dt_s=0.005,
    )
    assert metrics_via_controller.rmse == pytest.approx(direct_run.metrics.rmse, abs=1e-12)
    assert metrics_via_controller.max_abs_error == pytest.approx(
        direct_run.metrics.max_abs_error, abs=1e-12
    )
    assert metrics_via_controller.pearson_correlation == pytest.approx(
        direct_run.metrics.pearson_correlation, abs=1e-12
    )
    assert metrics_via_controller.n_samples == direct_run.metrics.n_samples


# ---------------------------------------------------------------------
# M3 — generic dispatch via physics_model_selected
# ---------------------------------------------------------------------


def _write_synthetic_fspl_csv(path: Path, *, freq_hz: float = 9.4e9) -> None:
    """Closed-form FSPL ``L = 20 log10(4 pi R / lambda)`` over a few ranges."""
    import math

    wavelength_m = 299_792_458.0 / freq_hz
    ranges = [100.0, 500.0, 1_000.0, 5_000.0, 10_000.0]
    losses = [20.0 * math.log10(4.0 * math.pi * r / wavelength_m) for r in ranges]
    rows = [f"{r:.6f},{loss:.6f}" for r, loss in zip(ranges, losses, strict=True)]
    path.write_text("range_m,loss_db\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_workspace_initial_current_physics_model_none(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.current_physics_model() is None


def test_workspace_tracks_selected_physics_model(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    from workbench.app.physics_lab import FreeSpaceLossModel

    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    ws.library_panel().select_label("Free-Space Path Loss  (rf_propagation)")
    model = ws.current_physics_model()
    assert model is not None
    assert isinstance(model, FreeSpaceLossModel)


def test_workspace_static_model_validation_dispatches_to_generic_layer(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    """Selecting Free-Space Path Loss + a matching FSPL CSV runs the
    generic Phase 9 M1 layer and produces tiny RMSE (closed-form match).
    """
    measured_root = tmp_path / "measured"
    measured_root.mkdir()
    _write_synthetic_fspl_csv(measured_root / "fspl.csv")
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured_root)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    ws.library_panel().select_label("Free-Space Path Loss  (rf_propagation)")
    measured_label = ws.library_panel().measured_category().child(0).text(0)
    ws.library_panel().select_label(measured_label)
    metrics = ws.last_validation_metrics()
    assert metrics is not None
    assert metrics.rmse == pytest.approx(0.0, abs=1e-6)
    assert metrics.n_samples == 5


def test_workspace_unknown_model_clears_metrics(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    """A custom plug-in with no default-fields mapping should not crash
    the workspace; instead the metrics state goes back to None.
    """

    class CustomModel:
        name = "Some Custom Plugin"
        category = "dynamics"
        time_mode = "dynamic"
        visualization = "2d"

        @property
        def parameters(self) -> tuple[()]:
            return ()

        def compute(self, state, params, dt_s):  # type: ignore[no-untyped-def]
            return {"y": 0.0}

    measured_root = tmp_path / "measured"
    measured_root.mkdir()
    _write_synthetic_drop_csv(measured_root / "drop.csv")
    ws = PhysicsLabWorkspace(
        enable_3d_viewer=False,
        measured_root=measured_root,
        physics_models=(CustomModel(),),  # type: ignore[arg-type]
    )
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    ws.library_panel().select_label("Some Custom Plugin  (dynamics)")
    measured_label = ws.library_panel().measured_category().child(0).text(0)
    ws.library_panel().select_label(measured_label)
    assert ws.last_validation_metrics() is None


def test_workspace_bouncing_ball_still_routes_to_legacy_path(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    """Selecting the BouncingBall row + measurement should keep using
    BouncingBallController.run_validation_from_dataset (the live
    simulator-state path), not the generic defaults path.
    """
    measured_root = tmp_path / "measured"
    measured_root.mkdir()
    _write_synthetic_drop_csv(measured_root / "drop.csv")
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured_root)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    ws.library_panel().select_label("Bouncing Ball  (dynamics)")
    measured_label = ws.library_panel().measured_category().child(0).text(0)
    ws.library_panel().select_label(measured_label)
    metrics = ws.last_validation_metrics()
    assert metrics is not None
    # Synthetic CSV uses the controller's default gravity + h0, so the
    # legacy path produces a small RMSE driven by the semi-implicit
    # Euler step's accumulated truncation error (the controller uses
    # dt=0.005 s; the CSV is a closed-form drop). 0.05 m on a 5 m drop
    # is generous headroom against floating drift between Python
    # versions while still catching gross regressions.
    assert metrics.rmse == pytest.approx(0.0, abs=5e-2)
