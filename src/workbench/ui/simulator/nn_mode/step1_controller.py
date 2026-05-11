"""Step 1 Dataset Builder controller (Phase 6.4c + task 2, plan/07 § 7.4.3).

Wires :class:`workbench.ui.simulator.nn_mode.step1_dataset.Step1DatasetPanel`
to a real scenario-driven :class:`workbench.app.nn.PipelineRunner` that
generates Pairing samples via the FMCW Triangle physics and the
hardcoded default scenario.

Scope (current MVP):

- The controller listens to the panel's ``build_requested`` /
  ``cancel_requested`` signals.
- ``Build Dataset`` opens a :class:`DatasetBuilder`, runs
  :meth:`PipelineRunner.run_pairing_dataset` for ``target`` frames
  using :func:`default_pairing_scenario`, finalises the file, and
  reports the result in the panel log.
- ``Cancel`` flips the in-flight builder's cancelled flag; the runner
  reads ``builder.is_cancelled`` between frames and breaks out cleanly.

A future sub-step will let the panel pick the scenario from the
Editor's ScenarioComposer (Phase 4.5) instead of hardcoding
``default_pairing_scenario``. The signal / controller wiring stays
the same.
"""

from __future__ import annotations

from pathlib import Path

from workbench.app.nn import (
    DatasetBuilder,
    PipelineRunner,
    default_pairing_scenario,
)
from workbench.domain.nn import DatasetVariant, FieldSpec, SampleSpec
from workbench.ui.simulator.nn_mode.step1_dataset import Step1DatasetPanel

_BUFFER_SIZE = 16
"""SampleSpec up_beats / down_beats / pair_indices leading axis length.

Padding slots beyond the active target count carry zeros (beats) /
``-1`` (GT). :func:`pairing_loss` excludes ``-1`` from the
denominator so a fixed-size buffer is safe for variable target counts.
"""


def _default_pairing_spec() -> SampleSpec:
    """Pairing SampleSpec used by the dataset build (plan/07 § 7.4.5b)."""
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (_BUFFER_SIZE,), "complex64", "Up-sweep beat list"),
            FieldSpec("down_beats", (_BUFFER_SIZE,), "complex64", "Down-sweep beat list"),
        ),
        labels=(FieldSpec("pair_indices", (_BUFFER_SIZE,), "int32", "GT pair index per up beat"),),
    )


class NNStep1Controller:
    """Glue between the Step 1 panel and the DatasetBuilder + PipelineRunner.

    Attributes:
        panel: The panel this controller drives.
        target_count: Number of targets in the hardcoded default
            scenario (1..3). Future sub-step replaces this with a
            user-picked scenario.
    """

    def __init__(
        self,
        panel: Step1DatasetPanel,
        *,
        target_count: int = 3,
        seed: int = 0,
    ) -> None:
        # seed kept on the constructor surface for backward compat
        # with earlier random-loop tests; the scenario-driven build is
        # deterministic so the value is unused.
        del seed
        self.panel = panel
        self.target_count = target_count
        self._builder: DatasetBuilder | None = None

        self.panel.build_requested.connect(self._on_build)
        self.panel.cancel_requested.connect(self._on_cancel)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_build(self) -> None:
        try:
            target = int(self.panel.frames_edit().text())
        except ValueError:
            self.panel.set_status("error: Frames must be an integer")
            self.panel.append_log("Build aborted: invalid Frames value")
            return
        if target < 0:
            self.panel.set_status("error: Frames must be >= 0")
            self.panel.append_log("Build aborted: Frames < 0")
            return

        output_text = self.panel.output_edit().text().strip()
        if not output_text:
            self.panel.set_status("error: Output path required")
            self.panel.append_log("Build aborted: empty output path")
            return
        output_path = Path(output_text)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        spec = _default_pairing_spec()
        variant = DatasetVariant(variant_id="A")
        self._builder = DatasetBuilder(
            spec=spec,
            variant=variant,
            dataset_id=output_path.stem or "pairing_dataset",
            output_path=output_path,
            target_samples=target,
            progress_callback=self._on_progress,
        )
        self.panel.set_status(f"building: 0/{target}")
        self.panel.append_log(f"Build started: {output_path}")

        scenario = default_pairing_scenario(target_count=self.target_count)
        runner = PipelineRunner(builder=self._builder, scenario=scenario)

        try:
            runner.run_pairing_dataset(n_frames=target)
        except (ValueError, RuntimeError) as exc:
            self.panel.append_log(f"Build interrupted: {exc}")
        finally:
            meta = self._builder.finalize(
                scenarios=("default_pairing_scenario",),
                extra={"target_count": str(self.target_count)},
            )
            self.panel.set_status(
                f"done: {meta.total_samples}/{target} samples -> {output_path.name}"
            )
            self.panel.append_log(
                f"Build complete: {meta.total_samples} samples written to {output_path}"
            )
            self._builder = None

    def _on_cancel(self) -> None:
        if self._builder is None:
            self.panel.append_log("Cancel: no build in flight")
            return
        self._builder.cancel()
        self.panel.append_log("Cancel requested; stopping at next frame")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _on_progress(self, n_appended: int, target: int | None) -> None:
        if target is None:
            self.panel.set_status(f"building: {n_appended} samples")
        else:
            self.panel.set_status(f"building: {n_appended}/{target}")
