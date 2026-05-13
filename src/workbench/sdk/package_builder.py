"""DLC package builder (Phase 7 C2, plan/17 § 17.2.6).

Thin SDK wrapper around :func:`workbench.io.package_io.pack_package`.
Exists so external authors can build a ``.trsim-pkg`` from Python
(``import workbench.sdk as sdk; sdk.build_package(...)``) without
reaching into the IO module's private structure.

The CLI binding lives in :mod:`workbench.cli.main` under the
``trsim sdk build`` subcommand.
"""

from __future__ import annotations

from pathlib import Path

from workbench.io.package_io import pack_package


def build_package(source: Path | str, output: Path | str) -> Path:
    """Build a ``.trsim-pkg`` from ``source`` directory.

    Args:
        source: Directory containing ``manifest.toml`` + plugin /
            resource trees (plan/17 § 17.2.4 layout).
        output: Destination ``.trsim-pkg`` path. Suffix is enforced
            by :func:`pack_package`.

    Returns:
        Absolute :class:`Path` to the written archive.

    Raises:
        ValueError / FileNotFoundError / NotADirectoryError: Forwarded
            from :func:`pack_package`. See that function for the full
            list of failure modes.
    """
    return pack_package(source, output)
