"""``.trsim-pkg`` package I/O (Phase 7 DLC C1, plan/17 § 17.2.4).

A ``.trsim-pkg`` is a zip archive containing a ``manifest.toml`` at
the root + plugin source / resource directories underneath it. This
module provides:

- :func:`pack_package` — directory ``source_dir`` -> zip at
  ``output_path``. Validates that ``source_dir/manifest.toml`` exists
  and parses as a valid :class:`PackageManifest`.
- :func:`unpack_package` — zip at ``pkg_path`` -> directory
  ``target_dir``. Refuses to extract a zip without a root
  ``manifest.toml`` or with paths that escape ``target_dir``
  (zip-slip defence).

Both ops are I/O-only — they don't touch the PackageManager or any
runtime state. Higher-level wiring (``trsim install`` CLI) calls
these primitives and then hands the unpacked directory to the
PackageManager scanner.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterator
from pathlib import Path

from workbench.domain.dlc.manifest import PackageManifest, load_manifest_from_toml

MANIFEST_FILENAME: str = "manifest.toml"
"""Required file at the zip root. Mirrors plan/17 § 17.2.4."""

PACKAGE_SUFFIX: str = ".trsim-pkg"
"""Canonical file extension. Validation enforces it on pack output."""


def pack_package(source_dir: Path | str, output_path: Path | str) -> Path:
    """Pack ``source_dir`` into a ``.trsim-pkg`` zip at ``output_path``.

    The output file's extension must be ``.trsim-pkg`` so downstream
    tooling can recognise it from the path alone. ``source_dir`` must
    contain a top-level ``manifest.toml`` that parses through
    :func:`workbench.domain.dlc.manifest.load_manifest_from_toml`;
    anything else is rejected before any bytes are written.

    All regular files under ``source_dir`` are added to the archive
    using POSIX-style relative paths so the zip is portable across
    Windows / Linux / macOS hosts. Symlinks and special files are
    skipped silently (the MVP DLC layout is plain text + resources).

    Args:
        source_dir: Directory containing ``manifest.toml`` + plugin /
            resource trees.
        output_path: Destination path. Must end with ``.trsim-pkg``.

    Returns:
        Absolute :class:`Path` to the written archive.

    Raises:
        FileNotFoundError: ``source_dir`` does not exist or has no
            ``manifest.toml``.
        ValueError: Output path suffix is not ``.trsim-pkg`` or the
            manifest fails to parse.
        NotADirectoryError: ``source_dir`` is not a directory.
    """
    src = Path(source_dir).expanduser().resolve()
    out = Path(output_path).expanduser().resolve()

    if out.suffix != PACKAGE_SUFFIX:
        msg = f"output_path must end with {PACKAGE_SUFFIX!r}, got {out.name!r}"
        raise ValueError(msg)
    if not src.exists():
        msg = f"source_dir does not exist: {src}"
        raise FileNotFoundError(msg)
    if not src.is_dir():
        msg = f"source_dir must be a directory, got {src}"
        raise NotADirectoryError(msg)
    manifest_path = src / MANIFEST_FILENAME
    if not manifest_path.is_file():
        msg = f"source_dir missing {MANIFEST_FILENAME}: {src}"
        raise FileNotFoundError(msg)
    # Validate manifest before any I/O — bail out fast on malformed
    # packages so the on-disk artifact never exists in a broken state.
    load_manifest_from_toml(manifest_path)

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in _iter_regular_files(src):
            rel = entry.relative_to(src).as_posix()
            archive.write(entry, arcname=rel)
    return out


def unpack_package(pkg_path: Path | str, target_dir: Path | str) -> Path:
    """Extract a ``.trsim-pkg`` zip into ``target_dir``.

    ``target_dir`` must not already exist (the call fails fast rather
    than silently merging into an existing tree). The zip must contain
    a root ``manifest.toml``; any entry whose normalised path escapes
    ``target_dir`` is rejected (zip-slip CVE-2018-1002201 defence).

    The unpacked manifest is parsed before the function returns so
    callers get a clear error for malformed payloads even after the
    archive succeeds.

    Args:
        pkg_path: ``.trsim-pkg`` archive (zip).
        target_dir: Destination directory. Must not exist yet.

    Returns:
        Absolute :class:`Path` to ``target_dir`` after extraction.

    Raises:
        FileNotFoundError: ``pkg_path`` does not exist.
        FileExistsError: ``target_dir`` already exists.
        ValueError: Archive has no root ``manifest.toml``, a zip-slip
            entry, or a malformed manifest.
    """
    pkg = Path(pkg_path).expanduser().resolve()
    target = Path(target_dir).expanduser().resolve()

    if not pkg.is_file():
        msg = f"package archive not found: {pkg}"
        raise FileNotFoundError(msg)
    if target.exists():
        msg = f"target_dir already exists: {target}"
        raise FileExistsError(msg)

    with zipfile.ZipFile(pkg, mode="r") as archive:
        names = archive.namelist()
        if MANIFEST_FILENAME not in names:
            msg = f"{pkg.name} is not a valid {PACKAGE_SUFFIX}: missing root {MANIFEST_FILENAME}"
            raise ValueError(msg)
        for name in names:
            _reject_unsafe_path(name, target)
        target.mkdir(parents=True, exist_ok=False)
        archive.extractall(target)

    # Validate the manifest from the unpacked tree (mirrors the
    # pack-side validation so corrupt packages can't slip through).
    load_manifest_from_toml(target / MANIFEST_FILENAME)
    return target


def read_manifest_from_package(pkg_path: Path | str) -> PackageManifest:
    """Read and validate the ``manifest.toml`` inside a ``.trsim-pkg``
    without extracting the rest of the archive.

    Useful for ``trsim install`` UX (preview before commit) and for
    CI checks that just need to know what a package declares.

    Args:
        pkg_path: ``.trsim-pkg`` archive.

    Returns:
        Parsed :class:`PackageManifest`.

    Raises:
        FileNotFoundError: ``pkg_path`` missing.
        ValueError: Archive has no root ``manifest.toml`` or the
            manifest fails to parse.
    """
    pkg = Path(pkg_path).expanduser().resolve()
    if not pkg.is_file():
        msg = f"package archive not found: {pkg}"
        raise FileNotFoundError(msg)
    with zipfile.ZipFile(pkg, mode="r") as archive:
        if MANIFEST_FILENAME not in archive.namelist():
            msg = f"{pkg.name} is not a valid {PACKAGE_SUFFIX}: missing root {MANIFEST_FILENAME}"
            raise ValueError(msg)
        raw = archive.read(MANIFEST_FILENAME)
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = f"{MANIFEST_FILENAME} inside {pkg} is not valid UTF-8: {exc}"
        raise ValueError(msg) from exc
    # Re-use the on-disk loader by round-tripping through a temp file
    # is overkill; just re-implement the parse path inline here.
    import tomllib

    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        msg = f"{MANIFEST_FILENAME} inside {pkg} is not valid TOML: {exc}"
        raise ValueError(msg) from exc

    # Defer validation to the same blob loader used by the on-disk
    # path (`load_manifest_from_toml` -> `_manifest_from_blob`).
    from workbench.domain.dlc.manifest import _manifest_from_blob

    return _manifest_from_blob(data, source=str(pkg))


def _iter_regular_files(root: Path) -> Iterator[Path]:
    """Yield every regular file under ``root`` (recursive, skip symlinks)."""
    for entry in root.rglob("*"):
        if entry.is_file() and not entry.is_symlink():
            yield entry


def _reject_unsafe_path(name: str, target: Path) -> None:
    """Reject zip entries whose resolved path escapes ``target``.

    Defends against zip-slip (CVE-2018-1002201) — an attacker could
    embed an entry named ``../../etc/passwd`` to write outside the
    extraction directory.
    """
    candidate = (target / name).resolve()
    try:
        candidate.relative_to(target)
    except ValueError as exc:
        msg = f"zip entry escapes target_dir (zip-slip): {name!r}"
        raise ValueError(msg) from exc
