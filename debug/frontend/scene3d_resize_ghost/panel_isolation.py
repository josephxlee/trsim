"""Standalone resize-ghost repro harness — Simulator 3-panel cluster.

Mounts Scene3D / FFT / Range-Doppler in isolation from the full
SimulatorWorkspace + MainWindow so the resize ghost can be bisected.
The real panel + controller classes are imported (not copied) so this
harness exercises exactly the production code path.

Usage (from the repo root)::

    $H = "debug/frontend/scene3d_resize_ghost/panel_isolation.py"
    python $H --panel center     # all 3, real layout
    python $H --panel scene3d    # Scene3D alone
    python $H --panel fft        # FFT alone
    python $H --panel rd         # Range-Doppler alone
    python $H --panel center --static   # no 30 Hz ticks

Maximise the window, then shrink it, and watch for a stale ghost:

  * Ghost with ``--panel scene3d`` alone -> the VTK panel itself.
  * Ghost only with ``--panel center``   -> a layout / compositing
                                            interaction between panels.
  * Ghost on ``--panel fft`` / ``rd``    -> not VTK-specific; the
                                            pyqtgraph panels ghost too.

``--static`` paints a single frame and skips the QTimer so the resize
behaviour is separated from the per-tick repaint.

See ``README.md`` in this folder for the full debugging writeup.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make ``src/`` importable without setting PYTHONPATH first.
# This file lives at debug/frontend/scene3d_resize_ghost/ — four levels
# below the repo root.
_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from PySide6.QtCore import Qt, QTimer  # noqa: E402 — after sys.path bootstrap
from PySide6.QtWidgets import (  # noqa: E402 — after sys.path bootstrap
    QApplication,
    QMainWindow,
    QPushButton,
    QSplitter,
    QToolBar,
    QWidget,
)

from workbench.ui.simulator.fft_controller import (  # noqa: E402
    SimulatorFFTController,
)
from workbench.ui.simulator.panels import (  # noqa: E402
    FFTPanel,
    RangeDopplerPanel,
    RunPanel,
    Scene3DPanel,
)
from workbench.ui.simulator.rd_controller import (  # noqa: E402
    SimulatorRDController,
)
from workbench.ui.simulator.run_controller import (  # noqa: E402
    SimulatorRunController,
)
from workbench.ui.simulator.scene_controller import (  # noqa: E402
    SimulatorSceneController,
)

_PANEL_KINDS = ("center", "scene3d", "fft", "rd")


def _print_scene_sizes(scene: Scene3DPanel) -> None:
    """Print panel / interactor / VTK render-window sizes (resize probe).

    Maximise the window and compare the numbers before vs after:

      * interactor size does NOT grow  -> the QtInteractor widget is not
        being resized by the layout (a Qt geometry / native-window bug).
      * interactor grows but render_window does not -> the interactor's
        resizeEvent is not reaching ``vtkRenderWindow.SetSize``.
      * both grow but the image looks unchanged -> a paint / viewport
        issue, not a sizing one.
    """
    itx = scene.interactor()
    if itx is None:
        sys.stdout.write(f"[size] panel={scene.width()}x{scene.height()} interactor=None\n")
    else:
        rw_w, rw_h = itx.ren_win.GetSize()
        sys.stdout.write(
            f"[size] panel={scene.width()}x{scene.height()}  "
            f"interactor={itx.width()}x{itx.height()}  "
            f"render_window={rw_w}x{rw_h}\n"
        )
    sys.stdout.flush()


def _add_probe_toolbar(win: QMainWindow, scene: Scene3DPanel) -> None:
    """Add a toolbar of manual VTK-refresh probes for the resize bug.

    After a maximise leaves the 3D view stale, click each button to see
    which operation forces a correct repaint — that pins the fix:

      * '1. render()'        -> the normal pyvista render is enough.
      * '2. SetSize+Render'  -> the render window needs an explicit
                                size push before rendering.
      * '3. nudge window'    -> only a real geometry change re-syncs;
                                the fix must force an extra resize.
    """
    toolbar = QToolBar("VTK resize probes", win)
    win.addToolBar(toolbar)

    def _render() -> None:
        itx = scene.interactor()
        if itx is not None:
            itx.render()
        _print_scene_sizes(scene)

    def _setsize_render() -> None:
        itx = scene.interactor()
        if itx is not None:
            ratio = itx.devicePixelRatioF()
            itx.ren_win.SetSize(round(itx.width() * ratio), round(itx.height() * ratio))
            itx.ren_win.Render()
        _print_scene_sizes(scene)

    def _nudge() -> None:
        win.resize(win.width() + 1, win.height() + 1)
        win.resize(win.width() - 1, win.height() - 1)
        _print_scene_sizes(scene)

    for label, callback in (
        ("1. render()", _render),
        ("2. SetSize + Render", _setsize_render),
        ("3. nudge window +-1px", _nudge),
    ):
        btn = QPushButton(label)
        btn.clicked.connect(callback)
        toolbar.addWidget(btn)


def build_window(panel_kind: str, *, static: bool) -> tuple[QMainWindow, tuple[object, ...]]:
    """Build the isolation window.

    Returns the window plus a tuple of objects that must outlive the
    event loop (the controllers + RunPanel have no QObject parent, so
    dropping the Python reference would garbage-collect their QTimers).
    """
    # The RunController needs a RunPanel to host its SimulationClock.
    # The RunPanel itself is never shown — only its clock + QTimer matter.
    run_panel = RunPanel()
    run_controller = SimulatorRunController(run_panel=run_panel, autostart_timer=not static)

    scene: Scene3DPanel | None = None
    fft: FFTPanel | None = None
    rd: RangeDopplerPanel | None = None
    if panel_kind in ("center", "scene3d"):
        scene = Scene3DPanel(enable_3d_viewer=True)
    if panel_kind in ("center", "fft"):
        fft = FFTPanel()
    if panel_kind in ("center", "rd"):
        rd = RangeDopplerPanel()

    controllers: list[object] = []
    if scene is not None:
        controllers.append(
            SimulatorSceneController(scene_panel=scene, run_controller=run_controller)
        )
    if fft is not None:
        controllers.append(SimulatorFFTController(fft_panel=fft, run_controller=run_controller))
    if rd is not None:
        controllers.append(SimulatorRDController(rd_panel=rd, run_controller=run_controller))

    central: QWidget
    if panel_kind == "center":
        # Mirrors SimulatorWorkspace's centre column: Scene3D on top,
        # FFT | Range-Doppler below.
        spectra = QSplitter(Qt.Orientation.Horizontal)
        spectra.addWidget(fft)
        spectra.addWidget(rd)
        spectra.setSizes([300, 300])
        center = QSplitter(Qt.Orientation.Vertical)
        center.addWidget(scene)
        center.addWidget(spectra)
        center.setSizes([320, 220])
        central = center
    elif panel_kind == "scene3d":
        central = scene  # type: ignore[assignment]
    elif panel_kind == "fft":
        central = fft  # type: ignore[assignment]
    else:  # "rd"
        central = rd  # type: ignore[assignment]

    win = QMainWindow()
    suffix = "static" if static else "running"
    win.setWindowTitle(f"Panel isolation — {panel_kind} ({suffix})")
    win.setCentralWidget(central)
    win.resize(1100, 750)
    if scene is not None:
        _add_probe_toolbar(win, scene)

    if static:
        # Paint one frame so the panels are not blank, then leave them
        # frozen — resizing now exercises only the resize path.
        for ctl in controllers:
            ctl.paint_for(0.0, 0)  # type: ignore[attr-defined]
    else:
        run_controller.play()

    # Size probe — prints panel / interactor / render-window sizes once
    # a second so a maximise can be checked against hard numbers.
    extra: tuple[object, ...] = ()
    if scene is not None:
        probe_timer = QTimer()
        probe_timer.setInterval(1000)
        probe_timer.timeout.connect(lambda: _print_scene_sizes(scene))
        probe_timer.start()
        extra = (probe_timer,)

    keep_alive: tuple[object, ...] = (run_panel, run_controller, *controllers, *extra)
    return win, keep_alive


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulator panel resize-ghost repro.")
    parser.add_argument("--panel", choices=_PANEL_KINDS, default="center")
    parser.add_argument(
        "--static",
        action="store_true",
        help="paint one frame and skip the QTimer ticks",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    win, _keep_alive = build_window(args.panel, static=args.static)
    win.show()
    sys.stdout.write(
        f"[panel-isolation] panel={args.panel} static={args.static} — "
        "maximise then shrink, watch for a ghost. Close the window to quit.\n"
    )
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
