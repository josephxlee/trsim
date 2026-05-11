"""Pipeline runner — scenario-driven Pairing dataset build (plan/07 § 7.4.3).

Phase 6 후속 (task 2). Replaces the random demo loop in
:class:`workbench.ui.simulator.nn_mode.step1_controller.NNStep1Controller`
with a scenario-driven loop that propagates target state, evaluates the
FMCW Triangle beat-frequency pair per target, and hands the result to
a :class:`DatasetBuilder`.

Scope (MVP):

- CV motion only — range advances by ``v_radial * dt`` each frame.
- 1..N_BUFFER targets per scenario, padded to the fixed
  ``up_beats / down_beats`` buffer length declared in the
  :class:`SampleSpec`. Unfilled slots get zeros + GT ``-1``.
- FMCW Triangle physics via :func:`workbench.physics.propagation.fmcw.
  fmcw_triangle_beats`. No ExtendedTarget / multipath / atmosphere.
- GT ``pair_indices[i] = i`` for ``i < n_targets``; ``-1`` thereafter
  (pairing_loss already excludes ``-1`` from the denominator).

Out of scope:

- Detector noise / CFAR false alarms — beats are computed analytically.
- ExtendedTarget glint, multipath, atmosphere — Variant axes that
  task 4 introduces.
- Trained NN inference — NumpyPairingNN is only used downstream
  (Step 2 evaluation), not during the dataset build.

References:

- plan/07 § 7.2.3 — pipeline stage slot system.
- plan/07 § 7.4.3 — Automatic Dataset Builder loop.
- plan/07 § 7.4.5b — Pairing GT generation contract.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from workbench.app.nn.dataset_builder import DatasetBuilder
from workbench.physics.propagation.fmcw import fmcw_triangle_beats

ProbeCallback = Callable[[str, Mapping[str, Any]], None]
"""Stage-output probe signature (mirrors ``domain.pipeline.ProbeCallback``).

Fired once per frame with ``stage="pairing"`` and payload
``{"up_beats", "down_beats", "pair_indices", "frame_index"}``.
"""


@dataclass(frozen=True, slots=True)
class PairingScenarioSpec:
    """Lightweight scenario record for the Pairing dataset builder.

    Attributes:
        targets_initial_state: Tuple of ``(range_m, radial_velocity_mps)``
            pairs, one per target. ``range_m > 0``; ``radial_velocity``
            sign convention: positive = approaching radar.
        dt_s: Frame period [s]. Range advances by ``-v_radial * dt`` each
            frame (approaching target -> range shrinks).
        carrier_freq_hz: Carrier frequency [Hz]. Default 9.4 GHz X-band.
        bandwidth_hz: Sweep bandwidth [Hz]. Default 150 MHz.
        sweep_period_s: Single-sweep duration [s]. Default 1 ms.

    Raises:
        ValueError: For empty target list, non-positive range / dt /
            frequency / bandwidth / sweep period.
    """

    targets_initial_state: tuple[tuple[float, float], ...]
    dt_s: float = 0.1
    carrier_freq_hz: float = 9.4e9
    bandwidth_hz: float = 150e6
    sweep_period_s: float = 1e-3

    def __post_init__(self) -> None:
        if not self.targets_initial_state:
            msg = "targets_initial_state must contain at least one target"
            raise ValueError(msg)
        for i, (r, _v) in enumerate(self.targets_initial_state):
            if r <= 0.0:
                msg = f"target {i} range_m must be > 0, got {r}"
                raise ValueError(msg)
        if self.dt_s <= 0.0:
            msg = f"dt_s must be > 0, got {self.dt_s}"
            raise ValueError(msg)
        if self.carrier_freq_hz <= 0.0:
            msg = f"carrier_freq_hz must be > 0, got {self.carrier_freq_hz}"
            raise ValueError(msg)
        if self.bandwidth_hz <= 0.0:
            msg = f"bandwidth_hz must be > 0, got {self.bandwidth_hz}"
            raise ValueError(msg)
        if self.sweep_period_s <= 0.0:
            msg = f"sweep_period_s must be > 0, got {self.sweep_period_s}"
            raise ValueError(msg)


class PipelineRunner:
    """Scenario-driven Pairing dataset orchestrator.

    Hands one ``(up_beats, down_beats, pair_indices)`` record per frame
    to :class:`DatasetBuilder.append`. The builder is responsible for
    validation, progress callback, and finalize / write_dataset.

    Cancellation: a caller that wants to abort mid-run calls
    :meth:`DatasetBuilder.cancel` on the builder this runner was
    constructed with — the next iteration of the frame loop sees
    ``builder.is_cancelled is True`` and breaks before appending.
    """

    def __init__(
        self,
        *,
        builder: DatasetBuilder,
        scenario: PairingScenarioSpec,
        probe_callback: ProbeCallback | None = None,
    ) -> None:
        self._builder = builder
        self._scenario = scenario
        self._probe_callback = probe_callback
        # The spec's up_beats / down_beats / pair_indices fields all
        # share the same leading axis length -> use the first input
        # shape as the buffer size.
        self._buffer_size = int(builder.spec.inputs[0].shape[0])
        if self._buffer_size < len(scenario.targets_initial_state):
            msg = (
                f"SampleSpec buffer size {self._buffer_size} too small for "
                f"{len(scenario.targets_initial_state)} targets in scenario"
            )
            raise ValueError(msg)

    def run_pairing_dataset(self, *, n_frames: int) -> int:
        """Run ``n_frames`` of the Pairing loop.

        Args:
            n_frames: Number of frames to execute. Must be >= 0; ``0``
                is a no-op (useful for "build skeleton then cancel"
                workflows).

        Returns:
            Number of frames actually executed (may be < ``n_frames``
            if the builder was cancelled).

        Raises:
            ValueError: If ``n_frames < 0``.
        """
        if n_frames < 0:
            msg = f"n_frames must be >= 0, got {n_frames}"
            raise ValueError(msg)

        n_targets = len(self._scenario.targets_initial_state)
        frames_executed = 0
        for k in range(n_frames):
            if self._builder.is_cancelled:
                break
            up_beats, down_beats, pair_indices = self._frame_record(k, n_targets)
            if self._probe_callback is not None:
                self._probe_callback(
                    "pairing",
                    {
                        "up_beats": up_beats,
                        "down_beats": down_beats,
                        "pair_indices": pair_indices,
                        "frame_index": k,
                    },
                )
            # The probe callback can flip builder.cancel() mid-frame —
            # re-check before append() so we do not provoke the
            # "append after cancel" RuntimeError on the next call.
            if self._builder.is_cancelled:
                break
            self._builder.append(
                {"up_beats": up_beats, "down_beats": down_beats},
                {"pair_indices": pair_indices},
            )
            frames_executed += 1
        return frames_executed

    def _frame_record(
        self, k: int, n_targets: int
    ) -> tuple[NDArray[np.complex64], NDArray[np.complex64], NDArray[np.int32]]:
        """Build ``(up, down, gt)`` for frame ``k``.

        Range at frame ``k`` is ``r0 - v_radial * k * dt`` (approaching
        target shrinks range; receding extends it). FMCW Triangle beats
        come from :func:`fmcw_triangle_beats`. Padding slots beyond
        ``n_targets`` carry zeros and GT ``-1``.
        """
        scenario = self._scenario
        up = np.zeros(self._buffer_size, dtype=np.complex64)
        down = np.zeros(self._buffer_size, dtype=np.complex64)
        gt = np.full(self._buffer_size, -1, dtype=np.int32)

        for i in range(n_targets):
            r0, v_radial = scenario.targets_initial_state[i]
            range_now = r0 - v_radial * k * scenario.dt_s
            # An unrealistic scenario can push range_now <= 0 after many
            # frames. fmcw_triangle_beats rejects that — propagate as a
            # ValueError to the caller so the scenario tuning is fixed
            # rather than silently producing garbage data.
            f_up, f_down = fmcw_triangle_beats(
                range_m=range_now,
                v_radial_m_s=v_radial,
                bandwidth_hz=scenario.bandwidth_hz,
                sweep_period_s=scenario.sweep_period_s,
                carrier_freq_hz=scenario.carrier_freq_hz,
            )
            up[i] = np.complex64(f_up)
            down[i] = np.complex64(f_down)
            gt[i] = np.int32(i)

        return up, down, gt


def default_pairing_scenario(target_count: int = 3) -> PairingScenarioSpec:
    """Hardcoded default scenario for the Step 1 Editor build button.

    Three targets at well-separated ``(range, v_radial)`` pairs so the
    FMCW Triangle pairing has unambiguous GT. The Editor's
    ScenarioComposer (Phase 4.5) will replace this with a real
    user-picked scenario in a later sub-step.

    Args:
        target_count: How many of the preset targets to include
            (1..3). Beyond 3 the function clamps to 3.

    Returns:
        :class:`PairingScenarioSpec` ready for :class:`PipelineRunner`.
    """
    presets: tuple[tuple[float, float], ...] = (
        (1500.0, -80.0),  # near, approaching
        (5000.0, 30.0),  # mid, receding
        (12_000.0, -200.0),  # far, fast approach
    )
    n = max(1, min(target_count, len(presets)))
    return PairingScenarioSpec(targets_initial_state=presets[:n])
