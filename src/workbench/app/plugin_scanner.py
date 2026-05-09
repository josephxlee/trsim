"""AST static scan for plugins — GT Isolation Level 3-1 (plan/04 § 4.3, v0.14).

Phase 3.5 — parses a plugin source file with :mod:`ast` (no
execution) and reports:

- Top-level imports (so the App can refuse Qt / pyvista / NN
  imports from a Domain-only plugin per plan/02 § 2.5 layering).
- Top-level class / function names (so the App can find the
  Detector / Tracker / etc. implementation entry points without
  executing the plugin first).
- Module docstring (plugin description for the UI).

The scan runs **before** the loader (plugin_loader.py) — failing
the scan blocks loading.

References:

- plan/04 § 4.3 Phase 3 — plugin_scanner / GT Isolation Level 3-1.
- plan/02 § 2.5 — domain-purity contract (forbidden imports).
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# Top-level packages a Domain-layer plugin must NOT touch (matches
# .importlinter Contract 3 — plan/02 § 2.5).
DEFAULT_FORBIDDEN_IMPORTS: Final[tuple[str, ...]] = (
    "PySide6",
    "pyqtgraph",
    "pyvista",
    "vtk",
    "torch",
    "tensorflow",
    "sklearn",
    "workbench.ui",
)


@dataclass(frozen=True, slots=True)
class PluginScanReport:
    """Output of :func:`scan_plugin_file`.

    Attributes:
        path: Resolved plugin file path.
        module_docstring: Top-level module docstring (``""`` if absent).
        imports: Tuple of top-level imported module names (the "root"
            of the dotted name — ``import foo.bar`` -> ``"foo"``).
        class_names: Top-level class definitions.
        function_names: Top-level function / async function definitions.
        forbidden_hits: Subset of ``imports`` that matched the
            ``forbidden_imports`` list.

    Properties:
        is_isolated: ``True`` when ``forbidden_hits`` is empty.
    """

    path: Path
    module_docstring: str
    imports: tuple[str, ...]
    class_names: tuple[str, ...]
    function_names: tuple[str, ...]
    forbidden_hits: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_isolated(self) -> bool:
        return not self.forbidden_hits


def _root_name(name: str) -> str:
    """``"foo.bar.baz"`` -> ``"foo"``. Empty string in -> empty out."""
    return name.split(".", 1)[0] if name else ""


def _collect_top_level(
    tree: ast.Module,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Walk ``tree`` once and pull out (imports, classes, functions)."""
    imports: list[str] = []
    classes: list[str] = []
    functions: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(_root_name(alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(_root_name(node.module))
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            functions.append(node.name)
    return tuple(imports), tuple(classes), tuple(functions)


def scan_plugin_file(
    file_path: Path | str,
    *,
    forbidden_imports: Iterable[str] = DEFAULT_FORBIDDEN_IMPORTS,
) -> PluginScanReport:
    """Static-scan a plugin file and produce a :class:`PluginScanReport`.

    Args:
        file_path: Path to a ``.py`` plugin file (must exist).
        forbidden_imports: Iterable of root module names that this
            plugin must not import. Defaults to
            :data:`DEFAULT_FORBIDDEN_IMPORTS` (Qt / vis / NN /
            workbench.ui).

    Returns:
        :class:`PluginScanReport`.

    Raises:
        FileNotFoundError: If ``file_path`` doesn't exist.
        ValueError: If the file isn't a ``.py`` file.
        SyntaxError: Propagated from :func:`ast.parse`.
    """
    path = Path(file_path)
    if not path.exists():
        msg = f"plugin file does not exist: {path}"
        raise FileNotFoundError(msg)
    if path.suffix != ".py":
        msg = f"plugin file must be .py, got {path.suffix!r}"
        raise ValueError(msg)

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports, class_names, function_names = _collect_top_level(tree)
    docstring = ast.get_docstring(tree) or ""

    forbidden_set = frozenset(_root_name(name) for name in forbidden_imports)
    forbidden_hits = tuple(name for name in imports if name in forbidden_set)

    return PluginScanReport(
        path=path.resolve(),
        module_docstring=docstring,
        imports=imports,
        class_names=class_names,
        function_names=function_names,
        forbidden_hits=forbidden_hits,
    )
