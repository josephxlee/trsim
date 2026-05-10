"""Run metrics panel (Phase 4.9, plan/05 § 5.3.6)."""

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


class RunPanel(QWidget):
    """Primary-target metrics + history list shell."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RunPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_history_block(), 0)
        body.addWidget(self._build_primary_block(), 1)
        layout.addLayout(body)

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
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

    def history_list(self) -> QListWidget:
        return self._history_list

    def lock_label(self) -> QLabel:
        return self._lock_label

    def continuity_label(self) -> QLabel:
        return self._continuity_label
