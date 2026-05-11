"""Variant build runner — 4-tier dataset chain build (plan/07 § 7.4.5a).

Task B (post-Phase 7.6) — runs :class:`PipelineRunner` once per
:class:`DatasetVariant`, writes one HDF5 per variant under a shared
output root, and emits a :class:`VariantsManifest` so the Step 2
evaluator can recover the (A / B / C / D) split without re-reading the
HDF5 attrs.

Lifecycle:

1. Caller supplies a :class:`SampleSpec` + tuple of
   :class:`VariantBuildPlan` records.
2. :meth:`VariantBuildRunner.run` iterates the plans, constructing a
   fresh :class:`DatasetBuilder` per variant. Each plan's
   ``progress_callback`` calls flow up through the outer runner's
   :data:`VariantProgressCallback`.
3. When every plan finishes (or :meth:`cancel` flips the flag mid-
   run), the runner writes the manifest covering the variants whose
   builders finalised. A run that was cancelled before any plan
   finalised returns ``manifest=None`` and skips the manifest write.

The runner is single-pass — re-running an existing instance is not
supported; build a new runner per chain.

References:

- plan/07 § 7.4.3 — Automatic Dataset Builder.
- plan/07 § 7.4.5a — Pairing Variant 4종 + manifest layout.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from workbench.app.nn.dataset_builder import DatasetBuilder
from workbench.app.nn.pipeline_runner import (
    PairingScenarioSpec,
    PipelineRunner,
    default_pairing_scenario,
)
from workbench.domain.nn import DatasetVariant, SampleSpec
from workbench.domain.nn.variant_manifest import (
    VariantEntry,
    VariantsManifest,
    standard_pairing_variants,
    write_variants_manifest,
)

VariantProgressCallback = Callable[[int, "VariantBuildPlan", int, int], None]
"""``callback(plan_index, plan, n_appended, target_frames)``.

Fired after every successful :meth:`DatasetBuilder.append` while
iterating ``plans``. ``target_frames`` is the plan's ``frames``
attribute (never ``None``) so the UI can render a percentage
without re-reading the plan.
"""


@dataclass(frozen=True, slots=True)
class VariantBuildPlan:
    """One variant's build instructions.

    Attributes:
        variant: Physics-condition flags. Drives the on-disk
            :class:`DatasetVariant` recorded in the HDF5 + manifest.
        dataset_filename: File name **relative to** the runner's
            ``output_root`` (e.g. ``"pairing_variant_A.h5"``). The
            same string lands in :attr:`VariantEntry.dataset_path`.
        scenario: :class:`PairingScenarioSpec` driving the
            :class:`PipelineRunner`.
        frames: Number of frames to execute for this variant
            (``>= 0``; ``0`` writes an empty dataset).

    Raises:
        ValueError: For empty ``dataset_filename`` or negative
            ``frames``.
    """

    variant: DatasetVariant
    dataset_filename: str
    scenario: PairingScenarioSpec
    frames: int

    def __post_init__(self) -> None:
        if not self.dataset_filename:
            msg = "VariantBuildPlan.dataset_filename must be non-empty"
            raise ValueError(msg)
        if self.frames < 0:
            msg = f"VariantBuildPlan.frames must be >= 0, got {self.frames}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class VariantBuildResult:
    """One variant's build outcome.

    Attributes:
        plan: The :class:`VariantBuildPlan` that produced this result.
        dataset_path: Absolute output path the HDF5 was written to.
        frames_executed: Samples actually finalised (less than
            ``plan.frames`` if the runner was cancelled mid-variant).
        cancelled: ``True`` when the builder was cancelled before its
            frame count reached ``plan.frames``.
    """

    plan: VariantBuildPlan
    dataset_path: Path
    frames_executed: int
    cancelled: bool


def standard_pairing_build_plans(
    *,
    target_count: int = 3,
    frames_per_variant: int = 100,
    scenario: PairingScenarioSpec | None = None,
) -> tuple[VariantBuildPlan, ...]:
    """Return the plan/07 § 7.4.5a standard 4-tier Pairing preset.

    The variants + dataset_filenames are sourced from
    :func:`standard_pairing_variants`; every plan shares the same
    scenario (the Pairing GT is closed-form, so the same scenario
    works for every variant).

    Args:
        target_count: Number of targets fed to
            :func:`default_pairing_scenario`. Ignored when
            ``scenario`` is supplied.
        frames_per_variant: Frame count for every plan (``>= 0``).
        scenario: Optional pre-built :class:`PairingScenarioSpec`.
            When ``None`` the function calls
            :func:`default_pairing_scenario(target_count)`.

    Returns:
        Tuple of four :class:`VariantBuildPlan` (A / B / C / D).
    """
    if frames_per_variant < 0:
        msg = f"frames_per_variant must be >= 0, got {frames_per_variant}"
        raise ValueError(msg)
    base_variants = standard_pairing_variants()
    shared_scenario = (
        scenario if scenario is not None else default_pairing_scenario(target_count=target_count)
    )
    return tuple(
        VariantBuildPlan(
            variant=entry.variant,
            dataset_filename=str(entry.dataset_path),
            scenario=shared_scenario,
            frames=frames_per_variant,
        )
        for entry in base_variants
    )


class VariantBuildRunner:
    """Run every :class:`VariantBuildPlan` and emit a :class:`VariantsManifest`.

    Attributes:
        spec: SampleSpec every plan's :class:`DatasetBuilder` collects
            against. ``spec.spec_id`` ends up in the manifest header.
        plans: Tuple of plans, executed in order. Plan ``variant_id``
            values must be unique (mirrors :class:`VariantsManifest`).
        output_root: Directory the per-variant HDF5 files + manifest
            are written under. Created if absent.
        manifest_filename: File name (under ``output_root``) the
            manifest is saved as. Defaults to
            ``"{spec.spec_id}_variants_manifest.toml"``.
        dataset_id_prefix: Optional prefix for each variant's
            :attr:`DatasetBuilder.dataset_id`; the suffix is the
            variant_id. Empty -> ``f"{spec.spec_id}_{variant_id}"``.

    Raises:
        ValueError: For empty plans, duplicate variant_id across
            plans, mismatched spec.
    """

    def __init__(
        self,
        *,
        spec: SampleSpec,
        plans: tuple[VariantBuildPlan, ...],
        output_root: Path | str,
        manifest_filename: str | None = None,
        dataset_id_prefix: str = "",
        progress_callback: VariantProgressCallback | None = None,
    ) -> None:
        if not plans:
            msg = "VariantBuildRunner.plans must contain at least one plan"
            raise ValueError(msg)
        seen: set[str] = set()
        for p in plans:
            vid = p.variant.variant_id
            if vid in seen:
                msg = f"VariantBuildRunner.plans contains duplicate variant_id {vid!r}"
                raise ValueError(msg)
            seen.add(vid)

        self._spec = spec
        self._plans = plans
        self._output_root = Path(output_root)
        self._manifest_filename = manifest_filename or f"{spec.spec_id}_variants_manifest.toml"
        self._dataset_id_prefix = dataset_id_prefix
        self._progress_callback = progress_callback

        self._cancelled = False
        self._current_builder: DatasetBuilder | None = None
        self._current_plan_index: int | None = None

    # ------------------------------------------------------------------
    # Surface
    # ------------------------------------------------------------------

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def current_plan_index(self) -> int | None:
        """Index of the plan currently being built, or ``None`` between plans."""
        return self._current_plan_index

    @property
    def manifest_path(self) -> Path:
        """Absolute path the manifest is written to on a successful run."""
        return self._output_root / self._manifest_filename

    def cancel(self) -> None:
        """Flag cancellation. Idempotent.

        The in-flight :class:`DatasetBuilder` is also cancelled so the
        :class:`PipelineRunner` exits cleanly at the next frame
        boundary.
        """
        self._cancelled = True
        if self._current_builder is not None:
            self._current_builder.cancel()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self) -> tuple[VariantsManifest | None, tuple[VariantBuildResult, ...]]:
        """Iterate every plan, finalising each variant's HDF5.

        Returns:
            ``(manifest, results)``.

            ``manifest`` is the :class:`VariantsManifest` containing
            one :class:`VariantEntry` per variant that finalised.
            ``None`` when the runner was cancelled before any plan
            finalised (so no manifest was written).

            ``results`` is one :class:`VariantBuildResult` per plan
            actually entered (cancelled-before-first-plan returns the
            empty tuple).
        """
        self._output_root.mkdir(parents=True, exist_ok=True)

        results: list[VariantBuildResult] = []
        entries: list[VariantEntry] = []

        for index, plan in enumerate(self._plans):
            if self._cancelled:
                break
            self._current_plan_index = index
            output_path = (self._output_root / plan.dataset_filename).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            dataset_id = self._dataset_id_for(plan.variant)

            builder = DatasetBuilder(
                spec=self._spec,
                variant=plan.variant,
                dataset_id=dataset_id,
                output_path=output_path,
                target_samples=plan.frames,
                progress_callback=self._make_plan_progress(index, plan),
            )
            self._current_builder = builder

            pipeline = PipelineRunner(builder=builder, scenario=plan.scenario)
            pipeline.run_pairing_dataset(n_frames=plan.frames)

            meta = builder.finalize(
                scenarios=("variant_pipeline",),
                extra={"variant_id": plan.variant.variant_id},
            )
            cancelled_mid_variant = builder.is_cancelled and meta.total_samples < plan.frames

            results.append(
                VariantBuildResult(
                    plan=plan,
                    dataset_path=output_path,
                    frames_executed=meta.total_samples,
                    cancelled=cancelled_mid_variant,
                )
            )
            entries.append(
                VariantEntry(
                    variant=plan.variant,
                    dataset_path=Path(plan.dataset_filename),
                )
            )
            self._current_builder = None

        self._current_plan_index = None

        if not entries:
            return None, tuple(results)

        manifest = VariantsManifest(spec_id=self._spec.spec_id, entries=tuple(entries))
        write_variants_manifest(self.manifest_path, manifest)
        return manifest, tuple(results)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _dataset_id_for(self, variant: DatasetVariant) -> str:
        if self._dataset_id_prefix:
            return f"{self._dataset_id_prefix}{variant.variant_id}"
        return f"{self._spec.spec_id}_{variant.variant_id}"

    def _make_plan_progress(
        self, index: int, plan: VariantBuildPlan
    ) -> Callable[[int, int | None], None]:
        callback = self._progress_callback
        if callback is None:
            return _noop_progress

        def _on_plan_progress(n_appended: int, _target: int | None) -> None:
            callback(index, plan, n_appended, plan.frames)

        return _on_plan_progress


def _noop_progress(_n: int, _target: int | None) -> None:
    """Sentinel progress callback when the runner has none."""
