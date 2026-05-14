"""Deeper DLC validation (Phase 7 C8, plan/17 § 17.2.6).

:mod:`workbench.sdk.test_harness` runs the lightweight smoke check
that ``trsim sdk test`` exposes — manifest parses, soft issues
(missing description / author) reported. This module layers a
deeper validator that DLC authors and CI pipelines can call when
they want stricter feedback before publishing.

What's checked:

- :func:`validate_entry_point_slots(manifest)` — every key in
  ``manifest.entry_points`` is in the curated set of known slot
  names (``trsim.tracker``, ``trsim.ui.panels``,
  ``trsim.resources.maps``, etc.). Unknown slot names produce
  issue strings so the author can correct them before the
  workbench silently ignores the plugin.

Out of scope (future):

- Importing the actual plugin module via PluginLoader (would
  require the DLC's Python dependencies to be installed in the
  CI environment).
- Cross-field manifest invariants (handled by
  :class:`PackageManifest.__post_init__`).
"""

from __future__ import annotations

from workbench.sdk.manifest import PackageManifest

KNOWN_ENTRY_POINT_SLOTS: frozenset[str] = frozenset(
    {
        "trsim.tracker",
        "trsim.pairing",
        "trsim.predictor",
        "trsim.classifier",
        "trsim.data_associator",
        "trsim.angle_estimator",
        "trsim.detector",
        "trsim.ui.panels",
        "trsim.resources.maps",
        "trsim.resources.radars",
        "trsim.resources.targets",
        "trsim.resources.scenarios",
        "trsim.physics_model",
        "trsim.dut_adapter",
    }
)
"""Slot names :class:`workbench.app.dlc.plugin_loader.PluginLoader`
will look at. Anything outside this set is dead-on-arrival at
plugin-load time, so the validator surfaces it as an issue."""


def validate_entry_point_slots(manifest: PackageManifest) -> tuple[str, ...]:
    """Return issue strings for any unknown ``entry_points`` slot name.

    Empty tuple = every slot is in the curated set.

    Args:
        manifest: Parsed :class:`PackageManifest`.

    Returns:
        Sorted tuple of human-readable issue strings. The strings
        carry enough context (slot name + nearest neighbour hint) to
        let an author fix the typo without rereading the docs.
    """
    issues: list[str] = []
    for slot in sorted(manifest.entry_points.keys()):
        if slot not in KNOWN_ENTRY_POINT_SLOTS:
            issues.append(
                f"unknown entry_points slot {slot!r} "
                f"(known slots: {sorted(KNOWN_ENTRY_POINT_SLOTS)})"
            )
    return tuple(issues)
