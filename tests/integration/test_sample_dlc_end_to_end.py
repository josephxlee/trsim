"""End-to-end check that the in-tree sample DLC round-trips through
the entire ``sdk build`` -> ``sdk test`` -> ``install`` workflow
(Phase 7 C6, plan/17 § 17.2.4).

Failing this test = the reference DLC at ``examples/dlc/simple_
pairing_demo/`` is broken, which means the
:file:`docs/dev_guide/creating_dlc.md` tutorial is broken too.
That's the highest-leverage signal we can hand a new DLC author —
"the example we shipped doesn't even work" is the kind of bug
they would hit immediately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench import sdk
from workbench.cli.main import main
from workbench.io.package_io import MANIFEST_FILENAME, read_manifest_from_package

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DLC_SOURCE = REPO_ROOT / "examples" / "dlc" / "simple_pairing_demo"


def test_sample_dlc_source_exists() -> None:
    """Guard: the reference DLC source directory is on disk."""
    assert SAMPLE_DLC_SOURCE.is_dir(), SAMPLE_DLC_SOURCE
    assert (SAMPLE_DLC_SOURCE / MANIFEST_FILENAME).is_file()


def test_sample_dlc_manifest_parses_via_python_api() -> None:
    """Hand-rolled manifest must parse through the canonical loader."""
    from workbench.domain.dlc.manifest import load_manifest_from_toml

    manifest = load_manifest_from_toml(SAMPLE_DLC_SOURCE / MANIFEST_FILENAME)
    assert manifest.package.package_id == "simple-pairing-demo"
    assert manifest.package.name == "Simple Pairing Demo"
    assert manifest.compatibility.trsim_min_version


def test_sample_dlc_round_trips_through_sdk_build_then_install(tmp_path: Path) -> None:
    """build -> test -> install via the Python API, all from the sample."""
    pkg = sdk.build_package(SAMPLE_DLC_SOURCE, tmp_path / "demo.trsim-pkg")
    assert pkg.is_file()

    result = sdk.test_package(pkg)
    assert result.package_id == "simple-pairing-demo"
    # Sample manifest fills description + author so no soft issues fire.
    assert result.issues == ()

    pkgs_root = tmp_path / "installed"
    rc = main(["install", "--package", str(pkg), "--packages-root", str(pkgs_root)])
    assert rc == 0
    target = pkgs_root / "simple-pairing-demo"
    assert (target / MANIFEST_FILENAME).is_file()
    assert (target / "resources" / "maps" / "demo_map.toml").is_file()
    assert (target / "ui" / "demo_panel.py").is_file()


def test_sample_dlc_manifest_inside_archive_matches_source(tmp_path: Path) -> None:
    """The packaged manifest must round-trip equal to the source manifest."""
    pkg = sdk.build_package(SAMPLE_DLC_SOURCE, tmp_path / "demo.trsim-pkg")
    manifest_inside = read_manifest_from_package(pkg)
    assert manifest_inside.package.package_id == "simple-pairing-demo"
    assert manifest_inside.package.version == "0.1.0"


def test_creating_dlc_tutorial_doc_exists() -> None:
    """Tutorial referenced from examples/dlc/simple_pairing_demo/README.md."""
    tutorial = REPO_ROOT / "docs" / "dev_guide" / "creating_dlc.md"
    assert tutorial.is_file(), tutorial
    # Smoke check: the tutorial references the sample DLC path.
    text = tutorial.read_text(encoding="utf-8")
    assert "simple_pairing_demo" in text


@pytest.mark.parametrize(
    "expected_section",
    ["[package]", "[compatibility]", "[entry_points]", "trsim.ui.panels"],
)
def test_sample_dlc_manifest_has_canonical_sections(expected_section: str) -> None:
    """Authors will copy this manifest; the canonical sections must
    all be present so the copy is a working starting point.
    """
    text = (SAMPLE_DLC_SOURCE / MANIFEST_FILENAME).read_text(encoding="utf-8")
    assert expected_section in text
