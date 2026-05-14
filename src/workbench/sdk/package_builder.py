"""DLC package builder (Phase 7 C2, plan/17 § 17.2.6).

Thin SDK wrapper around :func:`workbench.io.package_io.pack_package`.
Exists so external authors can build a ``.trsim-pkg`` from Python
(``import workbench.sdk as sdk; sdk.build_package(...)``) without
reaching into the IO module's private structure.

The CLI binding lives in :mod:`workbench.cli.main` under the
``trsim sdk build`` subcommand.

Circular-import note (P8 follow-up): ``workbench.io.package_io``
imports ``workbench.sdk.manifest`` to parse the manifest. That
triggers ``workbench.sdk.__init__``, which previously eagerly
imported ``pack_package`` from this module — closing the loop.
We now defer the ``pack_package`` import to function-call time so
the partially-initialised ``workbench.io.package_io`` finishes
defining ``pack_package`` before this wrapper needs it.
"""

from __future__ import annotations

from pathlib import Path


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
    from workbench.io.package_io import pack_package

    return pack_package(source, output)
