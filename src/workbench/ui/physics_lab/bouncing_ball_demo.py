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

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from workbench.app.physics_lab import (
    BouncingBallSimulator,
    BouncingBallState,
    PhysicsClock,
    analytic_peak_height_m,
)
from workbench.domain.physics_lab import (
    BOUNCING_BALL_PARAM_SPECS,
    MeasuredDataset,
    PaperReference,
    SavedExperiment,
    TestObject,
    TimeMode,
    ValidationMetrics,
    compute_validation_metrics,
    default_library,
    load_measured_csv,
    load_measured_hdf5,
)
from workbench.ui.physics_lab.auto_parameters import AutoParametersWidget
from workbench.ui.physics_lab.python_highlighter import PythonSyntaxHighlighter

# ---------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------


class LibraryWidget(QWidget):
    """Sidebar tree (Tests / Models / Saved Experiments) — PL-9.1f.

    plan/19 § 19.5.2 splits the Library into three top-level
    categories. PL-9.1f replaces the flat PL-D :class:`QListWidget`
    with a :class:`QTreeWidget` and exposes:

    - **Tests**: ``BOUNCING_BALL_ROW`` + the 9 default Test Objects.
    - **Models**: physical models the user can toggle (Gravity is
      always on; Air Drag becomes interactive in PL-9.1g).
    - **Saved Experiments**: populated via :meth:`set_saved_experiments`
      from a list of :class:`SavedExperiment`. Initially empty.

    Signals:
        demo_selected(str): emitted with the leaf-item text when the
            user selects any row under the three categories. Top-
            level category items themselves never fire the signal.
        save_requested(): emitted by the "Save current..." button
            so the workspace can prompt for a name and serialise.
        experiment_selected(SavedExperiment): emitted when the user
            picks a Saved Experiments leaf, so the workspace can
            restore parameters + mode.
    """

    demo_selected = Signal(str)
    save_requested = Signal()
    experiment_selected = Signal(object)
    measured_dataset_selected = Signal(object)
    paper_selected = Signal(object)

    BOUNCING_BALL_ROW = "Bouncing Ball Demo"
    CATEGORY_TESTS = "Tests"
    CATEGORY_MODELS = "Models"
    CATEGORY_SAVED = "Saved Experiments"
    CATEGORY_MEASURED = "Measured Data"
    CATEGORY_PAPERS = "Papers"

    # Models category placeholders. PL-9.1g will turn ``Air Drag`` into
    # an interactive toggle attached to the simulator.
    _DEFAULT_MODELS: tuple[str, ...] = (
        "Gravity (always on)",
        "Air Drag (toggle)",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLab_LibraryWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("Library", self)
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        self._tree = QTreeWidget(self)
        self._tree.setObjectName("PhysicsLab_LibraryTree")
        self._tree.setHeaderHidden(True)
        self._label_to_object: dict[str, TestObject] = {}
        self._label_to_experiment: dict[str, SavedExperiment] = {}
        self._label_to_measured: dict[str, MeasuredDataset] = {}
        self._label_to_paper: dict[str, PaperReference] = {}

        # Tests category: Bouncing Ball Demo + 9 Test Objects.
        self._tests_item = QTreeWidgetItem(self._tree, [self.CATEGORY_TESTS])
        QTreeWidgetItem(self._tests_item, [self.BOUNCING_BALL_ROW])
        for obj in default_library():
            label = f"{obj.name}  ({obj.visual})"
            QTreeWidgetItem(self._tests_item, [label])
            self._label_to_object[label] = obj

        # Models category placeholders.
        self._models_item = QTreeWidgetItem(self._tree, [self.CATEGORY_MODELS])
        for model_label in self._DEFAULT_MODELS:
            QTreeWidgetItem(self._models_item, [model_label])

        # Saved Experiments category — initially empty.
        self._saved_item = QTreeWidgetItem(self._tree, [self.CATEGORY_SAVED])

        # Measured Data + Papers (PL-9.2a/b) — populated by the
        # workspace from disk roots on construction or refresh.
        self._measured_item = QTreeWidgetItem(self._tree, [self.CATEGORY_MEASURED])
        self._papers_item = QTreeWidgetItem(self._tree, [self.CATEGORY_PAPERS])

        self._tree.expandAll()
        self._tree.currentItemChanged.connect(self._on_current_item_changed)
        layout.addWidget(self._tree, 1)

        # Save row — workspace hooks save_requested into a Save dialog.
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self._save_btn = QPushButton("Save current experiment...", self)
        self._save_btn.setObjectName("PhysicsLab_LibrarySaveBtn")
        self._save_btn.clicked.connect(self.save_requested.emit)
        row.addWidget(self._save_btn)
        layout.addLayout(row)

        # Restore PL-D default selection (Bouncing Ball Demo).
        self.select_label(self.BOUNCING_BALL_ROW)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tree_widget(self) -> QTreeWidget:
        return self._tree

    def save_button(self) -> QPushButton:
        return self._save_btn

    def tests_category(self) -> QTreeWidgetItem:
        return self._tests_item

    def models_category(self) -> QTreeWidgetItem:
        return self._models_item

    def saved_category(self) -> QTreeWidgetItem:
        return self._saved_item

    def measured_category(self) -> QTreeWidgetItem:
        return self._measured_item

    def papers_category(self) -> QTreeWidgetItem:
        return self._papers_item

    def test_object_for(self, label: str) -> TestObject | None:
        """Resolve a Library leaf label to its Test Object dataclass.

        Returns ``None`` for ``BOUNCING_BALL_ROW`` and any other non
        Test-Object row so the workspace can branch cleanly.
        """
        return self._label_to_object.get(label)

    def experiment_for(self, label: str) -> SavedExperiment | None:
        return self._label_to_experiment.get(label)

    def measured_for(self, label: str) -> MeasuredDataset | None:
        return self._label_to_measured.get(label)

    def paper_for(self, label: str) -> PaperReference | None:
        return self._label_to_paper.get(label)

    def current_label(self) -> str:
        item = self._tree.currentItem()
        if item is None or item.parent() is None:
            return ""
        return item.text(0)

    def _all_categories(self) -> tuple[QTreeWidgetItem, ...]:
        return (
            self._tests_item,
            self._models_item,
            self._saved_item,
            self._measured_item,
            self._papers_item,
        )

    def select_label(self, label: str) -> bool:
        """Find + select a leaf by its text. Returns True on success."""
        for category in self._all_categories():
            for i in range(category.childCount()):
                child = category.child(i)
                if child is not None and child.text(0) == label:
                    self._tree.setCurrentItem(child)
                    return True
        return False

    def leaf_labels(self) -> tuple[str, ...]:
        """Every leaf row's text across all five categories."""
        labels: list[str] = []
        for category in self._all_categories():
            for i in range(category.childCount()):
                child = category.child(i)
                if child is not None:
                    labels.append(child.text(0))
        return tuple(labels)

    def set_saved_experiments(
        self,
        experiments: Iterable[SavedExperiment],
    ) -> None:
        """Replace the Saved Experiments sub-tree with new entries.

        Each experiment's leaf label is its ``experiment_id`` followed
        by an optional ``(mode)`` suffix so the user can tell static
        / run / compare / sweep snapshots apart at a glance.
        """
        # Drop existing leaves + map entries.
        for label in list(self._label_to_experiment.keys()):
            self._label_to_experiment.pop(label, None)
        self._saved_item.takeChildren()
        for exp in experiments:
            label = f"{exp.experiment_id}  ({exp.mode.value})"
            QTreeWidgetItem(self._saved_item, [label])
            self._label_to_experiment[label] = exp
        self._tree.expandItem(self._saved_item)

    def set_measured_datasets(
        self,
        datasets: Iterable[MeasuredDataset],
    ) -> None:
        """Replace the Measured Data sub-tree with new entries (PL-9.2a)."""
        for label in list(self._label_to_measured.keys()):
            self._label_to_measured.pop(label, None)
        self._measured_item.takeChildren()
        for dataset in datasets:
            label = f"{dataset.dataset_id}  ({dataset.file_format})"
            QTreeWidgetItem(self._measured_item, [label])
            self._label_to_measured[label] = dataset
        self._tree.expandItem(self._measured_item)

    def set_papers(self, papers: Iterable[PaperReference]) -> None:
        """Replace the Papers sub-tree with new entries (PL-9.2b)."""
        for label in list(self._label_to_paper.keys()):
            self._label_to_paper.pop(label, None)
        self._papers_item.takeChildren()
        for paper in papers:
            label = paper.paper_id if not paper.title else f"{paper.paper_id} — {paper.title}"
            QTreeWidgetItem(self._papers_item, [label])
            self._label_to_paper[label] = paper
        self._tree.expandItem(self._papers_item)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_current_item_changed(
        self,
        current: QTreeWidgetItem | None,
        _previous: QTreeWidgetItem | None,
    ) -> None:
        if current is None or current.parent() is None:
            # Top-level category clicked; do not emit.
            return
        label = current.text(0)
        self.demo_selected.emit(label)
        if label in self._label_to_experiment:
            self.experiment_selected.emit(self._label_to_experiment[label])
        if label in self._label_to_measured:
            self.measured_dataset_selected.emit(self._label_to_measured[label])
        if label in self._label_to_paper:
            self.paper_selected.emit(self._label_to_paper[label])


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
    """pyqtgraph plot of ``y(t)`` (height in metres vs. time in seconds).

    PL-9.1e — supports multiple named curves on the same axes for the
    Compare and Sweep modes. The original single-curve API (``append``
    / ``set_history`` / ``clear_history`` / ``history_length``) still
    operates on the implicit ``"primary"`` curve so existing callers
    do not change.

    Extra curves:
        :meth:`add_overlay_curve(name, color)` — register a new curve.
        :meth:`append_to(name, t, y)` — extend it.
        :meth:`set_history_of(name, times, ys)` — replace its samples.
        :meth:`remove_overlay_curve(name)` — drop the curve + the
            backing buffers.
        :meth:`overlay_names()` — names of all curves except primary.
    """

    PRIMARY_CURVE: str = "primary"

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
        layout.addWidget(self._plot, 1)

        # Curve registry. The primary curve is always present.
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._histories: dict[str, tuple[list[float], list[float]]] = {}
        self._add_curve(self.PRIMARY_CURVE, color=None, width=2)

    def _add_curve(
        self,
        name: str,
        *,
        color: str | None,
        width: int = 2,
    ) -> pg.PlotDataItem:
        pen = pg.mkPen(width=width) if color is None else pg.mkPen(color, width=width)
        curve = self._plot.plot([], [], pen=pen, name=name)
        self._curves[name] = curve
        self._histories[name] = ([], [])
        return curve

    # ------------------------------------------------------------------
    # Primary-curve API (back-compat with PL-D)
    # ------------------------------------------------------------------

    def append(self, time_s: float, y_m: float) -> None:
        """Append one (t, y) sample to the primary curve and redraw."""
        self.append_to(self.PRIMARY_CURVE, time_s, y_m)

    def set_history(self, times: Iterable[float], ys: Iterable[float]) -> None:
        self.set_history_of(self.PRIMARY_CURVE, times, ys)

    def clear_history(self) -> None:
        self.clear_history_of(self.PRIMARY_CURVE)

    def history_length(self) -> int:
        return self.history_length_of(self.PRIMARY_CURVE)

    def plot_widget(self) -> pg.PlotWidget:
        return self._plot

    # ------------------------------------------------------------------
    # Multi-curve API (PL-9.1e Compare + Sweep)
    # ------------------------------------------------------------------

    def add_overlay_curve(self, name: str, *, color: str) -> None:
        """Register a new named overlay curve in addition to ``primary``.

        Raises ValueError on duplicate or reserved ``primary`` name.
        """
        if name == self.PRIMARY_CURVE:
            msg = f"{self.PRIMARY_CURVE!r} is the implicit primary curve"
            raise ValueError(msg)
        if name in self._curves:
            msg = f"BouncingBallPlot: curve {name!r} already exists"
            raise ValueError(msg)
        self._add_curve(name, color=color)

    def remove_overlay_curve(self, name: str) -> None:
        """Drop a named overlay (no-op on missing / primary)."""
        if name == self.PRIMARY_CURVE or name not in self._curves:
            return
        self._plot.removeItem(self._curves[name])
        del self._curves[name]
        del self._histories[name]

    def overlay_names(self) -> tuple[str, ...]:
        return tuple(n for n in self._curves if n != self.PRIMARY_CURVE)

    def all_curve_names(self) -> tuple[str, ...]:
        return tuple(self._curves.keys())

    def append_to(self, name: str, time_s: float, y_m: float) -> None:
        """Append one (t, y) sample to a named curve and redraw."""
        if name not in self._curves:
            msg = f"BouncingBallPlot: unknown curve {name!r}"
            raise ValueError(msg)
        times, ys = self._histories[name]
        times.append(time_s)
        ys.append(y_m)
        self._curves[name].setData(times, ys)

    def set_history_of(
        self,
        name: str,
        times: Iterable[float],
        ys: Iterable[float],
    ) -> None:
        if name not in self._curves:
            msg = f"BouncingBallPlot: unknown curve {name!r}"
            raise ValueError(msg)
        ts = list(times)
        vs = list(ys)
        self._histories[name] = (ts, vs)
        self._curves[name].setData(ts, vs)

    def clear_history_of(self, name: str) -> None:
        if name not in self._curves:
            return
        self._histories[name] = ([], [])
        self._curves[name].setData([], [])

    def history_length_of(self, name: str) -> int:
        if name not in self._histories:
            return 0
        return len(self._histories[name][0])


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

    # Plot curve names + display colours for the Compare / Sweep modes.
    COMPARE_ANALYTIC_CURVE: str = "analytic_peak"
    SWEEP_RESTITUTION_VALUES: tuple[float, ...] = (0.3, 0.5, 0.7, 0.9)
    _SWEEP_COLOURS: tuple[str, ...] = ("#d62728", "#2ca02c", "#1f77b4", "#9467bd")

    # Validation Bench (PL-9.2c) overlay curves on the y(t) plot.
    VALIDATION_MEASURED_CURVE: str = "validation_measured"
    VALIDATION_SIM_CURVE: str = "validation_sim"
    VALIDATION_DEFAULT_X_COLUMN: str = "time_s"
    VALIDATION_DEFAULT_Y_COLUMN: str = "position_m"

    validation_metrics_ready = Signal(object)

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
        mode_combo: QComboBox | None = None,
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
        self._mode_combo = mode_combo
        self._mode: TimeMode = TimeMode.RUN
        # Sweep mode keeps one extra simulator per restitution value
        # plus the curve name it draws into.
        self._sweep_simulators: list[BouncingBallSimulator] = []
        self._sweep_curve_names: list[str] = []

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
        # PL-9.1g — wire the drag slider directly to the simulator. The
        # restitution slider has a dedicated signal for PL-D back-compat;
        # all other parameters route through ``parameter_changed``.
        self._parameters.parameter_changed.connect(self._on_parameter_changed)

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

        # PL-9.1e — mode combo. ``currentTextChanged`` routes to
        # ``set_mode`` which clears + replays per-mode overlays.
        if self._mode_combo is not None:
            self._mode_combo.currentTextChanged.connect(lambda text: self.set_mode(TimeMode(text)))

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
        # Mode-specific overlays start from a clean slate after a stop.
        if self._mode == TimeMode.COMPARE:
            self._reset_compare_overlay()
        elif self._mode == TimeMode.SWEEP:
            self._reset_sweep_overlay()
        self._refresh_frame_ui()
        self._refresh_status()

    def reset_with(
        self,
        *,
        gravity_m_s2: float | None = None,
        restitution: float | None = None,
        initial_height_m: float | None = None,
        initial_velocity_m_s: float | None = None,
        drag_coefficient_k: float | None = None,
    ) -> None:
        """Replace the simulator with new initial conditions (PL-9.1f).

        Used by :class:`PhysicsLabWorkspace.load_experiment` to restore
        a :class:`SavedExperiment`. Any unset argument keeps its
        previous value.
        """
        self.pause()
        sim = self.simulator
        g = gravity_m_s2 if gravity_m_s2 is not None else sim.gravity_m_s2
        r = restitution if restitution is not None else sim.restitution
        h0 = initial_height_m if initial_height_m is not None else sim.initial_height_m
        v0 = initial_velocity_m_s if initial_velocity_m_s is not None else sim.initial_velocity_m_s
        k = drag_coefficient_k if drag_coefficient_k is not None else sim.drag_coefficient_k
        self.simulator = BouncingBallSimulator(
            gravity_m_s2=g,
            restitution=r,
            initial_height_m=h0,
            initial_velocity_m_s=v0,
            drag_coefficient_k=k,
        )
        self.clock.stop()
        self._history = [self.simulator.state]
        self._history_index = 0
        self._plot.clear_history()
        self._plot.append(self.simulator.state.time_s, self.simulator.state.position_m)
        # Rebuild mode-specific overlays around the new conditions.
        if self._mode == TimeMode.COMPARE:
            self._reset_compare_overlay()
        elif self._mode == TimeMode.SWEEP:
            self._teardown_sweep_overlay()
            self._setup_sweep_overlay()
        self._refresh_frame_ui()
        self._refresh_status()

    # ------------------------------------------------------------------
    # Mode surface (PL-9.1e)
    # ------------------------------------------------------------------

    @property
    def mode(self) -> TimeMode:
        return self._mode

    def set_mode(self, mode: TimeMode) -> None:
        """Switch between Static / Run / Compare / Sweep.

        Always pauses + resets the simulator so each mode starts from
        a clean ``t=0`` state. Mode-specific overlay curves are torn
        down on exit and rebuilt on entry.
        """
        if mode == self._mode:
            return
        prev = self._mode
        # Tear down previous mode's overlays.
        if prev == TimeMode.COMPARE:
            self._teardown_compare_overlay()
        elif prev == TimeMode.SWEEP:
            self._teardown_sweep_overlay()
        self._mode = mode
        # Reset to t=0 — the new mode rebuilds from a clean state.
        self.stop()
        self._apply_transport_enabled(enabled=mode != TimeMode.STATIC)
        if mode == TimeMode.STATIC:
            # Time controls disabled; plot shows seed state only.
            pass
        elif mode == TimeMode.COMPARE:
            self._setup_compare_overlay()
        elif mode == TimeMode.SWEEP:
            self._setup_sweep_overlay()
        # Reflect the mode in the combo (no-op when the combo emitted
        # the change in the first place because the value already matches).
        if self._mode_combo is not None and self._mode_combo.currentText() != mode.value:
            self._mode_combo.setCurrentText(mode.value)

    def _on_parameter_changed(self, name: str, value: float) -> None:
        """Forward auto-slider changes to simulator setters (PL-9.1g)."""
        if name == "drag_coefficient_k":
            self.simulator.set_drag_coefficient(value)
        # gravity / initial_height / initial_velocity are start-of-run
        # parameters — applied on the next reset / experiment load.

    def _apply_transport_enabled(self, *, enabled: bool) -> None:
        for btn in (self._play_btn, self._pause_btn, self._stop_btn):
            btn.setEnabled(enabled)
        if self._frame_slider is not None:
            self._frame_slider.setEnabled(enabled)
        if self._step_fwd_btn is not None:
            self._step_fwd_btn.setEnabled(enabled)
        if self._step_back_btn is not None:
            self._step_back_btn.setEnabled(enabled and self._history_index > 0)

    # ---- Compare-mode overlay (analytic peak-height markers) -------

    def _setup_compare_overlay(self) -> None:
        self._plot.add_overlay_curve(self.COMPARE_ANALYTIC_CURVE, color="#ff7f0e")
        self._refresh_compare_overlay()

    def _teardown_compare_overlay(self) -> None:
        self._plot.remove_overlay_curve(self.COMPARE_ANALYTIC_CURVE)

    def _reset_compare_overlay(self) -> None:
        self._plot.clear_history_of(self.COMPARE_ANALYTIC_CURVE)
        self._refresh_compare_overlay()

    def _refresh_compare_overlay(self) -> None:
        """Plot the analytic peak height per bounce up to ``N=20`` and
        let the user visually compare the simulated bouncing decay
        against the closed-form ``h_n = r^(2n) * h_0`` curve.
        """
        if self.COMPARE_ANALYTIC_CURVE not in self._plot.all_curve_names():
            return
        h0 = self.simulator.initial_height_m
        r = self.simulator.restitution
        max_bounce = 20
        times: list[float] = []
        heights: list[float] = []
        # Approximate landing time of bounce n as ``2 * sum_{k<n} v_k / g``
        # where v_k = sqrt(2 * g * h_k). The series telescopes to
        # ``t_n = sqrt(2*h0/g) * (1 + 2*sum_{k=1..n} r^k)`` — useful as
        # a marker x-axis without the per-step roundoff of the
        # simulated trajectory.
        import math

        g = self.simulator.gravity_m_s2
        t_first = math.sqrt(2.0 * h0 / g)
        for n in range(max_bounce + 1):
            h_n = analytic_peak_height_m(h0, r, n)
            if n == 0:
                t = 0.0
            else:
                # Sum of r^k for k=1..n.
                geom = sum(r**k for k in range(1, n + 1))
                t = t_first * (1.0 + 2.0 * geom)
            times.append(t)
            heights.append(h_n)
        self._plot.set_history_of(self.COMPARE_ANALYTIC_CURVE, times, heights)

    # ---- Sweep-mode overlays (one trajectory per restitution) -------

    def _setup_sweep_overlay(self) -> None:
        self._sweep_simulators = []
        self._sweep_curve_names = []
        for r_value, colour in zip(
            self.SWEEP_RESTITUTION_VALUES,
            self._SWEEP_COLOURS,
            strict=True,
        ):
            sim = BouncingBallSimulator(
                gravity_m_s2=self.simulator.gravity_m_s2,
                restitution=r_value,
                initial_height_m=self.simulator.initial_height_m,
                initial_velocity_m_s=self.simulator.initial_velocity_m_s,
            )
            name = f"sweep_r{int(r_value * 100)}"
            self._plot.add_overlay_curve(name, color=colour)
            self._plot.append_to(name, sim.state.time_s, sim.state.position_m)
            self._sweep_simulators.append(sim)
            self._sweep_curve_names.append(name)

    def _teardown_sweep_overlay(self) -> None:
        for name in self._sweep_curve_names:
            self._plot.remove_overlay_curve(name)
        self._sweep_simulators = []
        self._sweep_curve_names = []

    def _reset_sweep_overlay(self) -> None:
        for sim, name in zip(self._sweep_simulators, self._sweep_curve_names, strict=True):
            sim.reset()
            self._plot.clear_history_of(name)
            self._plot.append_to(name, sim.state.time_s, sim.state.position_m)

    def _step_sweep_simulators(self, dt_s: float) -> None:
        for sim, name in zip(self._sweep_simulators, self._sweep_curve_names, strict=True):
            state = sim.step(dt_s)
            self._plot.append_to(name, state.time_s, state.position_m)

    # ------------------------------------------------------------------
    # Validation Bench (PL-9.2c)
    # ------------------------------------------------------------------

    def run_validation_from_dataset(
        self,
        dataset: MeasuredDataset,
        *,
        x_column: str | None = None,
        y_column: str | None = None,
        dt_s: float = 0.005,
    ) -> ValidationMetrics:
        """Compare current simulator output to a measured dataset.

        Loads the named columns from ``dataset`` (CSV column index or
        HDF5 dataset name), runs a fresh simulator with the current
        parameters over the measured x-range, interpolates onto the
        measurement grid, and returns the
        :class:`ValidationMetrics`.

        Side-effects:
            - Adds two overlay curves to the plot:
              ``VALIDATION_MEASURED_CURVE`` (red, measured) and
              ``VALIDATION_SIM_CURVE`` (blue, simulated).
            - Emits ``validation_metrics_ready(metrics)``.

        Args:
            dataset: A :class:`MeasuredDataset` registered in the
                Library.
            x_column: Column to use as the independent axis. Defaults
                to ``VALIDATION_DEFAULT_X_COLUMN``; falls back to the
                first column when the default is absent.
            y_column: Column to use as the dependent axis. Defaults to
                ``VALIDATION_DEFAULT_Y_COLUMN``; falls back to the
                second column when the default is absent.
            dt_s: Simulator step size (smaller -> tighter interpolation
                grid, more work).

        Raises:
            ValueError: For datasets with < 2 columns or unknown
                column names.
        """
        measured_x, measured_y = self._load_measurement_columns(dataset, x_column, y_column)
        # Simulate from t=0 to max(measured_x) with the current state.
        sim_x, sim_y = self._simulate_for_validation(measured_x, dt_s)
        metrics = compute_validation_metrics(measured_x, measured_y, sim_x, sim_y)
        self._install_validation_overlays(measured_x, measured_y, sim_x, sim_y)
        self.validation_metrics_ready.emit(metrics)
        return metrics

    def clear_validation_overlays(self) -> None:
        """Remove the validation overlay curves added by the last run."""
        self._plot.remove_overlay_curve(self.VALIDATION_MEASURED_CURVE)
        self._plot.remove_overlay_curve(self.VALIDATION_SIM_CURVE)

    def _load_measurement_columns(
        self,
        dataset: MeasuredDataset,
        x_column: str | None,
        y_column: str | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        if len(dataset.columns) < 2:
            msg = (
                f"run_validation: dataset {dataset.dataset_id!r} has "
                f"< 2 columns ({dataset.columns})"
            )
            raise ValueError(msg)
        x_col = x_column or (
            self.VALIDATION_DEFAULT_X_COLUMN
            if self.VALIDATION_DEFAULT_X_COLUMN in dataset.columns
            else dataset.columns[0]
        )
        y_col = y_column or (
            self.VALIDATION_DEFAULT_Y_COLUMN
            if self.VALIDATION_DEFAULT_Y_COLUMN in dataset.columns
            else dataset.columns[1]
        )
        if x_col not in dataset.columns:
            msg = f"run_validation: x column {x_col!r} not in {dataset.columns}"
            raise ValueError(msg)
        if y_col not in dataset.columns:
            msg = f"run_validation: y column {y_col!r} not in {dataset.columns}"
            raise ValueError(msg)
        if dataset.file_format == "csv":
            arr = load_measured_csv(dataset)
            x_idx = dataset.columns.index(x_col)
            y_idx = dataset.columns.index(y_col)
            return arr[:, x_idx], arr[:, y_idx]
        # HDF5
        return (
            load_measured_hdf5(dataset, x_col),
            load_measured_hdf5(dataset, y_col),
        )

    def _simulate_for_validation(
        self,
        measured_x: np.ndarray,
        dt_s: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run a fresh sim from t=0 to ``max(measured_x)``.

        Does not touch the controller's live simulator or history —
        the user's interactive state stays intact across validation
        runs.
        """
        end_t = float(measured_x.max())
        if end_t <= 0.0:
            msg = "run_validation: measured x-range must include positive values"
            raise ValueError(msg)
        sim = BouncingBallSimulator(
            gravity_m_s2=self.simulator.gravity_m_s2,
            restitution=self.simulator.restitution,
            initial_height_m=self.simulator.initial_height_m,
            initial_velocity_m_s=self.simulator.initial_velocity_m_s,
            drag_coefficient_k=self.simulator.drag_coefficient_k,
        )
        n_steps = max(2, int(np.ceil(end_t / dt_s)) + 1)
        times = np.empty(n_steps, dtype=np.float64)
        ys = np.empty(n_steps, dtype=np.float64)
        times[0] = sim.state.time_s
        ys[0] = sim.state.position_m
        for i in range(1, n_steps):
            state = sim.step(dt_s)
            times[i] = state.time_s
            ys[i] = state.position_m
        return times, ys

    def _install_validation_overlays(
        self,
        measured_x: np.ndarray,
        measured_y: np.ndarray,
        sim_x: np.ndarray,
        sim_y: np.ndarray,
    ) -> None:
        # Drop any previous overlay before adding the new ones.
        self.clear_validation_overlays()
        self._plot.add_overlay_curve(self.VALIDATION_MEASURED_CURVE, color="#d62728")
        self._plot.add_overlay_curve(self.VALIDATION_SIM_CURVE, color="#1f77b4")
        self._plot.set_history_of(
            self.VALIDATION_MEASURED_CURVE,
            list(measured_x),
            list(measured_y),
        )
        self._plot.set_history_of(
            self.VALIDATION_SIM_CURVE,
            list(sim_x),
            list(sim_y),
        )

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
        Sweep-mode siblings also step in lock-step so the user can see
        all N restitution trajectories progress together.
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
        if self._mode == TimeMode.SWEEP and self._sweep_simulators:
            self._step_sweep_simulators(dt_s)
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
