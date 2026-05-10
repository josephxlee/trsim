"""Target-Run inner-layer toolbar (plan/05 section 5.5.1).

Layout (left to right):

``[Target Run:] [Run] [Pause] [Stop]   |   State: IDLE``

Visually distinct from :class:`SimulationToolbar` because Target-Run is
the *inner* layer (plan/05 section 5.5.1, plan/14 v0.14): the user can
keep the simulation running and only restart targets.

Hook callables are no-ops at Phase 4.2b - Phase 5 wires
:class:`RunManager` in via :func:`workbench.ui.commands.builtin.register_builtin_commands`.
The state badge therefore starts at ``IDLE`` and is updated by an
external setter.
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QLabel, QToolBar, QWidget

from workbench.ui.commands.registry import WorkbenchCommandRegistry

_VALID_STATES: frozenset[str] = frozenset({"IDLE", "RUNNING", "PAUSED", "ENDED"})


class TargetRunToolbar(QToolBar):
    """Target Run / Pause / Stop + State badge."""

    def __init__(
        self,
        registry: WorkbenchCommandRegistry,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Target Run", parent)
        self.setObjectName("TargetRunToolbar")
        self.setMovable(False)
        self._registry = registry

        self.addWidget(self._heading_label("Target Run:"))
        self._actions = self._add_lifecycle_actions()
        self.addSeparator()
        self._state_label = QLabel("State: IDLE", self)
        self._state_label.setObjectName("TargetRunState")
        self._state_label.setStyleSheet("padding: 0 6px;")
        self.addWidget(self._state_label)

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
            ("target.run", "Run"),
            ("target.pause", "Pause"),
            ("target.stop", "Stop"),
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

    # ------------------------------------------------------------------
    # External setters (Phase 5 wiring will call this)
    # ------------------------------------------------------------------
    def set_state(self, state: str) -> None:
        """Update the state badge.

        Raises:
            ValueError: If ``state`` is not one of IDLE/RUNNING/PAUSED/ENDED.
        """
        if state not in _VALID_STATES:
            msg = f"unknown run state {state!r}; expected one of {sorted(_VALID_STATES)}"
            raise ValueError(msg)
        self._state_label.setText(f"State: {state}")

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def lifecycle_action(self, command_id: str) -> QAction:
        """Return the QAction wired to ``command_id`` (test helper)."""
        return self._actions[command_id]

    def state_label(self) -> QLabel:
        """Return the ``State: ...`` QLabel (test helper)."""
        return self._state_label
