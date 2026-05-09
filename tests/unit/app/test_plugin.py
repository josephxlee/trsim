"""Unit tests for app.plugin_loader + plugin_scanner (Phase 3.5)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from workbench.app.plugin_loader import load_plugin_module
from workbench.app.plugin_scanner import (
    DEFAULT_FORBIDDEN_IMPORTS,
    PluginScanReport,
    scan_plugin_file,
)


def _write_plugin(root: Path, source: str, name: str = "p.py") -> Path:
    path = root / name
    path.write_text(source, encoding="utf-8")
    return path


# ---------------------------------------------------------------------
# plugin_scanner
# ---------------------------------------------------------------------


def test_scanner_extracts_docstring_imports_classes_functions() -> None:
    src = '''"""Sample plugin doc."""

import math
from collections.abc import Iterable

class MyDetector:
    pass

def configure(self):
    pass

async def detect(self):
    pass
'''
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_plugin(Path(tmp), src)
        report = scan_plugin_file(p)
    assert isinstance(report, PluginScanReport)
    assert report.module_docstring == "Sample plugin doc."
    assert "math" in report.imports
    assert "collections" in report.imports
    assert report.class_names == ("MyDetector",)
    assert set(report.function_names) == {"configure", "detect"}
    assert report.is_isolated


def test_scanner_flags_forbidden_imports() -> None:
    src = """
import PySide6
import torch
from pyvista import abc

class X:
    pass
"""
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_plugin(Path(tmp), src)
        report = scan_plugin_file(p)
    assert "PySide6" in report.forbidden_hits
    assert "torch" in report.forbidden_hits
    assert "pyvista" in report.forbidden_hits
    assert not report.is_isolated


def test_scanner_custom_forbidden_list() -> None:
    src = "import math\n"
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_plugin(Path(tmp), src)
        report = scan_plugin_file(p, forbidden_imports=("math",))
    assert report.forbidden_hits == ("math",)


def test_scanner_handles_no_docstring() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_plugin(Path(tmp), "x = 1\n")
        report = scan_plugin_file(p)
    assert report.module_docstring == ""


def test_scanner_root_name_extracted_from_dotted() -> None:
    src = "from workbench.ui.editor import foo\n"
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_plugin(Path(tmp), src)
        report = scan_plugin_file(p)
        # 'workbench.ui' is the forbidden entry; root extraction means
        # only 'workbench' shows in imports. With root-only matching
        # we have to feed 'workbench' explicitly to flag the file.
        report2 = scan_plugin_file(p, forbidden_imports=("workbench",))
    assert "workbench" in report.imports
    assert "workbench" in report2.forbidden_hits


def test_scanner_rejects_non_py() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "x.toml"
        p.write_text("not python\n", encoding="utf-8")
        with pytest.raises(ValueError, match=r"\.py"):
            scan_plugin_file(p)


def test_scanner_rejects_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match=r"plugin file"):
        scan_plugin_file("/no/such/plugin.py")


def test_scanner_propagates_syntax_error() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_plugin(Path(tmp), "def broken(:\n    pass\n")
        with pytest.raises(SyntaxError):
            scan_plugin_file(p)


def test_default_forbidden_imports_includes_qt_vis_nn() -> None:
    forbidden = set(DEFAULT_FORBIDDEN_IMPORTS)
    assert {"PySide6", "pyvista", "torch"} <= forbidden


# ---------------------------------------------------------------------
# plugin_loader
# ---------------------------------------------------------------------


def test_loader_imports_module_and_returns_attrs() -> None:
    src = '''"""Smoke test."""

class Detector:
    def configure(self):
        return "ok"

PLUGIN_NAME = "smoke"
'''
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_plugin(Path(tmp), src, "smoke_plugin.py")
        mod = load_plugin_module(p)
    assert mod.PLUGIN_NAME == "smoke"
    assert mod.Detector().configure() == "ok"


def test_loader_uses_custom_module_name() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_plugin(Path(tmp), "x = 42\n", "named.py")
        mod = load_plugin_module(p, module_name="my.special.plugin")
    assert mod.__name__ == "my.special.plugin"
    assert mod.x == 42


def test_loader_rejects_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match=r"plugin file"):
        load_plugin_module("/no/such/plugin.py")


def test_loader_rejects_non_py_extension() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "p.txt"
        p.write_text("anything\n", encoding="utf-8")
        with pytest.raises(ValueError, match=r"\.py"):
            load_plugin_module(p)


def test_loader_propagates_runtime_error() -> None:
    src = "raise RuntimeError('bad init')\n"
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_plugin(Path(tmp), src, "bad.py")
        with pytest.raises(RuntimeError, match=r"bad init"):
            load_plugin_module(p)
