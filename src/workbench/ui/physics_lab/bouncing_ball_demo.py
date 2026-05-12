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

import ast
import inspect
from collections.abc import Iterable

import pyqtgraph as pg
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
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

from workbench.app.physics_lab import (
    BouncingBallSimulator,
    BouncingBallState,
    PhysicsClock,
)
from workbench.domain.physics_lab import (
    BOUNCING_BALL_PARAM_SPECS,
    default_library,
)
from workbench.ui.physics_lab.auto_parameters import AutoParametersWidget
from workbench.ui.physics_lab.python_highlighter import PythonSyntaxHighlighter

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


_DEFAULT_USER_STEP: str = '''def step(simulator, dt_s):
    """User-editable replacement for BouncingBallSimulator.step.

    PL-E Code edit mode entry point. ``simulator`` is the live
    BouncingBallSimulator instance; ``dt_s`` is the timestep in
    seconds. Mutate state through ``simulator.update_state(new_state)``
    so the workspace + plot pick up the change.

    The default body below mirrors the built-in semi-implicit Euler
    step. Modify it to experiment — air drag, variable gravity,
    floor below 0, etc. — then click Save & Reload.
    """
    from workbench.app.physics_lab import BouncingBallState

    s = simulator.state
    new_v = s.velocity_m_s - simulator.gravity_m_s2 * dt_s
    new_y = s.position_m + new_v * dt_s
    new_bounces = s.bounces
    if new_y <= 0.0:
        new_y = 0.0
        new_v = -new_v * simulator.restitution
        if abs(new_v) < 1e-3:
            new_v = 0.0
        new_bounces += 1
    simulator.update_state(BouncingBallState(
        time_s=s.time_s + dt_s,
        position_m=new_y,
        velocity_m_s=new_v,
        bounces=new_bounces,
    ))
'''


class CodePreview(QWidget):
    """Editable view of the active simulator's ``step`` source (PL-E).

    Three modes:

    - **Read** (default): the source is the verbatim built-in step
      dumped via :func:`inspect.getsource`. The editor is read-only;
      the background is the system default.
    - **Edit**: the user can modify the text. The editor turns
      writable and the background tints to make the mode visible.
    - **Saved**: after Save & Reload, the user-edited function is
      compiled + plugged into the simulator. The editor stays in
      Edit mode but the controller's ``code_status`` reports either
      "applied" or the error message that surfaced.

    Signals:
        save_requested: emitted with the current editor text when the
            user clicks "Save & Reload". The controller compiles +
            installs the function and reports back via
            ``set_status``.
        revert_requested: clear the override, restore the original
            source.
    """

    save_requested = Signal(str)
    revert_requested = Signal()

    _READ_STYLE: str = ""
    _EDIT_STYLE: str = "background-color: rgba(120, 180, 120, 32);"

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
        # PL-9.1a — install Python syntax highlighter on the document.
        # Read-mode shows the built-in step source coloured; Edit-mode
        # keeps the colours so the user can still navigate the source
        # they are editing.
        self._highlighter = PythonSyntaxHighlighter(self._editor.document())
        try:
            self._builtin_src = inspect.getsource(BouncingBallSimulator.step)
        except (OSError, TypeError):
            self._builtin_src = "# source unavailable in this environment"
        self._editor.setPlainText(self._builtin_src)
        layout.addWidget(self._editor, 1)

        # Action row — Edit toggle + Save & Reload + Revert + status.
        actions = QHBoxLayout()
        self._edit_btn = QPushButton("Edit", self)
        self._edit_btn.setObjectName("PhysicsLab_CodeEditBtn")
        self._edit_btn.setCheckable(True)
        self._edit_btn.toggled.connect(self._on_edit_toggled)
        self._save_btn = QPushButton("Save && Reload", self)
        self._save_btn.setObjectName("PhysicsLab_CodeSaveBtn")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._revert_btn = QPushButton("Revert", self)
        self._revert_btn.setObjectName("PhysicsLab_CodeRevertBtn")
        self._revert_btn.setEnabled(False)
        self._revert_btn.clicked.connect(self._on_revert_clicked)
        self._status_label = QLabel("read-only — click Edit to modify", self)
        self._status_label.setObjectName("PhysicsLab_CodeStatusLabel")
        self._status_label.setStyleSheet("color: #777;")

        for btn in (self._edit_btn, self._save_btn, self._revert_btn):
            actions.addWidget(btn)
        actions.addWidget(self._status_label, 1)
        layout.addLayout(actions)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def editor(self) -> QTextEdit:
        return self._editor

    def edit_button(self) -> QPushButton:
        return self._edit_btn

    def save_button(self) -> QPushButton:
        return self._save_btn

    def revert_button(self) -> QPushButton:
        return self._revert_btn

    def status_label(self) -> QLabel:
        return self._status_label

    def highlighter(self) -> PythonSyntaxHighlighter:
        return self._highlighter

    def is_editing(self) -> bool:
        return self._edit_btn.isChecked()

    def current_source(self) -> str:
        return self._editor.toPlainText()

    def builtin_source(self) -> str:
        return self._builtin_src

    def reset_to_builtin(self) -> None:
        """Public re-revert hook for the controller.

        The override on the simulator is cleared by the controller —
        this method only refreshes the editor body. We use
        :data:`_DEFAULT_USER_STEP` instead of the raw
        ``inspect.getsource`` dump because the latter is a *method*
        with 4-space indent + ``self`` arg, which is not valid
        module-level Python and would crash ``exec`` if the user
        clicks Save & Reload again. The scaffold mirrors the same
        physics but in standalone-function form.
        """
        self._editor.setPlainText(_DEFAULT_USER_STEP)
        # Drop back to read-only so the user is not staring at an
        # editable body that just got swapped under them — the
        # controller posts a green "reverted" status right after.
        if self._edit_btn.isChecked():
            self._edit_btn.setChecked(False)

    def set_status(self, message: str, *, ok: bool = True) -> None:
        """Controller posts compile / install results here."""
        colour = "#5aa86e" if ok else "#d36a6a"
        self._status_label.setStyleSheet(f"color: {colour};")
        self._status_label.setText(message)

    def fill_with_default_user_step(self) -> None:
        """Replace the read-only built-in dump with the editable
        scaffold the user starts from. Called automatically on first
        Edit click.
        """
        self._editor.setPlainText(_DEFAULT_USER_STEP)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_edit_toggled(self, checked: bool) -> None:
        self._editor.setReadOnly(not checked)
        self._editor.setStyleSheet(self._EDIT_STYLE if checked else self._READ_STYLE)
        self._save_btn.setEnabled(checked)
        self._revert_btn.setEnabled(checked)
        if checked:
            # Swap the built-in dump for the editable scaffold the
            # first time the user enters Edit mode so they have a
            # working starting point.
            if self._editor.toPlainText().strip() == self._builtin_src.strip():
                self.fill_with_default_user_step()
            self._status_label.setStyleSheet("color: #777;")
            self._status_label.setText("editing — modify, then Save && Reload")
            self._edit_btn.setText("Editing")
        else:
            self._edit_btn.setText("Edit")
            self._status_label.setStyleSheet("color: #777;")
            self._status_label.setText("read-only — click Edit to modify")

    def _on_save_clicked(self) -> None:
        self.save_requested.emit(self._editor.toPlainText())

    def _on_revert_clicked(self) -> None:
        self.revert_requested.emit()


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


class ParametersWidget(QWidget):
    """Bouncing Ball parameter pane (PL-9.1c).

    Wraps :class:`AutoParametersWidget` configured with
    :data:`BOUNCING_BALL_PARAM_SPECS` (gravity / restitution /
    initial-height / initial-velocity, four sliders auto-generated
    from ``@physics_param`` metadata).

    Backward-compatible API for the original restitution-only PL-D
    surface:

    Signals:
        restitution_changed(float): emitted whenever the restitution
            slider moves. Fires only for the ``restitution`` row of
            the underlying :class:`AutoParametersWidget`.
        parameter_changed(str, float): pass-through of the underlying
            widget's signal (PL-9.1c) — exposes every slider.

    Methods:
        :meth:`current_restitution` / :meth:`set_restitution` /
        :meth:`slider` retain their PL-D behaviour. :meth:`auto_parameters`
        returns the underlying widget so callers can wire the other
        sliders (e.g. gravity) to simulator setters.
    """

    restitution_changed = Signal(float)
    parameter_changed = Signal(str, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLab_ParametersWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._auto = AutoParametersWidget(BOUNCING_BALL_PARAM_SPECS, parent=self)
        layout.addWidget(self._auto)
        self._auto.parameter_changed.connect(self._on_auto_changed)

    def _on_auto_changed(self, name: str, value: float) -> None:
        self.parameter_changed.emit(name, value)
        if name == "restitution":
            self.restitution_changed.emit(value)

    def auto_parameters(self) -> AutoParametersWidget:
        return self._auto

    def current_restitution(self) -> float:
        return self._auto.current_value("restitution")

    def set_restitution(self, value: float) -> None:
        # Public clamping behaviour from PL-D — set_value already
        # clamps internally, but we keep the explicit ``[0, 1]`` clamp
        # so callers don't have to know the underlying spec bounds.
        clamped = max(0.0, min(1.0, value))
        self._auto.set_value("restitution", clamped)

    def slider(self) -> QSlider:
        return self._auto.slider_for("restitution")


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
        code_preview: CodePreview | None = None,
        frame_slider: QSlider | None = None,
        step_back_button: QPushButton | None = None,
        step_forward_button: QPushButton | None = None,
        frame_readout: QLabel | None = None,
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
        self._code_preview = code_preview
        self._frame_slider = frame_slider
        self._step_back_btn = step_back_button
        self._step_fwd_btn = step_forward_button
        self._frame_readout = frame_readout

        # PL-9.1b — frame history. Each call to ``step_forward_once`` /
        # the play timer appends one :class:`BouncingBallState`; the
        # user can rewind via ``step_backward_once`` or jump anywhere
        # via the frame slider. ``_history_index`` points to the state
        # currently mirrored on the simulator + plot.
        self._history: list[BouncingBallState] = [self.simulator.state]
        self._history_index: int = 0

        self._timer = QTimer(self)
        # Slightly faster than the dt so play is smooth without
        # overrunning the wall clock.
        self._timer.setInterval(max(1, int(clock_dt_s * 1000)))
        self._timer.timeout.connect(self._on_timer_tick)

        self._play_btn.clicked.connect(self.play)
        self._pause_btn.clicked.connect(self.pause)
        self._stop_btn.clicked.connect(self.stop)
        self._parameters.restitution_changed.connect(self.simulator.set_restitution)

        # PL-E — Code edit hooks. When the CodePreview emits save /
        # revert, we compile or restore the override.
        if self._code_preview is not None:
            self._code_preview.save_requested.connect(self.apply_user_step_code)
            self._code_preview.revert_requested.connect(self.revert_user_step_code)

        # PL-9.1b — frame controls. All four widgets are optional so
        # tests + headless callers can construct a controller without
        # them; the workspace always passes the full quartet.
        if self._step_back_btn is not None:
            self._step_back_btn.clicked.connect(self.step_backward_once)
        if self._step_fwd_btn is not None:
            self._step_fwd_btn.clicked.connect(self.step_forward_once)
        if self._frame_slider is not None:
            self._frame_slider.setRange(0, 0)
            self._frame_slider.setValue(0)
            self._frame_slider.valueChanged.connect(self._on_frame_slider_changed)

        # Seed the plot with the initial state at t=0 so the user
        # sees the ball position even before pressing Play.
        self._plot.append(self.simulator.state.time_s, self.simulator.state.position_m)
        self._refresh_frame_ui()
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
        self._history = [self.simulator.state]
        self._history_index = 0
        self._plot.clear_history()
        self._plot.append(self.simulator.state.time_s, self.simulator.state.position_m)
        self._refresh_frame_ui()
        self._refresh_status()

    # ------------------------------------------------------------------
    # Frame history surface (PL-9.1b)
    # ------------------------------------------------------------------

    @property
    def history(self) -> tuple[BouncingBallState, ...]:
        """Immutable snapshot of all frames generated since the last reset."""
        return tuple(self._history)

    @property
    def current_frame_index(self) -> int:
        """Index of the state currently shown on the simulator and plot."""
        return self._history_index

    def step_forward_once(self) -> None:
        """Move one frame forward.

        If the cursor is in the middle of an existing history, replay
        the next stored state. Otherwise generate a new frame by
        running :meth:`BouncingBallSimulator.step` and append it.
        """
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self._apply_history_at_cursor()
        else:
            self._advance_one_frame(self.clock.dt_s)

    def step_backward_once(self) -> None:
        """Move one frame backward (no-op at frame 0).

        Backward stepping never mutates the history list — the future
        frames stay around so the user can scrub forward again. The
        plot redraws to show only frames up to the new cursor.
        """
        if self._history_index > 0:
            self._history_index -= 1
            self._apply_history_at_cursor()

    def seek_to_frame(self, frame_index: int) -> None:
        """Jump the cursor to ``frame_index`` (clamped to history)."""
        if not self._history:
            return
        clamped = max(0, min(len(self._history) - 1, frame_index))
        if clamped == self._history_index:
            return
        self._history_index = clamped
        self._apply_history_at_cursor()

    def _apply_history_at_cursor(self) -> None:
        state = self._history[self._history_index]
        self.simulator.update_state(state)
        past = self._history[: self._history_index + 1]
        self._plot.set_history(
            [s.time_s for s in past],
            [s.position_m for s in past],
        )
        self._refresh_frame_ui()
        self._refresh_status()

    def _advance_one_frame(self, dt_s: float) -> None:
        """Generate and adopt one new frame.

        If the cursor was mid-history (because the user stepped back
        and then resumed Play / Step Forward), the future frames are
        discarded — Play branches a new timeline from the cursor.
        """
        if self._history_index < len(self._history) - 1:
            self._history = self._history[: self._history_index + 1]
            past = self._history
            self._plot.set_history(
                [s.time_s for s in past],
                [s.position_m for s in past],
            )
        state = self.simulator.step(dt_s)
        self._history.append(state)
        self._history_index = len(self._history) - 1
        self._plot.append(state.time_s, state.position_m)
        self._refresh_frame_ui()
        self._refresh_status()

    def _on_frame_slider_changed(self, value: int) -> None:
        # The slider is in lock-step with ``_history_index``; ignore
        # values that already match to avoid the recursive feedback
        # ``setValue`` would otherwise create.
        if value != self._history_index:
            self.seek_to_frame(value)

    def _refresh_frame_ui(self) -> None:
        max_idx = max(0, len(self._history) - 1)
        if self._frame_slider is not None:
            was_blocked = self._frame_slider.blockSignals(True)
            self._frame_slider.setRange(0, max_idx)
            self._frame_slider.setValue(self._history_index)
            self._frame_slider.blockSignals(was_blocked)
        if self._frame_readout is not None:
            self._frame_readout.setText(f"frame {self._history_index} / {max_idx}")
        if self._step_back_btn is not None:
            self._step_back_btn.setEnabled(self._history_index > 0)

    # ------------------------------------------------------------------
    # Tick path
    # ------------------------------------------------------------------

    def _on_timer_tick(self) -> None:
        tick = self.clock.tick()
        if tick is None:
            return
        self._advance_one_frame(tick.dt_s)

    def step_once(self, dt_s: float | None = None) -> None:
        """Headless single step — tests drive this directly so they
        don't have to spin a real QTimer.

        Equivalent to one tick of the Play loop: always appends a fresh
        frame to history (truncating any future) and advances the
        cursor.
        """
        step_dt = dt_s if dt_s is not None else self.clock.dt_s
        self.clock.start()
        ev = self.clock.tick()
        if ev is None:
            return
        self._advance_one_frame(step_dt)

    # ------------------------------------------------------------------
    # UI surface
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # PL-E — user step code reload
    # ------------------------------------------------------------------

    def apply_user_step_code(self, source: str) -> bool:
        """Compile + install a user-supplied ``step`` function.

        Pauses the timer first so the simulator is not stepping while
        we swap the function pointer. Returns True on success, False
        on syntax / runtime error (in which case the simulator keeps
        its existing step).

        The source must define a top-level function named ``step``
        with signature ``step(simulator, dt_s)``. Compile errors
        and missing-function errors land on the CodePreview status
        label in red; the override stays as whatever was in place
        before the click.
        """
        # 1) Syntax check first so a typo doesn't half-install garbage.
        try:
            ast.parse(source, mode="exec")
        except SyntaxError as exc:
            self._post_code_status(f"SyntaxError: {exc.msg} (line {exc.lineno})", ok=False)
            return False

        # 2) Exec into a sandbox namespace + pull out the step symbol.
        namespace: dict[str, object] = {}
        try:
            exec(compile(source, "<physics_lab user step>", "exec"), namespace)
        except Exception as exc:
            self._post_code_status(f"exec failed: {exc}", ok=False)
            return False

        step_fn = namespace.get("step")
        if not callable(step_fn):
            self._post_code_status(
                "no `step(simulator, dt_s)` function defined",
                ok=False,
            )
            return False

        # 3) Pause then install. The next tick uses the new function.
        was_running = self.clock.is_running
        if was_running:
            self.pause()
        self.simulator.set_step_override(step_fn)
        self._post_code_status("applied — next tick runs the user step", ok=True)
        if was_running:
            self.play()
        return True

    def revert_user_step_code(self) -> None:
        """Clear the override and restore the built-in step."""
        was_running = self.clock.is_running
        if was_running:
            self.pause()
        self.simulator.set_step_override(None)
        if self._code_preview is not None:
            self._code_preview.reset_to_builtin()
        self._post_code_status("reverted — built-in step restored", ok=True)
        if was_running:
            self.play()

    def _post_code_status(self, message: str, *, ok: bool) -> None:
        if self._code_preview is not None:
            self._code_preview.set_status(message, ok=ok)

    def _refresh_status(self) -> None:
        s = self.simulator.state
        verb = "running" if self.clock.is_running else "paused"
        self._status.setText(
            f"{verb}  t={s.time_s:.2f}s  y={s.position_m:.2f}m  "
            f"v={s.velocity_m_s:.2f}m/s  bounces={s.bounces}"
        )
