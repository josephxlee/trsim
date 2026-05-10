"""DockManager - QDockWidget registry (Phase 4.2d, plan/05 section 5.2).

The MainWindow keeps panels (Scenario Explorer, Plugin Manager, 3D
Scene View, FFT Spectrum, Properties, Run Panel...) inside QDockWidget
instances so the user can drag, retitle, and rearrange them. To keep
that state coherent across sessions (plan/05 section 5.8), every
dockable panel is registered through a single :class:`DockManager`.

Phase 4.2d ships the **infrastructure**:

- :class:`DockManager.register` mounts a widget as a QDockWidget on
  the host QMainWindow at a chosen Qt.DockWidgetArea.
- :class:`DockManager.toggle_visibility` flips show/hide.
- :class:`DockManager.save_state` / :meth:`restore_state` thinly wrap
  QMainWindow.saveState/restoreState so the workbench can persist the
  raw layout without each panel reinventing serialisation.

TOML persistence (full plan/05 section 5.8 schema with open scenarios
+ plugin list + camera presets) is wired in a later phase. For now
:meth:`save_state` returns the binary blob; the caller decides where
to store it. The DockManager intentionally has no knowledge of the
panels' actual content - that comes from Phase 4.3+ when real Editor
activities and Simulator panels mount themselves here.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget

DockArea = Qt.DockWidgetArea

_DEFAULT_AREA: DockArea = Qt.DockWidgetArea.LeftDockWidgetArea


@dataclass(slots=True)
class DockEntry:
    """One registered dock widget plus the panel it wraps."""

    name: str
    title: str
    widget: QWidget
    dock: QDockWidget
    area: DockArea


@dataclass(slots=True)
class DockManager:
    """In-memory registry of QDockWidgets attached to a host QMainWindow.

    The manager does not own the host QMainWindow; the host owns it.
    Each :meth:`register` call mounts a new dock on the host - calling
    :meth:`register` twice with the same ``name`` raises
    :class:`ValueError`.
    """

    host: QMainWindow
    _entries: dict[str, DockEntry] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------
    def register(
        self,
        name: str,
        title: str,
        widget: QWidget,
        *,
        area: DockArea = _DEFAULT_AREA,
    ) -> QDockWidget:
        """Mount ``widget`` on the host as a QDockWidget under ``name``.

        Args:
            name: Stable dot-namespaced id (``"scenario_explorer"``,
                ``"fft_spectrum"``). Used as the key for later
                lookup / toggle / restore.
            title: Human label shown in the dock's title bar.
            widget: The actual panel widget. The DockManager wraps it.
            area: Initial Qt.DockWidgetArea. Default is the left side
                so the typical Explorer-style panel lands where the
                user expects.

        Returns:
            The QDockWidget that now contains ``widget``.

        Raises:
            ValueError: If ``name`` is empty or already registered.
        """
        if not name:
            msg = "dock name must be a non-empty string"
            raise ValueError(msg)
        if name in self._entries:
            msg = f"dock name {name!r} is already registered"
            raise ValueError(msg)
        dock = QDockWidget(title, self.host)
        dock.setObjectName(f"Dock_{name}")
        dock.setWidget(widget)
        self.host.addDockWidget(area, dock)
        self._entries[name] = DockEntry(name=name, title=title, widget=widget, dock=dock, area=area)
        return dock

    def unregister(self, name: str) -> None:
        """Remove ``name``. Raises :class:`KeyError` if absent."""
        entry = self._entries.pop(name)
        self.host.removeDockWidget(entry.dock)
        entry.dock.deleteLater()

    def toggle_visibility(self, name: str) -> bool:
        """Flip show/hide for ``name``. Returns the new visibility flag."""
        entry = self._entries[name]
        new_state = not entry.dock.isVisible()
        entry.dock.setVisible(new_state)
        return new_state

    def set_visible(self, name: str, visible: bool) -> None:
        """Force ``name`` to ``visible`` regardless of current state."""
        self._entries[name].dock.setVisible(visible)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    def is_registered(self, name: str) -> bool:
        return name in self._entries

    def get(self, name: str) -> DockEntry:
        """Return the :class:`DockEntry` for ``name``."""
        return self._entries[name]

    def names(self) -> tuple[str, ...]:
        """Tuple of registered dock names in registration order."""
        return tuple(self._entries.keys())

    def __iter__(self) -> Iterator[DockEntry]:
        return iter(self._entries.values())

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Workspace-state persistence (plan/05 section 5.8)
    # ------------------------------------------------------------------
    def save_state(self) -> QByteArray:
        """Capture the host's full dock+toolbar layout as a QByteArray.

        Wraps :meth:`QMainWindow.saveState`. Caller is responsible for
        durably storing the bytes (Phase 4.6 will add a TOML envelope).
        """
        return self.host.saveState()

    def restore_state(self, blob: QByteArray) -> bool:
        """Restore a previously :meth:`save_state` blob.

        Returns the boolean from :meth:`QMainWindow.restoreState`
        (``False`` if the blob's geometry version is incompatible with
        the current main window).
        """
        return self.host.restoreState(blob)
