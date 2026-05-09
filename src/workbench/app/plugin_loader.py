"""Plugin loader — dynamic .py module loading (plan/04 § 4.3).

Phase 3.5 — minimum-viable plugin loader. Imports a user-supplied
``.py`` file by path, returns the resulting module object so the App
can pull out the contract implementations (Detector / Tracker / etc.,
plan/03 § 3.2.1j).

Security note: this is **not** a sandbox. Loading a plugin executes
its top-level code, exactly like importing any module. The
:mod:`workbench.app.plugin_scanner` static-scan layer runs *first*
to flag forbidden imports (Qt / NN libs from a Domain plugin) before
the user opts in to actually loading. The loader itself only decides
*how* to import.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_plugin_module(file_path: Path | str, *, module_name: str | None = None) -> ModuleType:
    """Load a Python file as a module and return it.

    Args:
        file_path: Path to the ``.py`` plugin file.
        module_name: Optional dotted name to register the module
            under. Defaults to ``"workbench_plugin_<file_stem>"``.

    Returns:
        The imported :class:`types.ModuleType`. The module is also
        recorded in ``sys.modules`` so further imports inside the
        plugin can resolve relative references.

    Raises:
        FileNotFoundError: If the plugin file doesn't exist.
        ValueError: If the file isn't a ``.py`` file.
        ImportError: If ``importlib`` can't build a spec.
    """
    path = Path(file_path)
    if not path.exists():
        msg = f"plugin file does not exist: {path}"
        raise FileNotFoundError(msg)
    if path.suffix != ".py":
        msg = f"plugin file must be .py, got {path.suffix!r}"
        raise ValueError(msg)

    name = module_name if module_name is not None else f"workbench_plugin_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        msg = f"could not build import spec for {path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    # Don't pollute sys.modules unconditionally — only if execution
    # succeeds. Keeps repeated load attempts after a syntax error
    # from leaving a half-imported module around.
    spec.loader.exec_module(module)
    return module
