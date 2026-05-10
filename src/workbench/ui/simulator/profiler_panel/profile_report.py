"""ProfileReport table (Phase 4.12, plan/18 § 18.17)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

PROFILE_REPORT_COLUMNS: tuple[str, ...] = ("Stage", "avg", "p50", "p95", "p99")


class ProfileReport(QWidget):
    """FrameTimingReport tabular view (one row per pipeline stage)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ProfileReport")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self._table = QTableWidget(0, len(PROFILE_REPORT_COLUMNS), self)
        self._table.setObjectName("ProfileReportTable")
        self._table.setHorizontalHeaderLabels(list(PROFILE_REPORT_COLUMNS))
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

    def set_rows(
        self,
        rows: list[tuple[str, float, float, float, float]],
    ) -> None:
        """Populate the table; each row = (stage, avg, p50, p95, p99) us."""
        self._table.setRowCount(len(rows))
        for row_idx, (stage, avg, p50, p95, p99) in enumerate(rows):
            self._table.setItem(row_idx, 0, QTableWidgetItem(stage))
            for col, value in enumerate((avg, p50, p95, p99), start=1):
                item = QTableWidgetItem(f"{value:.1f}")
                self._table.setItem(row_idx, col, item)

    def clear(self) -> None:
        self._table.setRowCount(0)

    def table(self) -> QTableWidget:
        return self._table
