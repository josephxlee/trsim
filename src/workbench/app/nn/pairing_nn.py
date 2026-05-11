"""numpy-only Pairing NN reference (plan/07 § 7.4.5b).

Phase 6.5 — first concrete plugin satisfying
:class:`workbench.sdk.protocols.NNPluginMixin`. The "NN" here is a
deterministic nearest-neighbour matcher: the Hungarian algorithm on
``|up_beat[i] - down_beat[j]|`` cost. It exists as a baseline that
real learned weights can be benchmarked against — the FMCW-Triangle
Pairing task is well-suited to closed-form solutions at low SNR, so
a "no-NN" reference is the right zero point.

API per plan/07 § 7.3.1 + § 7.4.5b:

- ``model_architecture`` / ``weights_path`` / ``framework_origin`` —
  mixin attributes.
- ``load_weights(path)`` — no-op (the matcher has no learned
  parameters; the call exists so the workbench's plugin lifecycle
  contract still applies).
- ``declare_internal_probes()`` — declares ``distance_matrix`` as
  an Internal Probe so the UI can render the per-pair cost grid.
- ``predict(up_beats, down_beats)`` — returns the matched
  ``pair_indices`` array (one entry per up beat; ``-1`` for
  unmatched).

References:

- plan/07 § 7.3.1 — NNPluginMixin.
- plan/07 § 7.4.5b — Pairing task definition.
- plan/16 § 16.3.4 — Hungarian assignment baseline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment

FrameworkOrigin = Literal["tensorflow", "pytorch", "numpy_only"]


class NumpyPairingNN:
    """Nearest-neighbour FMCW-Triangle Pairing baseline.

    Attributes:
        model_architecture: ``"numpy_nearest_neighbor_pairing"`` —
            stable identifier surfaced in the dataset manifest.
        weights_path: Optional path to a (non-existent for this
            baseline) weights file. Kept for the NNPluginMixin
            contract.
        framework_origin: ``"numpy_only"``.

    The matcher does not need a constructor argument; defaults match
    the mixin's expected surface.
    """

    model_architecture: str = "numpy_nearest_neighbor_pairing"
    framework_origin: FrameworkOrigin = "numpy_only"

    def __init__(self, *, weights_path: Path | None = None) -> None:
        self.weights_path = weights_path or Path("")
        self._distance_matrix: NDArray[np.float64] | None = None

    # ------------------------------------------------------------------
    # NNPluginMixin surface
    # ------------------------------------------------------------------

    def load_weights(self, path: Path) -> None:
        """No-op — the matcher has no learned parameters.

        The pipeline calls this once after configure() per plan/07
        § 7.3.1; recording the path keeps the manifest accurate.
        """
        self.weights_path = path

    def declare_internal_probes(self) -> dict[str, type]:
        """Expose ``distance_matrix`` as an Internal Probe.

        plan/07 § 7.3.2 — the Probe Panel auto-registers handles for
        every entry declared here. The most recent prediction's cost
        matrix is accessible via :attr:`last_distance_matrix`.
        """
        return {"distance_matrix": np.ndarray}

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(
        self,
        up_beats: NDArray[np.complexfloating],
        down_beats: NDArray[np.complexfloating],
    ) -> NDArray[np.int32]:
        """Return ``pair_indices[i] = j`` matching ``up[i]`` -> ``down[j]``.

        Uses the Hungarian algorithm (scipy linear_sum_assignment) on
        the per-pair cost ``|up[i] - down[j]|``. Globally optimal —
        no greedy short-cuts. Unmatched up beats receive ``-1``;
        when ``len(up) == len(down)`` every up beat is matched.

        Args:
            up_beats: 1-D complex array of N up-sweep beat values.
            down_beats: 1-D complex array of M down-sweep beat values.

        Returns:
            1-D int32 array of length N. ``pair_indices[i]`` is the
            index in ``down_beats`` paired to ``up_beats[i]``, or
            ``-1`` if no match.

        Raises:
            ValueError: If either array is not 1-D.
        """
        if up_beats.ndim != 1:
            msg = f"up_beats must be 1-D, got ndim={up_beats.ndim}"
            raise ValueError(msg)
        if down_beats.ndim != 1:
            msg = f"down_beats must be 1-D, got ndim={down_beats.ndim}"
            raise ValueError(msg)

        n_up = up_beats.size
        n_down = down_beats.size
        pair_indices = np.full(n_up, -1, dtype=np.int32)
        if n_up == 0 or n_down == 0:
            self._distance_matrix = np.zeros((n_up, n_down), dtype=np.float64)
            return pair_indices

        cost = np.abs(up_beats[:, np.newaxis] - down_beats[np.newaxis, :])
        cost = cost.astype(np.float64, copy=False)
        row_ind, col_ind = linear_sum_assignment(cost)
        pair_indices[row_ind] = col_ind.astype(np.int32)
        self._distance_matrix = cost
        return pair_indices

    @property
    def last_distance_matrix(self) -> NDArray[np.float64] | None:
        """Return the cost matrix from the most recent :meth:`predict`.

        ``None`` until :meth:`predict` has been called. The Editor's
        Probe Panel reads this when the user expands the
        ``distance_matrix`` Internal Probe handle.
        """
        return self._distance_matrix
