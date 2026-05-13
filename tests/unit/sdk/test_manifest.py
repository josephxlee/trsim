"""DLC manifest.toml schema tests (Phase 7.1, plan/17 § 17.2.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.sdk.manifest import (
    CompatibilitySpec,
    PackageManifest,
    PackageMeta,
    PythonDeps,
    load_manifest_from_toml,
)

_FULL_MANIFEST_TOML = """
[package]
id = "advanced-tracker"
name = "Advanced Tracker for Stealth Targets"
version = "1.2.0"
author = "Researcher Kim <kim@univ.ac.kr>"
description = "Stealth target tracker (CNN + Kalman)"
license = "MIT"
homepage = "https://github.com/researcher/trsim-advanced-tracker"

[compatibility]
trsim_min_version = "0.35.0"
trsim_max_version = "1.x"

[dependencies]
"glint-modeling-extras" = ">=1.0.0"

[entry_points]
"trsim.plugins.tracker" = "advanced_tracker:AdvancedTracker"
"trsim.resources.radars" = "resources/radars/"

[python]
extra_requires = ["torch>=2.0", "scikit-learn>=1.3"]
"""

_MINIMAL_MANIFEST_TOML = """
[package]
id = "minimal-pkg"
name = "Minimal Package"
version = "0.1.0"
license = "Apache-2.0"

[compatibility]
trsim_min_version = "0.35.0"
"""


def _write(tmp_path: Path, body: str) -> Path:
    out = tmp_path / "manifest.toml"
    out.write_text(body, encoding="utf-8")
    return out


# ---------------------------------------------------------------------
# PackageMeta validation
# ---------------------------------------------------------------------


def test_package_meta_full_construction() -> None:
    meta = PackageMeta(
        package_id="advanced-tracker",
        name="Advanced Tracker",
        version="1.2.0",
        license="MIT",
    )
    assert meta.package_id == "advanced-tracker"


@pytest.mark.parametrize(
    "bad_id",
    [
        "",  # empty
        "Advanced-Tracker",  # capitals
        "advanced_tracker",  # underscore
        "-advanced",  # leading hyphen
        "advanced-",  # trailing hyphen
        "advanced tracker",  # whitespace
        "advanced/tracker",  # path
    ],
)
def test_package_meta_rejects_non_kebab_id(bad_id: str) -> None:
    with pytest.raises(ValueError, match=r"package_id"):
        PackageMeta(
            package_id=bad_id,
            name="x",
            version="0.1.0",
            license="MIT",
        )


@pytest.mark.parametrize("bad_version", ["", "1", "1.2", "v1.2.0", "1.2.x", "abc"])
def test_package_meta_rejects_non_semver_version(bad_version: str) -> None:
    with pytest.raises(ValueError, match=r"version"):
        PackageMeta(
            package_id="x",
            name="x",
            version=bad_version,
            license="MIT",
        )


def test_package_meta_rejects_empty_license() -> None:
    with pytest.raises(ValueError, match=r"license"):
        PackageMeta(
            package_id="x",
            name="x",
            version="0.1.0",
            license="",
        )


def test_package_meta_accepts_semver_with_prerelease() -> None:
    """SemVer ``1.0.0-rc.1`` and ``1.0.0+build.5`` must pass."""
    PackageMeta(package_id="x", name="x", version="1.0.0-rc.1", license="MIT")
    PackageMeta(package_id="x", name="x", version="1.0.0+build.5", license="MIT")


# ---------------------------------------------------------------------
# CompatibilitySpec validation
# ---------------------------------------------------------------------


def test_compatibility_min_only() -> None:
    spec = CompatibilitySpec(trsim_min_version="0.35.0")
    assert spec.trsim_max_version == ""


def test_compatibility_empty_min_rejected() -> None:
    with pytest.raises(ValueError, match=r"trsim_min_version"):
        CompatibilitySpec(trsim_min_version="")


def test_compatibility_non_semver_min_rejected() -> None:
    with pytest.raises(ValueError, match=r"trsim_min_version"):
        CompatibilitySpec(trsim_min_version="0.35")


def test_compatibility_freeform_max_accepted() -> None:
    """``1.x`` as max_version is plan/17 § 17.2.4 example and must pass."""
    spec = CompatibilitySpec(trsim_min_version="0.35.0", trsim_max_version="1.x")
    assert spec.trsim_max_version == "1.x"


# ---------------------------------------------------------------------
# load_manifest_from_toml — full round-trip
# ---------------------------------------------------------------------


def test_full_manifest_round_trip(tmp_path: Path) -> None:
    path = _write(tmp_path, _FULL_MANIFEST_TOML)
    manifest = load_manifest_from_toml(path)

    assert isinstance(manifest, PackageManifest)
    assert manifest.package.package_id == "advanced-tracker"
    assert manifest.package.version == "1.2.0"
    assert manifest.package.license == "MIT"
    assert manifest.compatibility.trsim_min_version == "0.35.0"
    assert manifest.compatibility.trsim_max_version == "1.x"
    assert dict(manifest.dependencies) == {"glint-modeling-extras": ">=1.0.0"}
    assert manifest.entry_points["trsim.plugins.tracker"] == "advanced_tracker:AdvancedTracker"
    assert manifest.python.extra_requires == ("torch>=2.0", "scikit-learn>=1.3")


def test_minimal_manifest_round_trip(tmp_path: Path) -> None:
    path = _write(tmp_path, _MINIMAL_MANIFEST_TOML)
    manifest = load_manifest_from_toml(path)
    assert manifest.package.package_id == "minimal-pkg"
    assert manifest.dependencies == {}
    assert manifest.entry_points == {}
    assert manifest.python.extra_requires == ()


def test_manifest_with_utf8_bom_parses(tmp_path: Path) -> None:
    """PowerShell 5.1 ``Out-File -Encoding utf8`` writes a BOM and tomllib
    would otherwise reject the file with "Invalid statement (at line 1,
    column 1)" — surfaced during MVP_GUIDE § 4.1 manifest authoring.
    """
    path = tmp_path / "manifest.toml"
    body_bytes = b"\xef\xbb\xbf" + _MINIMAL_MANIFEST_TOML.encode("utf-8")
    path.write_bytes(body_bytes)
    manifest = load_manifest_from_toml(path)
    assert manifest.package.package_id == "minimal-pkg"


def test_manifest_invalid_utf8_rejected(tmp_path: Path) -> None:
    """A manifest written in cp949 / latin-1 surfaces a clean error."""
    path = tmp_path / "manifest.toml"
    # 0xFF is invalid as the first byte of a UTF-8 sequence.
    path.write_bytes(b"\xff\xfe[package]\n")
    with pytest.raises(ValueError, match=r"not valid UTF-8"):
        load_manifest_from_toml(path)


def test_missing_package_section_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, '[compatibility]\ntrsim_min_version = "0.35.0"\n')
    with pytest.raises(ValueError, match=r"\[package\]"):
        load_manifest_from_toml(path)


def test_missing_compatibility_section_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        '[package]\nid = "x"\nname = "x"\nversion = "0.1.0"\nlicense = "MIT"\n',
    )
    with pytest.raises(ValueError, match=r"\[compatibility\]"):
        load_manifest_from_toml(path)


def test_invalid_id_in_toml_propagates_dataclass_error(tmp_path: Path) -> None:
    body = """
[package]
id = "INVALID_ID"
name = "x"
version = "0.1.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"
"""
    path = _write(tmp_path, body)
    with pytest.raises(ValueError, match=r"package_id"):
        load_manifest_from_toml(path)


def test_load_nonexistent_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_manifest_from_toml(tmp_path / "does_not_exist.toml")


# ---------------------------------------------------------------------
# PythonDeps + PackageManifest dataclass shape
# ---------------------------------------------------------------------


def test_python_deps_default_is_empty_tuple() -> None:
    assert PythonDeps().extra_requires == ()


def test_manifest_default_collections_are_empty() -> None:
    manifest = PackageManifest(
        package=PackageMeta(package_id="x", name="x", version="0.1.0", license="MIT"),
        compatibility=CompatibilitySpec(trsim_min_version="0.35.0"),
    )
    assert manifest.dependencies == {}
    assert manifest.entry_points == {}
    assert manifest.python.extra_requires == ()
