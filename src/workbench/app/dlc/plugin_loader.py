"""Plugin Loader — entry-point import for installed packages (plan/17 § 17.4.2).

Phase 7.3 — turns each :class:`LoadedPackage` 's
``entry_points`` mapping into actual Python class references that
the Pipeline can mount into its stage slots. The loader inspects
two kinds of entry-point targets:

1. ``module:attr`` — Python-import target. The module path is taken
   relative to the package root (``LoadedPackage.root``); ``attr``
   is the class / callable to register.
2. Filesystem-path target (e.g. ``resources/radars/``) — passed
   through unchanged; the ResourceLibrary (Phase 7.4) resolves it
   against ``LoadedPackage.root``.

Slot conventions follow plan/17 § 17.2.4:

- ``trsim.plugins.tracker`` / ``trsim.plugins.pairing`` /
  ``trsim.plugins.detector`` / ``trsim.plugins.angle_estimator``
  / ``trsim.plugins.classifier`` -> Python-import targets.
- ``trsim.resources.maps`` / ``trsim.resources.radars`` /
  ``trsim.resources.targets`` -> directory path targets.
- ``trsim.ui.panels`` -> Python-import targets.

The loader is intentionally lazy about error handling: a single
broken entry point logs an error and does not abort the whole
:meth:`load_all` pass; the workbench keeps starting with the
remaining good packages.

Security note: importing arbitrary Python from third-party packages
is the user's choice; the MVP trusts the package contents. plan/17
§ 17.2.8 layers signature checks / sandboxing later.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workbench.app.dlc.package_manager import LoadedPackage, PackageManager

_PYTHON_IMPORT_SLOT_PREFIXES: tuple[str, ...] = (
    "trsim.plugins.",
    "trsim.ui.",
)

# Singleton entry-point slots that resolve to a Python class via
# ``module:attr`` — same target shape as ``_PYTHON_IMPORT_SLOT_PREFIXES``
# but the slot name is exact (no trailing dot, no sub-categorisation).
# Phase 9 § 19.7.5+ "Plugin discovery" introduces ``trsim.physics_model``
# for plan/19 PhysicsModelProtocol implementations.
_PYTHON_IMPORT_EXACT_SLOTS: frozenset[str] = frozenset(
    {
        "trsim.physics_model",
        "trsim.tracker",
        "trsim.pairing",
        "trsim.predictor",
        "trsim.classifier",
        "trsim.data_associator",
        "trsim.angle_estimator",
        "trsim.detector",
        "trsim.dut_adapter",
    }
)

_PATH_SLOT_PREFIXES: tuple[str, ...] = ("trsim.resources.",)


@dataclass(frozen=True, slots=True)
class LoadedPlugin:
    """One resolved entry point.

    Attributes:
        slot: Entry-point slot name (``"trsim.plugins.tracker"``).
        package_id: Owning package's id.
        target: Original entry-point string from the manifest.
        attribute: For Python-import slots, the imported class /
            callable. ``None`` for path slots (the target string is
            the only thing that matters).
        resource_dir: For path slots, the resolved absolute
            directory. ``None`` for Python-import slots.
    """

    slot: str
    package_id: str
    target: str
    attribute: object | None = None
    resource_dir: Path | None = None


@dataclass(frozen=True, slots=True)
class PluginLoadError:
    """One entry in :attr:`PluginLoader.load_errors`.

    Attributes:
        package_id: Package whose entry point failed to load.
        slot: Entry-point slot name.
        target: The entry-point string from the manifest.
        message: Human-readable English failure reason.
    """

    package_id: str
    slot: str
    target: str
    message: str


def _is_python_import_slot(slot: str) -> bool:
    if slot in _PYTHON_IMPORT_EXACT_SLOTS:
        return True
    return any(slot.startswith(p) for p in _PYTHON_IMPORT_SLOT_PREFIXES)


def _is_path_slot(slot: str) -> bool:
    return any(slot.startswith(p) for p in _PATH_SLOT_PREFIXES)


class PluginLoader:
    """Loads :class:`LoadedPackage.manifest.entry_points` into Python objects.

    Attributes:
        manager: :class:`PackageManager` providing the installed
            packages.
    """

    def __init__(self, manager: PackageManager) -> None:
        self.manager = manager
        self._plugins_by_slot: dict[str, list[LoadedPlugin]] = {}
        self._load_errors: list[PluginLoadError] = []

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_all(self) -> Mapping[str, tuple[LoadedPlugin, ...]]:
        """Walk every installed package and resolve its entry points.

        The caller is expected to have invoked
        :meth:`PackageManager.scan` first; this method does not
        re-scan. Re-running replaces the previous state.

        Returns:
            Mapping ``slot_name -> tuple[LoadedPlugin, ...]`` for
            every slot that picked up at least one plugin. Slots
            with no plugins are absent from the result.

        Notes:
            Errors during this pass go to :attr:`load_errors`; the
            loop continues with the next entry point.
        """
        self._plugins_by_slot = {}
        self._load_errors = []
        for pid in self.manager.installed_ids():
            pkg = self.manager.get(pid)
            if pkg is None:
                continue
            for slot, target in pkg.manifest.entry_points.items():
                plugin = self._resolve_entry_point(pkg, slot, target)
                if plugin is None:
                    continue
                self._plugins_by_slot.setdefault(slot, []).append(plugin)
        return {slot: tuple(plugins) for slot, plugins in self._plugins_by_slot.items()}

    def _resolve_entry_point(
        self, pkg: LoadedPackage, slot: str, target: str
    ) -> LoadedPlugin | None:
        if _is_python_import_slot(slot):
            return self._load_python_target(pkg, slot, target)
        if _is_path_slot(slot):
            return self._load_path_target(pkg, slot, target)
        self._load_errors.append(
            PluginLoadError(
                package_id=pkg.package_id,
                slot=slot,
                target=target,
                message=(
                    "unknown slot; expected trsim.plugins.* / trsim.ui.* / "
                    "trsim.resources.* or a singleton slot "
                    f"in {sorted(_PYTHON_IMPORT_EXACT_SLOTS)!r}"
                ),
            )
        )
        return None

    def _load_python_target(
        self, pkg: LoadedPackage, slot: str, target: str
    ) -> LoadedPlugin | None:
        if ":" not in target:
            self._load_errors.append(
                PluginLoadError(
                    package_id=pkg.package_id,
                    slot=slot,
                    target=target,
                    message="Python entry point must be 'module:attribute'",
                )
            )
            return None
        module_part, _, attr_name = target.partition(":")
        module_part = module_part.strip()
        attr_name = attr_name.strip()
        if not module_part or not attr_name:
            self._load_errors.append(
                PluginLoadError(
                    package_id=pkg.package_id,
                    slot=slot,
                    target=target,
                    message="Python entry point must have non-empty module and attribute",
                )
            )
            return None

        try:
            module = _import_from_package_root(pkg.root, module_part)
        except (OSError, ImportError, SyntaxError) as exc:
            self._load_errors.append(
                PluginLoadError(
                    package_id=pkg.package_id,
                    slot=slot,
                    target=target,
                    message=f"import failed: {exc}",
                )
            )
            return None

        if not hasattr(module, attr_name):
            self._load_errors.append(
                PluginLoadError(
                    package_id=pkg.package_id,
                    slot=slot,
                    target=target,
                    message=f"module {module_part!r} has no attribute {attr_name!r}",
                )
            )
            return None

        return LoadedPlugin(
            slot=slot,
            package_id=pkg.package_id,
            target=target,
            attribute=getattr(module, attr_name),
        )

    def _load_path_target(self, pkg: LoadedPackage, slot: str, target: str) -> LoadedPlugin | None:
        resolved = (pkg.root / target).resolve()
        if not resolved.is_dir():
            self._load_errors.append(
                PluginLoadError(
                    package_id=pkg.package_id,
                    slot=slot,
                    target=target,
                    message=f"resource path is not a directory: {resolved}",
                )
            )
            return None
        return LoadedPlugin(
            slot=slot,
            package_id=pkg.package_id,
            target=target,
            resource_dir=resolved,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def plugins_for_slot(self, slot: str) -> tuple[LoadedPlugin, ...]:
        return tuple(self._plugins_by_slot.get(slot, ()))

    def all_slots(self) -> tuple[str, ...]:
        return tuple(sorted(self._plugins_by_slot.keys()))

    @property
    def load_errors(self) -> tuple[PluginLoadError, ...]:
        return tuple(self._load_errors)


def _import_from_package_root(root: Path, module_name: str) -> Any:
    """Import ``module_name`` from a file under ``root``.

    Accepts both dot-style (``"pkg.sub.mod"``) and slash-style
    (``"pkg/sub/mod"``) module paths — plan/17 § 17.2.4 manifest
    examples use slash, while a pure-Python author may prefer dots.
    Backslash separators are normalised the same way so a Windows
    author writing ``"ui\\panel"`` is not surprised.

    Looks for ``root / <module_name>.py`` first, then for a package
    ``root / <module_name> / __init__.py``. The module is loaded
    into a unique private name to avoid clashing with the host
    workbench's sys.modules entries.
    """
    normalised = module_name.replace("\\", "/").replace("/", ".")
    parts = [p for p in normalised.split(".") if p]
    if not parts:
        msg = f"module path {module_name!r} resolves to an empty segment list"
        raise ImportError(msg)

    candidate_file = root.joinpath(*parts[:-1], parts[-1] + ".py")
    candidate_pkg = root.joinpath(*parts) / "__init__.py"
    if candidate_file.is_file():
        target_path = candidate_file
    elif candidate_pkg.is_file():
        target_path = candidate_pkg
    else:
        msg = (
            f"cannot find {module_name!r} under {root} "
            f"(looked for {candidate_file} and {candidate_pkg})"
        )
        raise ImportError(msg)

    # Use a stable, package-prefixed module name so reload semantics
    # are predictable and so two packages cannot collide on the same
    # plain module name. Use the normalised dot form so two manifests
    # spelling the same module differently (slash vs dot) still share
    # one sys.modules slot.
    unique_name = f"workbench_dlc.{root.name}.{'.'.join(parts)}"
    spec = importlib.util.spec_from_file_location(unique_name, target_path)
    if spec is None or spec.loader is None:
        msg = f"could not create import spec for {target_path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    spec.loader.exec_module(module)
    return module
