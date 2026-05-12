"""Variant 4-tier manifest schema (task 4, plan/07 § 7.4.5a).

Records every :class:`DatasetVariant` that contributed to a Pairing
NN training run, mapping it to the HDF5 dataset file written by
:class:`workbench.app.nn.DatasetBuilder`. The Step 2 evaluator + the
Compare UI consume the manifest to recover "what physics conditions
produced this file" without re-reading the HDF5 attrs.

File layout (plan/07 § 7.4.5a) — sibling to the dataset files:

::

    workspace/datasets/
    ├── pairing_variant_A.h5
    ├── pairing_variant_B.h5
    ├── pairing_variant_C.h5
    ├── pairing_variant_D.h5
    └── pairing_variants_manifest.toml      <- this module's I/O target

TOML schema:

::

    [manifest]
    spec_id = "pairing"

    [[variants]]
    variant_id = "A"
    description = "ideal"
    sea_state = 0
    attitude_on = false
    sidelobe_on = false
    dataset_path = "pairing_variant_A.h5"

    [[variants]]
    variant_id = "B"
    ...

Standard 4-tier preset is exposed via
:func:`standard_pairing_variants` (Variant_A ideal / _B attitude
only / _C sidelobe only / _D full realistic).
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from workbench.domain.nn.sample_spec import DatasetVariant


@dataclass(frozen=True, slots=True)
class VariantEntry:
    """One variant + its on-disk dataset path.

    Attributes:
        variant: Physics-condition flags (Phase 6.1
            :class:`DatasetVariant`).
        dataset_path: Path to the HDF5 file holding the variant's
            samples. Relative paths are resolved against the
            manifest's parent directory at load time.
    """

    variant: DatasetVariant
    dataset_path: Path


@dataclass(frozen=True, slots=True)
class VariantsManifest:
    """List of :class:`VariantEntry` for one SampleSpec task.

    Attributes:
        spec_id: SampleSpec identifier (e.g. ``"pairing"``).
        entries: Tuple of VariantEntry, ``len >= 1``. Order is the
            on-disk variant order — A then B then C then D is the
            plan/07 § 7.4.5a convention.

    Raises:
        ValueError: For empty spec_id, empty entries, duplicate
            variant_id across entries.
    """

    spec_id: str
    entries: tuple[VariantEntry, ...]

    def __post_init__(self) -> None:
        if not self.spec_id:
            msg = "VariantsManifest.spec_id must be a non-empty string"
            raise ValueError(msg)
        if not self.entries:
            msg = "VariantsManifest.entries must contain at least one VariantEntry"
            raise ValueError(msg)
        seen: set[str] = set()
        for e in self.entries:
            if e.variant.variant_id in seen:
                msg = f"VariantsManifest contains duplicate variant_id {e.variant.variant_id!r}"
                raise ValueError(msg)
            seen.add(e.variant.variant_id)


def standard_pairing_variants() -> tuple[VariantEntry, ...]:
    """Return the plan/07 § 7.4.5a standard 4-tier Pairing preset.

    A (ideal) -> B (attitude only) -> C (sidelobe only) -> D (full
    realistic). Dataset paths are the plan example file names.
    """
    return (
        VariantEntry(
            variant=DatasetVariant(
                variant_id="A",
                sea_state=0,
                attitude_on=False,
                sidelobe_on=False,
                description="ideal",
            ),
            dataset_path=Path("pairing_variant_A.h5"),
        ),
        VariantEntry(
            variant=DatasetVariant(
                variant_id="B",
                sea_state=3,
                attitude_on=True,
                sidelobe_on=False,
                description="attitude only",
            ),
            dataset_path=Path("pairing_variant_B.h5"),
        ),
        VariantEntry(
            variant=DatasetVariant(
                variant_id="C",
                sea_state=0,
                attitude_on=False,
                sidelobe_on=True,
                description="sidelobe only",
            ),
            dataset_path=Path("pairing_variant_C.h5"),
        ),
        VariantEntry(
            variant=DatasetVariant(
                variant_id="D",
                sea_state=3,
                attitude_on=True,
                sidelobe_on=True,
                description="full realistic",
            ),
            dataset_path=Path("pairing_variant_D.h5"),
        ),
    )


# ---------------------------------------------------------------------
# TOML write
# ---------------------------------------------------------------------


def _toml_quote(value: str) -> str:
    """Render ``value`` as a basic TOML quoted string.

    Escapes backslashes + double quotes; control characters are not
    expected in our schema (variant_id / spec_id are kebab-case +
    SemVer-style; description / dataset_path are user-supplied but
    free of control characters in practice).
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_variants_manifest(path: Path | str, manifest: VariantsManifest) -> None:
    """Persist ``manifest`` to ``path`` as TOML.

    Args:
        path: Output ``.toml`` file. Parent directory must exist.
        manifest: :class:`VariantsManifest` to serialise.

    The write is atomic at the filesystem level only insofar as
    :meth:`pathlib.Path.write_text` is — Editor-level transactional
    save (Phase 7.5) wraps this in a tmp-and-rename later.
    """
    lines: list[str] = []
    lines.append("[manifest]")
    lines.append(f"spec_id = {_toml_quote(manifest.spec_id)}")
    lines.append("")
    for e in manifest.entries:
        lines.append("[[variants]]")
        lines.append(f"variant_id = {_toml_quote(e.variant.variant_id)}")
        lines.append(f"description = {_toml_quote(e.variant.description)}")
        lines.append(f"sea_state = {e.variant.sea_state}")
        attitude_str = "true" if e.variant.attitude_on else "false"
        sidelobe_str = "true" if e.variant.sidelobe_on else "false"
        lines.append(f"attitude_on = {attitude_str}")
        lines.append(f"sidelobe_on = {sidelobe_str}")
        lines.append(f"dataset_path = {_toml_quote(str(e.dataset_path).replace(chr(92), '/'))}")
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------
# TOML read
# ---------------------------------------------------------------------


def load_variants_manifest(path: Path | str) -> VariantsManifest:
    """Read + validate a Variants manifest TOML.

    Args:
        path: ``.toml`` file path written by :func:`write_variants_manifest`
            (or hand-authored).

    Returns:
        Parsed :class:`VariantsManifest`. Each ``VariantEntry.dataset_path``
        is left as written — relative paths stay relative; the caller
        joins against the manifest directory when materialising arrays.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: For missing sections / fields, or dataclass-level
            validation failures (empty variant_id, sea_state out of
            range, etc.).
    """
    # Strip UTF-8 BOM the same way as the DLC manifest reader —
    # PowerShell 5.1's ``Out-File -Encoding utf8`` writes one, and
    # ``tomllib`` would otherwise reject it.
    path_obj = Path(path)
    raw = path_obj.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        blob = tomllib.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        msg = f"{path_obj}: variants manifest is not valid UTF-8 ({exc})"
        raise ValueError(msg) from exc
    return _manifest_from_blob(blob, source=str(path_obj))


def _manifest_from_blob(
    blob: Mapping[str, object], *, source: str = "<memory>"
) -> VariantsManifest:
    manifest_blob = blob.get("manifest")
    if not isinstance(manifest_blob, Mapping):
        msg = f"{source}: [manifest] section missing or not a table"
        raise ValueError(msg)
    spec_id = str(manifest_blob.get("spec_id", ""))

    variants_raw = blob.get("variants", [])
    if not isinstance(variants_raw, list):
        msg = f"{source}: [[variants]] must be an array of tables"
        raise ValueError(msg)

    entries: list[VariantEntry] = []
    for i, v in enumerate(variants_raw):
        if not isinstance(v, Mapping):
            msg = f"{source}: variants[{i}] must be a table"
            raise ValueError(msg)
        sea_state_raw = v.get("sea_state", 0)
        if not isinstance(sea_state_raw, int) or isinstance(sea_state_raw, bool):
            msg = f"{source}: variants[{i}].sea_state must be an integer"
            raise ValueError(msg)
        variant = DatasetVariant(
            variant_id=str(v.get("variant_id", "")),
            sea_state=sea_state_raw,
            attitude_on=bool(v.get("attitude_on", False)),
            sidelobe_on=bool(v.get("sidelobe_on", False)),
            description=str(v.get("description", "")),
        )
        dataset_path = Path(str(v.get("dataset_path", "")))
        entries.append(VariantEntry(variant=variant, dataset_path=dataset_path))

    return VariantsManifest(spec_id=spec_id, entries=tuple(entries))
