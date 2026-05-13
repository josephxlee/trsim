"""Unit tests for ui.editor.package_manager_panel (Phase 7 C5)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.package_manager_panel import (
    InstalledPackageRow,
    PackageManagerPanel,
)

pytestmark = pytest.mark.qt


def _panel(qtbot: object) -> PackageManagerPanel:
    panel = PackageManagerPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    return panel


# ---------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------


def test_panel_starts_with_empty_list_and_disabled_uninstall(qtbot: object) -> None:
    panel = _panel(qtbot)
    assert panel.list_widget().count() == 0
    assert panel.installed_packages() == ()
    assert panel.selected_package_id() is None
    assert panel.uninstall_button().isEnabled() is False


def test_install_and_refresh_buttons_always_enabled(qtbot: object) -> None:
    panel = _panel(qtbot)
    assert panel.install_button().isEnabled()
    assert panel.refresh_button().isEnabled()


# ---------------------------------------------------------------------
# set_installed_packages
# ---------------------------------------------------------------------


def _rows() -> list[InstalledPackageRow]:
    return [
        InstalledPackageRow(package_id="alpha", name="Alpha", version="0.1.0"),
        InstalledPackageRow(package_id="beta", name="Beta", version="2.3.4"),
    ]


def test_set_installed_packages_populates_list(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_installed_packages(_rows())
    assert panel.list_widget().count() == 2
    assert panel.installed_packages() == tuple(_rows())


def test_set_installed_packages_replaces_previous_rows(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_installed_packages(_rows())
    panel.set_installed_packages(
        [InstalledPackageRow(package_id="gamma", name="Gamma", version="9.9.9")]
    )
    assert panel.list_widget().count() == 1
    assert panel.installed_packages()[0].package_id == "gamma"


def test_set_installed_packages_clears_selection(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_installed_packages(_rows())
    panel.list_widget().setCurrentRow(0)
    assert panel.selected_package_id() == "alpha"
    panel.set_installed_packages([])
    assert panel.selected_package_id() is None
    assert panel.uninstall_button().isEnabled() is False


def test_row_display_text_format(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_installed_packages(_rows())
    item = panel.list_widget().item(0)
    assert item is not None
    assert "Alpha" in item.text()
    assert "alpha" in item.text()
    assert "0.1.0" in item.text()


# ---------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------


def test_install_button_emits_install_requested(qtbot: object) -> None:
    panel = _panel(qtbot)
    received: list[bool] = []
    panel.install_requested.connect(lambda: received.append(True))
    panel.install_button().click()
    assert received == [True]


def test_refresh_button_emits_refresh_requested(qtbot: object) -> None:
    panel = _panel(qtbot)
    received: list[bool] = []
    panel.refresh_requested.connect(lambda: received.append(True))
    panel.refresh_button().click()
    assert received == [True]


def test_uninstall_button_emits_uninstall_requested_with_selected_id(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_installed_packages(_rows())
    panel.list_widget().setCurrentRow(1)
    received: list[str] = []
    panel.uninstall_requested.connect(received.append)
    panel.uninstall_button().click()
    assert received == ["beta"]


def test_uninstall_button_disabled_without_selection(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_installed_packages(_rows())
    assert panel.uninstall_button().isEnabled() is False
    panel.list_widget().setCurrentRow(0)
    assert panel.uninstall_button().isEnabled() is True
    panel.list_widget().setCurrentRow(-1)
    assert panel.uninstall_button().isEnabled() is False
