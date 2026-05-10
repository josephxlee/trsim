"""Simulation outer-layer toolbar (plan/05 section 5.5.1).

Layout (left to right):

``[Simulation:] [Start] [Pause] [Stop]   |   Speed ( x1  x2  x4  x8 )   actual: 3.7x``

Every Start/Pause/Stop button and every Speed radio routes through
:meth:`WorkbenchCommandRegistry.dispatch`, so the same wiring is
exercised whether the user clicks a button, picks the entry from the
palette, or presses a shortcut.

Phase 4.2b ships the **shell**: hooks default to no-ops in
:func:`workbench.ui.commands.builtin.register_builtin_commands` until
Phase 5 plugs the real :class:`SimulationClock` in. The ``actual: ...``
readout therefore starts blank and is updated by an external setter.
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QRadioButton,
    QToolBar,
    QWidget,
)

from workbench.ui.commands.builtin import SIM_SPEEDS
from workbench.ui.commands.registry import WorkbenchCommandRegistry


class SimulationToolbar(QToolBar):
    """Sim Start / Pause / Stop + Speed selector + actual readout."""

    def __init__(
        self,
        registry: WorkbenchCommandRegistry,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Simulation", parent)
        self.setObjectName("SimulationToolbar")
        self.setMovable(False)
        self._registry = registry

        self.addWidget(self._heading_label("Simulation:"))
        self._actions = self._add_lifecycle_actions()
        self.addSeparator()
        self.addWidget(self._heading_label("Speed"))
        self._speed_buttons, self._speed_group = self._add_speed_radios()
        self._actual_label = QLabel("actual: -", self)
        self._actual_label.setObjectName("SimActualRatio")
        self.addWidget(self._actual_label)

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    @staticmethod
    def _heading_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("padding: 0 6px; color: #888;")
        return lbl

    def _add_lifecycle_actions(self) -> dict[str, QAction]:
        actions: dict[str, QAction] = {}
        for command_id, label in (
            ("sim.start", "Start"),
            ("sim.pause", "Pause"),
            ("sim.stop", "Stop"),
        ):
            cmd = self._registry.get(command_id)
            act = QAction(label, self)
            act.setToolTip(cmd.title)
            if cmd.shortcut is not None:
                act.setShortcut(QKeySequence(cmd.shortcut))
            act.triggered.connect(lambda _checked, cid=command_id: self._registry.dispatch(cid))
            self.addAction(act)
            actions[command_id] = act
        return actions

    def _add_speed_radios(self) -> tuple[dict[int, QRadioButton], QButtonGroup]:
        group = QButtonGroup(self)
        group.setExclusive(True)
        buttons: dict[int, QRadioButton] = {}
        for multiplier in SIM_SPEEDS:
            btn = QRadioButton(f"x{multiplier}")
            btn.setObjectName(f"SimSpeed_x{multiplier}")
            cmd_id = f"sim.speed.x{multiplier}"
            btn.toggled.connect(
                lambda checked, cid=cmd_id: self._registry.dispatch(cid) if checked else None
            )
            self.addWidget(btn)
            group.addButton(btn)
            buttons[multiplier] = btn
        # Default to x1 without firing the dispatcher.
        buttons[1].blockSignals(True)
        buttons[1].setChecked(True)
        buttons[1].blockSignals(False)
        return buttons, group

    # ------------------------------------------------------------------
    # External setters (Phase 5 wiring will call these)
    # ------------------------------------------------------------------
    def set_actual_ratio(self, ratio: float | None) -> None:
        """Update the ``actual: ...`` label. ``None`` clears it to ``-``."""
        if ratio is None:
            self._actual_label.setText("actual: -")
        else:
            self._actual_label.setText(f"actual: {ratio:.1f}x")

    def set_selected_speed(self, multiplier: int) -> None:
        """Programmatic speed-radio selection without re-dispatch."""
        if multiplier not in self._speed_buttons:
            msg = f"unknown speed multiplier {multiplier!r}; expected one of {SIM_SPEEDS}"
            raise ValueError(msg)
        btn = self._speed_buttons[multiplier]
        btn.blockSignals(True)
        btn.setChecked(True)
        btn.blockSignals(False)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def lifecycle_action(self, command_id: str) -> QAction:
        """Return the QAction wired to ``command_id`` (test helper)."""
        return self._actions[command_id]

    def speed_button(self, multiplier: int) -> QRadioButton:
        """Return the speed radio for ``multiplier`` (test helper)."""
        return self._speed_buttons[multiplier]

    def actual_label(self) -> QLabel:
        """Return the ``actual: ...`` QLabel (test helper)."""
        return self._actual_label
