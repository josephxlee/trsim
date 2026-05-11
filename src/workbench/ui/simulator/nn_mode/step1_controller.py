"""Step 1 Dataset Builder controller (Phase 6.4c, plan/07 § 7.4.3).

Wires :class:`workbench.ui.simulator.nn_mode.step1_dataset.Step1DatasetPanel`
to a real :class:`workbench.app.nn.DatasetBuilder`.

Scope (MVP):

- The controller listens to the panel's ``build_requested`` /
  ``cancel_requested`` signals.
- ``Build Dataset`` opens a :class:`DatasetBuilder`, appends a
  user-configured number of dummy Pairing samples (no scenario / no
  Pipeline integration yet), finalises the file, and reports the
  output path in the panel's log.
- ``Cancel`` flips the in-flight builder's cancelled flag so the
  next append rejects; if no build is in flight it just logs.

Real scenario + Pipeline integration (Phase 6.5+) replaces the dummy
sample loop with a Pipeline run that pipes
:func:`workbench.domain.pipeline.step` probes into the same
``builder.append``. The signal / controller wiring stays the same.

The controller never touches Qt outside the panel API — it stores no
QObjects beyond the connected panel — so unit tests can run without
a real event loop.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from workbench.app.nn import DatasetBuilder
from workbench.domain.nn import DatasetVariant, FieldSpec, SampleSpec
from workbench.ui.simulator.nn_mode.step1_dataset import Step1DatasetPanel


def _default_pairing_spec() -> SampleSpec:
    """Pairing SampleSpec used by the demo build (plan/07 § 7.4.5b)."""
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (16,), "complex64", "Up-sweep beat list"),
            FieldSpec("down_beats", (16,), "complex64", "Down-sweep beat list"),
        ),
        labels=(FieldSpec("pair_indices", (16,), "int32", "GT pair index per up beat"),),
    )


class NNStep1Controller:
    """Glue between the Step 1 panel and the DatasetBuilder.

    Attributes:
        panel: The panel this controller drives.
        seed: RNG seed for the dummy demo samples (deterministic
            tests).
    """

    def __init__(self, panel: Step1DatasetPanel, *, seed: int = 0) -> None:
        self.panel = panel
        self._rng = np.random.default_rng(seed=seed)
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

        try:
            for _ in range(target):
                if self._builder.is_cancelled:
                    break
                self._builder.append(*self._random_pairing_sample())
        except RuntimeError as exc:
            self.panel.append_log(f"Build interrupted: {exc}")
        finally:
            assert self._builder is not None
            meta = self._builder.finalize(scenarios=("demo",))
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
        self.panel.append_log("Cancel requested; stopping at next append")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _on_progress(self, n_appended: int, target: int | None) -> None:
        if target is None:
            self.panel.set_status(f"building: {n_appended} samples")
        else:
            self.panel.set_status(f"building: {n_appended}/{target}")

    def _random_pairing_sample(
        self,
    ) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
        inputs = {
            "up_beats": self._rng.standard_normal(16).astype(np.complex64),
            "down_beats": self._rng.standard_normal(16).astype(np.complex64),
        }
        labels = {
            "pair_indices": self._rng.integers(0, 16, size=16).astype(np.int32),
        }
        return inputs, labels
