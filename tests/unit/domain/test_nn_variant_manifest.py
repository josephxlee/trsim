"""Variant manifest tests (task 4, plan/07 § 7.4.5a)."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.domain.nn import (
    DatasetVariant,
    VariantEntry,
    VariantsManifest,
    load_variants_manifest,
    standard_pairing_variants,
    write_variants_manifest,
)

# ---------------------------------------------------------------------
# Standard preset
# ---------------------------------------------------------------------


def test_standard_pairing_variants_has_4_entries() -> None:
    entries = standard_pairing_variants()
    assert len(entries) == 4
    assert [e.variant.variant_id for e in entries] == ["A", "B", "C", "D"]


def test_standard_pairing_variant_a_is_ideal() -> None:
    a = standard_pairing_variants()[0]
    assert a.variant.sea_state == 0
    assert a.variant.attitude_on is False
    assert a.variant.sidelobe_on is False


def test_standard_pairing_variant_d_is_full_realistic() -> None:
    d = standard_pairing_variants()[3]
    assert d.variant.sea_state == 3
    assert d.variant.attitude_on is True
    assert d.variant.sidelobe_on is True


def test_standard_pairing_variant_paths_match_plan() -> None:
    entries = standard_pairing_variants()
    assert entries[0].dataset_path == Path("pairing_variant_A.h5")
    assert entries[3].dataset_path == Path("pairing_variant_D.h5")


# ---------------------------------------------------------------------
# VariantsManifest validation
# ---------------------------------------------------------------------


def test_construct_manifest_with_standard_entries() -> None:
    manifest = VariantsManifest(spec_id="pairing", entries=standard_pairing_variants())
    assert manifest.spec_id == "pairing"
    assert len(manifest.entries) == 4


def test_empty_spec_id_rejected() -> None:
    with pytest.raises(ValueError, match=r"spec_id"):
        VariantsManifest(spec_id="", entries=standard_pairing_variants())


def test_empty_entries_rejected() -> None:
    with pytest.raises(ValueError, match=r"entries"):
        VariantsManifest(spec_id="pairing", entries=())


def test_duplicate_variant_id_rejected() -> None:
    a = standard_pairing_variants()[0]
    with pytest.raises(ValueError, match=r"duplicate variant_id"):
        VariantsManifest(spec_id="pairing", entries=(a, a))


# ---------------------------------------------------------------------
# TOML write -> read round-trip
# ---------------------------------------------------------------------


def test_write_then_read_round_trip(tmp_path: Path) -> None:
    out = tmp_path / "pairing_variants_manifest.toml"
    manifest = VariantsManifest(spec_id="pairing", entries=standard_pairing_variants())
    write_variants_manifest(out, manifest)

    loaded = load_variants_manifest(out)
    assert loaded.spec_id == "pairing"
    assert len(loaded.entries) == 4
    assert [e.variant.variant_id for e in loaded.entries] == ["A", "B", "C", "D"]
    # Variant D round-trip details
    d = loaded.entries[3]
    assert d.variant.sea_state == 3
    assert d.variant.attitude_on is True
    assert d.variant.sidelobe_on is True
    assert d.variant.description == "full realistic"
    assert d.dataset_path == Path("pairing_variant_D.h5")


def test_write_preserves_dataset_path_value(tmp_path: Path) -> None:
    out = tmp_path / "m.toml"
    manifest = VariantsManifest(
        spec_id="pairing",
        entries=(
            VariantEntry(
                variant=DatasetVariant(variant_id="X"),
                dataset_path=Path("subdir/x.h5"),
            ),
        ),
    )
    write_variants_manifest(out, manifest)
    loaded = load_variants_manifest(out)
    # POSIX-style normalisation in TOML write -> loaded path matches.
    assert loaded.entries[0].dataset_path == Path("subdir/x.h5")


# ---------------------------------------------------------------------
# TOML read failure cases
# ---------------------------------------------------------------------


def test_load_missing_manifest_section_raises(tmp_path: Path) -> None:
    f = tmp_path / "bad.toml"
    f.write_text("[[variants]]\nvariant_id = 'A'\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"\[manifest\]"):
        load_variants_manifest(f)


def test_load_variants_with_wrong_sea_state_type_rejected(tmp_path: Path) -> None:
    """``sea_state = "high"`` is a TOML string, not an int."""
    f = tmp_path / "bad.toml"
    f.write_text(
        '[manifest]\nspec_id = "pairing"\n'
        '[[variants]]\nvariant_id = "A"\nsea_state = "high"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"sea_state"):
        load_variants_manifest(f)


def test_load_invalid_variant_id_propagates(tmp_path: Path) -> None:
    f = tmp_path / "bad.toml"
    f.write_text(
        '[manifest]\nspec_id = "pairing"\n[[variants]]\nvariant_id = ""\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"variant_id"):
        load_variants_manifest(f)


def test_load_nonexistent_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_variants_manifest(tmp_path / "does_not_exist.toml")
