"""Run metrics panel (Phase 4.9, plan/05 § 5.3.6) + L1 live-sim readout.

Phase 4 L1 (2026-05-13) adds a "Simulation Time" group above the
primary-target metrics. The new group shows the live ``SimulationClock``
state — ``sim_t_s`` / ``frame_id`` / state label / current speed —
that :class:`workbench.ui.simulator.run_controller.SimulatorRunController`
(L1b) drives on every QTimer tick. Before L1 the panel was a fully
inert placeholder; tests now assert on the live-sim API.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from workbench.domain.types import SimulationState, SpeedMultiplier


class RunPanel(QWidget):
    """Primary-target metrics + history list shell."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RunPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self._build_sim_time_block())

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_history_block(), 0)
        body.addWidget(self._build_primary_block(), 1)
        layout.addLayout(body)

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_sim_time_block(self) -> QGroupBox:
        box = QGroupBox("Simulation Time", self)
        box.setObjectName("RunPanelSimTime")
        form = QFormLayout(box)
        self._sim_time_label = QLabel("0.000 s")
        self._sim_time_label.setObjectName("RunPanelSimTime_t")
        self._frame_id_label = QLabel("0")
        self._frame_id_label.setObjectName("RunPanelSimTime_frame")
        self._state_label = QLabel(SimulationState.STOPPED.value)
        self._state_label.setObjectName("RunPanelSimTime_state")
        self._speed_label = QLabel("x1")
        self._speed_label.setObjectName("RunPanelSimTime_speed")
        form.addRow("sim_t", self._sim_time_label)
        form.addRow("frame", self._frame_id_label)
        form.addRow("state", self._state_label)
        form.addRow("speed", self._speed_label)
        return box

    def _build_history_block(self) -> QGroupBox:
        box = QGroupBox("Run History", self)
        box.setObjectName("RunPanelHistory")
        box.setMinimumWidth(180)
        v = QVBoxLayout(box)
        self._history_list = QListWidget(box)
        self._history_list.setObjectName("RunPanelHistoryList")
        v.addWidget(self._history_list, 1)
        return box

    def _build_primary_block(self) -> QGroupBox:
        box = QGroupBox("Primary Target", self)
        box.setObjectName("RunPanelPrimary")
        form = QFormLayout(box)
        self._lock_label = QLabel("--")
        self._lock_label.setObjectName("RunPanelLock")
        self._continuity_label = QLabel("--")
        self._continuity_label.setObjectName("RunPanelContinuity")
        self._id_switch_label = QLabel("--")
        self._id_switch_label.setObjectName("RunPanelIDSwitch")
        self._range_rmse_label = QLabel("--")
        self._range_rmse_label.setObjectName("RunPanelRangeRMSE")
        self._az_rmse_label = QLabel("--")
        self._az_rmse_label.setObjectName("RunPanelAzRMSE")
        self._lag_label = QLabel("--")
        self._lag_label.setObjectName("RunPanelPositionerLag")
        form.addRow("Lock", self._lock_label)
        form.addRow("Track continuity", self._continuity_label)
        form.addRow("ID switches", self._id_switch_label)
        form.addRow("Range RMSE", self._range_rmse_label)
        form.addRow("AZ RMSE", self._az_rmse_label)
        form.addRow("Positioner lag", self._lag_label)
        return box

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_history(self, run_ids: list[str]) -> None:
        self._history_list.clear()
        for rid in run_ids:
            self._history_list.addItem(rid)

    def set_primary_metrics(
        self,
        *,
        lock: str,
        continuity: float,
        id_switches: int,
        range_rmse_m: float,
        az_rmse_deg: float,
        positioner_lag_deg: float,
    ) -> None:
        self._lock_label.setText(lock)
        self._continuity_label.setText(f"{continuity:.2f}")
        self._id_switch_label.setText(str(id_switches))
        self._range_rmse_label.setText(f"{range_rmse_m:.2f} m")
        self._az_rmse_label.setText(f"{az_rmse_deg:.2f} deg")
        self._lag_label.setText(f"{positioner_lag_deg:.2f} deg")

    def set_sim_time(self, sim_t_s: float, frame_id: int) -> None:
        """Update the live SimulationClock readout (Phase 4 L1).

        Args:
            sim_t_s: Current simulation time [s], non-negative.
            frame_id: Monotonic frame counter, >= 0.

        Raises:
            ValueError: If ``sim_t_s`` is negative or ``frame_id`` is < 0.
        """
        if sim_t_s < 0.0:
            msg = f"sim_t_s must be non-negative, got {sim_t_s}"
            raise ValueError(msg)
        if frame_id < 0:
            msg = f"frame_id must be non-negative, got {frame_id}"
            raise ValueError(msg)
        self._sim_time_label.setText(f"{sim_t_s:.3f} s")
        self._frame_id_label.setText(str(frame_id))

    def set_sim_state(self, state: SimulationState) -> None:
        """Update the state readout (Phase 4 L1)."""
        self._state_label.setText(state.value)

    def set_sim_speed(self, speed: SpeedMultiplier) -> None:
        """Update the speed multiplier readout (Phase 4 L1)."""
        self._speed_label.setText(f"x{int(speed.value)}")

    def history_list(self) -> QListWidget:
        return self._history_list

    def lock_label(self) -> QLabel:
        return self._lock_label

    def continuity_label(self) -> QLabel:
        return self._continuity_label

    def sim_time_label(self) -> QLabel:
        return self._sim_time_label

    def frame_id_label(self) -> QLabel:
        return self._frame_id_label

    def sim_state_label(self) -> QLabel:
        return self._state_label

    def sim_speed_label(self) -> QLabel:
        return self._speed_label
