"""Bouncing Ball demo widgets (PL-D, plan/19 § 19.12.1).

Drop-in replacements for the PL-B placeholder panes:

- :class:`LibraryWidget` — QListWidget showing the 9 Test Objects
  (Sphere / Cube / ...) plus the synthetic "Bouncing Ball Demo" row.
- :class:`CodePreview` — read-only QTextEdit dumping the source of
  the :meth:`BouncingBallSimulator.step` method so the user can read
  the formula driving the visualisation.
- :class:`BouncingBallPlot` — pyqtgraph PlotWidget rendering the
  ``y(t)`` trajectory in real time. ``set_history(times, ys)``
  redraws the curve; ``clear_history()`` resets the buffer.
- :class:`ParametersWidget` — single Restitution slider 0..1, emits
  ``restitution_changed(float)``.
- :class:`BouncingBallController` — wires the workspace's time
  controls + Parameters + Visualization + PhysicsClock +
  BouncingBallSimulator. Owns the QTimer that drives Run mode.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable

import pyqtgraph as pg
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from workbench.app.physics_lab import BouncingBallSimulator, PhysicsClock
from workbench.domain.physics_lab import default_library

# ---------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------


class LibraryWidget(QWidget):
    """Sidebar list of Saved Tests + the 9 Test Objects.

    Selecting "Bouncing Ball Demo" tells the controller to attach to
    the live simulator (the only interactive option in PL-D). The 9
    Test Object rows are read-only for the MVP — Phase 9.1 will
    couple them to dedicated demos.

    Signals:
        demo_selected: ``str`` row text, emitted on selection change.
    """

    demo_selected = Signal(str)
    BOUNCING_BALL_ROW = "Bouncing Ball Demo"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLab_LibraryWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("Library", self)
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        self._list = QListWidget(self)
        self._list.setObjectName("PhysicsLab_LibraryList")
        # Active demo first, Test Object catalogue after (read-only).
        QListWidgetItem(self.BOUNCING_BALL_ROW, self._list)
        for obj in default_library():
            item = QListWidgetItem(f"{obj.name}  ({obj.visual})", self._list)
            item.setData(0x0100, obj.name)
        self._list.currentTextChanged.connect(self.demo_selected.emit)
        self._list.setCurrentRow(0)
        layout.addWidget(self._list, 1)

    def list_widget(self) -> QListWidget:
        return self._list


# ---------------------------------------------------------------------
# Code preview
# ---------------------------------------------------------------------


class CodePreview(QWidget):
    """Read-only dump of the active simulator's ``step`` source.

    PL-D shows :meth:`BouncingBallSimulator.step` so the user can see
    the formula behind the trajectory. Phase 9.3 layers an Edit mode
    + Plugin Authoring on top.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLab_CodePreview")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("Code (BouncingBallSimulator.step)", self)
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        self._editor = QTextEdit(self)
        self._editor.setObjectName("PhysicsLab_CodeEditor")
        self._editor.setReadOnly(True)
        self._editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._editor.setFontFamily("Consolas")
        try:
            src = inspect.getsource(BouncingBallSimulator.step)
        except (OSError, TypeError):
            src = "# source unavailable in this environment"
        self._editor.setPlainText(src)
        layout.addWidget(self._editor, 1)

    def editor(self) -> QTextEdit:
        return self._editor


# ---------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------


class BouncingBallPlot(QWidget):
    """pyqtgraph plot of ``y(t)`` (height in metres vs. time in seconds)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLab_BouncingBallPlot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("Visualization — y(t) trajectory", self)
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        self._plot = pg.PlotWidget(self)
        self._plot.setObjectName("PhysicsLab_BouncingBallPlotWidget")
        self._plot.setLabel("left", "height", units="m")
        self._plot.setLabel("bottom", "time", units="s")
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._curve = self._plot.plot([], [], pen=pg.mkPen(width=2))
        layout.addWidget(self._plot, 1)

        self._times: list[float] = []
        self._ys: list[float] = []

    def append(self, time_s: float, y_m: float) -> None:
        """Append one (t, y) sample and redraw."""
        self._times.append(time_s)
        self._ys.append(y_m)
        self._curve.setData(self._times, self._ys)

    def set_history(self, times: Iterable[float], ys: Iterable[float]) -> None:
        self._times = list(times)
        self._ys = list(ys)
        self._curve.setData(self._times, self._ys)

    def clear_history(self) -> None:
        self._times.clear()
        self._ys.clear()
        self._curve.setData([], [])

    def history_length(self) -> int:
        return len(self._times)

    def plot_widget(self) -> pg.PlotWidget:
        return self._plot


# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------


_RESTITUTION_TICKS: int = 100


class ParametersWidget(QWidget):
    """Restitution slider 0..1 (1 % steps).

    plan/19 § 19.5.5 will auto-generate this from a
    ``@physics_param(0.0, 1.0)`` decorator in Phase 9.3; the MVP
    ships a hand-wired slider for the single Bouncing Ball
    parameter.
    """

    restitution_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLab_ParametersWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("Parameters", self)
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        form = QFormLayout()
        self._slider = QSlider(parent=self)
        self._slider.setObjectName("PhysicsLab_RestitutionSlider")
        from PySide6.QtCore import Qt

        self._slider.setOrientation(Qt.Orientation.Horizontal)
        self._slider.setRange(0, _RESTITUTION_TICKS)
        self._slider.setValue(70)  # 0.70 default
        self._readout = QLabel("0.70", self)
        self._readout.setObjectName("PhysicsLab_RestitutionReadout")
        self._slider.valueChanged.connect(self._on_slider_value)

        row = QHBoxLayout()
        row.addWidget(self._slider, 1)
        row.addWidget(self._readout)
        form.addRow("Restitution", row)
        layout.addLayout(form)
        layout.addStretch(1)

    def _on_slider_value(self, tick: int) -> None:
        value = tick / _RESTITUTION_TICKS
        self._readout.setText(f"{value:.2f}")
        self.restitution_changed.emit(value)

    def current_restitution(self) -> float:
        return self._slider.value() / _RESTITUTION_TICKS

    def set_restitution(self, value: float) -> None:
        clamped = max(0.0, min(1.0, value))
        self._slider.setValue(round(clamped * _RESTITUTION_TICKS))

    def slider(self) -> QSlider:
        return self._slider


# ---------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------


class BouncingBallController(QObject):
    """Wires PhysicsLab time controls + parameters + viz to the simulator.

    Attributes:
        simulator: The :class:`BouncingBallSimulator` instance.
        clock: The :class:`PhysicsClock` driving Run mode.

    The controller does not own the widgets — it borrows references
    so SimulatorWorkspace-style swap-outs stay possible.
    """

    def __init__(
        self,
        *,
        plot: BouncingBallPlot,
        parameters: ParametersWidget,
        play_button: QPushButton,
        pause_button: QPushButton,
        stop_button: QPushButton,
        status_label: QLabel,
        clock_dt_s: float = 0.02,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.simulator = BouncingBallSimulator(restitution=parameters.current_restitution())
        self.clock = PhysicsClock(dt_s=clock_dt_s)
        self._plot = plot
        self._parameters = parameters
        self._play_btn = play_button
        self._pause_btn = pause_button
        self._stop_btn = stop_button
        self._status = status_label

        self._timer = QTimer(self)
        # Slightly faster than the dt so play is smooth without
        # overrunning the wall clock.
        self._timer.setInterval(max(1, int(clock_dt_s * 1000)))
        self._timer.timeout.connect(self._on_timer_tick)

        self._play_btn.clicked.connect(self.play)
        self._pause_btn.clicked.connect(self.pause)
        self._stop_btn.clicked.connect(self.stop)
        self._parameters.restitution_changed.connect(self.simulator.set_restitution)

        # Seed the plot with the initial state at t=0 so the user
        # sees the ball position even before pressing Play.
        self._plot.append(self.simulator.state.time_s, self.simulator.state.position_m)
        self._refresh_status()

    # ------------------------------------------------------------------
    # Transport slots
    # ------------------------------------------------------------------

    def play(self) -> None:
        self.clock.start()
        self._timer.start()
        self._refresh_status()

    def pause(self) -> None:
        self.clock.pause()
        self._timer.stop()
        self._refresh_status()

    def stop(self) -> None:
        self.clock.stop()
        self._timer.stop()
        self.simulator.reset()
        self._plot.clear_history()
        self._plot.append(self.simulator.state.time_s, self.simulator.state.position_m)
        self._refresh_status()

    # ------------------------------------------------------------------
    # Tick path
    # ------------------------------------------------------------------

    def _on_timer_tick(self) -> None:
        tick = self.clock.tick()
        if tick is None:
            return
        state = self.simulator.step(tick.dt_s)
        self._plot.append(state.time_s, state.position_m)
        self._refresh_status()

    def step_once(self, dt_s: float | None = None) -> None:
        """Headless single step — tests drive this directly so they
        don't have to spin a real QTimer.
        """
        step = dt_s if dt_s is not None else self.clock.dt_s
        self.clock.start()
        ev = self.clock.tick()
        if ev is None:
            return
        state = self.simulator.step(step if dt_s is not None else ev.dt_s)
        self._plot.append(state.time_s, state.position_m)
        self._refresh_status()

    # ------------------------------------------------------------------
    # UI surface
    # ------------------------------------------------------------------

    def _refresh_status(self) -> None:
        s = self.simulator.state
        verb = "running" if self.clock.is_running else "paused"
        self._status.setText(
            f"{verb}  t={s.time_s:.2f}s  y={s.position_m:.2f}m  "
            f"v={s.velocity_m_s:.2f}m/s  bounces={s.bounces}"
        )
