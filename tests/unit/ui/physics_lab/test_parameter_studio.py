"""Parameter Studio controller + workspace tests (PL-9.2d)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")
pytest.importorskip("scipy")

from workbench.app.physics_lab import BouncingBallSimulator, FitConfig, FitResult
from workbench.domain.physics_lab import inspect_csv
from workbench.ui.physics_lab import LibraryWidget, PhysicsLabWorkspace

pytestmark = pytest.mark.qt


def _write_trajectory_csv(
    path: Path,
    *,
    restitution: float = 0.5,
    drag: float = 0.0,
    height: float = 5.0,
    duration_s: float = 2.0,
    dt_s: float = 0.005,
) -> None:
    sim = BouncingBallSimulator(
        restitution=restitution,
        initial_height_m=height,
        drag_coefficient_k=drag,
    )
    n_steps = max(2, int(np.ceil(duration_s / dt_s)) + 1)
    rows = [f"{sim.state.time_s:.6f},{sim.state.position_m:.6f}"]
    for _ in range(1, n_steps):
        s = sim.step(dt_s)
        rows.append(f"{s.time_s:.6f},{s.position_m:.6f}")
    path.write_text("time_s,position_m\n" + "\n".join(rows) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------
# LibraryWidget — fit button + signal
# ---------------------------------------------------------------------


def test_library_fit_button_disabled_by_default(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    assert lib.fit_button().isEnabled() is False


def test_library_fit_button_enables_on_measured_selection(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    measured_root = tmp_path / "m"
    measured_root.mkdir()
    _write_trajectory_csv(measured_root / "drop.csv")
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured_root)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    cat = ws.library_panel().measured_category()
    ws.library_panel().select_label(cat.child(0).text(0))
    assert ws.library_panel().fit_button().isEnabled() is True


def test_library_fit_button_disabled_on_non_measured_selection(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    measured_root = tmp_path / "m"
    measured_root.mkdir()
    _write_trajectory_csv(measured_root / "drop.csv")
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured_root)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    cat = ws.library_panel().measured_category()
    ws.library_panel().select_label(cat.child(0).text(0))
    assert ws.library_panel().fit_button().isEnabled() is True
    # Switch back to Bouncing Ball -> disabled.
    ws.library_panel().select_label(LibraryWidget.BOUNCING_BALL_ROW)
    assert ws.library_panel().fit_button().isEnabled() is False


# ---------------------------------------------------------------------
# Controller fit_to_measurement
# ---------------------------------------------------------------------


def test_fit_to_measurement_recovers_restitution(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_trajectory_csv(csv_path, restitution=0.5)
    dataset = inspect_csv(csv_path)
    # Move the live simulator off-target so fitting has work to do.
    ws.bouncing_ball_controller().reset_with(restitution=0.85)
    result = ws.bouncing_ball_controller().fit_to_measurement(dataset)
    assert isinstance(result, FitResult)
    assert result.fitted_restitution == pytest.approx(0.5, abs=0.05)


def test_fit_to_measurement_applies_to_live_simulator(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_trajectory_csv(csv_path, restitution=0.5)
    dataset = inspect_csv(csv_path)
    ws.bouncing_ball_controller().reset_with(restitution=0.85)
    result = ws.bouncing_ball_controller().fit_to_measurement(dataset)
    assert ws.bouncing_ball_controller().simulator.restitution == pytest.approx(
        result.fitted_restitution
    )


def test_fit_to_measurement_inspect_only_does_not_mutate_simulator(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_trajectory_csv(csv_path, restitution=0.5)
    dataset = inspect_csv(csv_path)
    controller = ws.bouncing_ball_controller()
    controller.reset_with(restitution=0.85)
    before_r = controller.simulator.restitution
    controller.fit_to_measurement(dataset, apply_to_live_state=False)
    assert controller.simulator.restitution == pytest.approx(before_r)


def test_fit_result_ready_signal_fires(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drop.csv"
    _write_trajectory_csv(csv_path)
    dataset = inspect_csv(csv_path)
    received: list[FitResult] = []
    ws.bouncing_ball_controller().fit_result_ready.connect(received.append)
    ws.bouncing_ball_controller().fit_to_measurement(dataset)
    assert len(received) == 1


def test_fit_two_parameters_both_in_config(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    csv_path = tmp_path / "drag.csv"
    _write_trajectory_csv(csv_path, restitution=0.5, drag=0.1, duration_s=2.0)
    dataset = inspect_csv(csv_path)
    ws.bouncing_ball_controller().reset_with(restitution=0.9, drag_coefficient_k=0.0)
    result = ws.bouncing_ball_controller().fit_to_measurement(
        dataset,
        config=FitConfig(fit_restitution=True, fit_drag_coefficient_k=True),
        max_iter=400,
    )
    assert result.final_rmse < 0.2


# ---------------------------------------------------------------------
# Workspace fit_requested integration
# ---------------------------------------------------------------------


def test_workspace_fit_requested_triggers_fit(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    measured_root = tmp_path / "m"
    measured_root.mkdir()
    _write_trajectory_csv(measured_root / "drop.csv", restitution=0.4)
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured_root)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    # Move live state off-target.
    ws.bouncing_ball_controller().reset_with(restitution=0.9)
    cat = ws.library_panel().measured_category()
    label = cat.child(0).text(0)
    ws.library_panel().select_label(label)
    ws.library_panel().fit_button().click()
    result = ws.last_fit_result()
    assert result is not None
    assert result.fitted_restitution == pytest.approx(0.4, abs=0.05)


def test_workspace_fit_updates_parameters_pane(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    measured_root = tmp_path / "m"
    measured_root.mkdir()
    _write_trajectory_csv(measured_root / "drop.csv", restitution=0.3)
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured_root)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    ws.bouncing_ball_controller().reset_with(restitution=0.9)
    cat = ws.library_panel().measured_category()
    ws.library_panel().select_label(cat.child(0).text(0))
    ws.library_panel().fit_button().click()
    # Restitution slider readout now matches the fitted value (within
    # the 100-tick quantisation of the auto-slider).
    fitted_r = ws.parameters_panel().auto_parameters().current_value("restitution")
    target_r = ws.last_fit_result().fitted_restitution  # type: ignore[union-attr]
    assert fitted_r == pytest.approx(target_r, abs=0.05)


def test_workspace_initial_fit_state_none(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.last_fit_result() is None


def test_workspace_fit_status_text_includes_rmse(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    measured_root = tmp_path / "m"
    measured_root.mkdir()
    _write_trajectory_csv(measured_root / "drop.csv", restitution=0.5)
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured_root)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    cat = ws.library_panel().measured_category()
    ws.library_panel().select_label(cat.child(0).text(0))
    ws.library_panel().fit_button().click()
    status = ws.time_controls().status_label().text()
    assert "fit:" in status
    assert "RMSE" in status
