"""Plugin Protocols for DLC authors — 11 stable contracts (plan/17 § 17.4.1).

These protocols are the **stable Public API**. Domain refactors must not
break them — DLC packages depend only on this module. See plan/02 § 2.6b
for the SDK Layer contract and plan/19 § 19.8 for ``PhysicsModelProtocol``.

The protocol bodies are intentionally minimal in Phase 0.4 — concrete
``def`` signatures are filled in during Phase 2 (Domain Contracts) when
the data types they exchange (Detection / Track / etc.) become concrete.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from workbench.domain.physics_lab import PhysicsParam

# Framework-origin tag carried by every NN plugin (plan/07 § 7.3.1).
FrameworkOrigin = Literal["tensorflow", "pytorch", "numpy_only"]

# Physics model categories surfaced in the Library (plan/19 § 19.8.1).
PhysicsModelCategory = Literal[
    "dynamics",
    "rf_propagation",
    "rcs",
    "atmosphere",
    "antenna",
    "other",
]
PhysicsModelTimeMode = Literal["static", "dynamic"]
PhysicsModelVisualization = Literal["2d", "3d", "both", "none"]


@runtime_checkable
class DetectorProtocol(Protocol):
    """Detection stage — CFAR, NN-based, etc.

    Concrete signature lands in Phase 2 (plan/04 § 4.3 Phase 2 + plan/03 § 3.3).
    """


@runtime_checkable
class PairingProtocol(Protocol):
    """FMCW Triangle Up/Down pairing — matches up-sweep and down-sweep peaks.

    See plan/08 § 8.3.5 for FMCW Triangle pairing context.
    """


@runtime_checkable
class AngleEstimatorProtocol(Protocol):
    """Angle estimation from monopulse Σ/Δ channels (plan/03 § 3.2.1h, v0.25)."""


@runtime_checkable
class TrackerProtocol(Protocol):
    """Tracker — EKF / UKF / Particle Filter / NN (plan/16 § 16.3.3)."""


@runtime_checkable
class PredictorProtocol(Protocol):
    """Track predictor — propagates state between updates."""


@runtime_checkable
class ClassifierProtocol(Protocol):
    """Track classification (type, friendliness, etc.) — stub for MVP."""


@runtime_checkable
class DataAssociatorProtocol(Protocol):
    """Multi-target data association — GNN / JPDA (plan/16 § 16.3.4)."""


@runtime_checkable
class ResourceProtocol(Protocol):
    """Map / Radar / Target resource loader (plan/10 § 10.9)."""


@runtime_checkable
class UIPanelProtocol(Protocol):
    """DLC-provided UI panel — pyqtgraph or PyVista (plan/17 § 17.4.4)."""


@runtime_checkable
class DUTAdapterProtocol(Protocol):
    """HIL DUT communication adapter (plan/18 § 18.7).

    Includes Lock-step Handshake methods for Reference Timing (plan/18 § 18.16.4, v0.39).
    """


@runtime_checkable
class PhysicsModelProtocol(Protocol):
    """Physics model plugin for Physics Lab (plan/19 § 19.8, v0.40).

    Implementations supply a name + a category + a parameter spec
    list + a ``compute`` method that maps an input state-dict to an
    output state-dict. The Physics Lab Library lists every registered
    model under the ``Models`` category, the Parameters pane auto-
    generates sliders from :attr:`parameters`, and the Validation
    Bench feeds measured data into :meth:`compute` to score the
    model against truth.

    plan/06 § 6.7 v0.40: user-defined physics-model plugins **are**
    allowed (reversed from the v0.27..v0.39 ban) because the
    Validation Bench gates which plugins reach the main simulation.

    All members are properties or zero-arg methods so the
    ``runtime_checkable`` :func:`isinstance` check stays cheap.
    """

    @property
    def name(self) -> str:
        """Display label + lookup key. Must be unique inside a Library."""
        ...

    @property
    def category(self) -> PhysicsModelCategory:
        """Which physical domain the model lives in."""
        ...

    @property
    def parameters(self) -> Sequence[PhysicsParam]:
        """Parameter specs the Auto-Parameters widget uses for sliders."""
        ...

    @property
    def time_mode(self) -> PhysicsModelTimeMode:
        """``"static"`` = single-shot function (no ``dt`` argument).
        ``"dynamic"`` = needs ``dt`` and integrates state forward.
        """
        ...

    @property
    def visualization(self) -> PhysicsModelVisualization:
        """Preferred Library viz when this model is selected."""
        ...

    def compute(
        self,
        state: Mapping[str, Any],
        params: Mapping[str, float],
        dt_s: float | None,
    ) -> Mapping[str, Any]:
        """Run one evaluation.

        Args:
            state: Input state. For ``time_mode == "static"`` this is
                usually empty; for ``"dynamic"`` it carries the
                previous frame.
            params: Current slider values keyed by
                :attr:`PhysicsParam.name`.
            dt_s: ``None`` when ``time_mode == "static"``; the step
                size otherwise.

        Returns:
            New state mapping. Static models return the result of the
            computation (e.g. ``{"rcs_m2": 25.4}``); dynamic models
            return the propagated state (e.g. ``{"y_m": ..., "v_m_s":
            ...}``).
        """
        ...


@runtime_checkable
class TestObjectProtocol(Protocol):
    """Physics Lab Test Object plugin (PL-9.3e, plan/19 § 19.7.4).

    Implementations are any dataclass-like object exposing the three
    attributes the Library + Mesh registry need:

    - ``name``: display label.
    - ``visual``: short kind identifier (``"sphere"``, ``"cube"``,
      or a custom string registered via
      :func:`workbench.ui.physics_lab.register_visual_kind_builder`).
    - ``analytic_rcs_m2(wavelength_m)``: closed-form RCS at the given
      wavelength; ``None`` when the object has no analytic reference
      (Point / Plane / user-defined custom kinds without RCS).

    Built-in 9 Test Objects (Sphere / Cube / Plate / Cylinder / Cone /
    Trihedral / Wall / Plane / Point) all satisfy this protocol; user
    plugins instantiate any class that exposes the same surface.
    """

    name: str
    visual: str

    def analytic_rcs_m2(self, wavelength_m: float) -> float | None: ...


# Stop pytest from collecting the Protocol class as a test (its name
# starts with "Test"). Set after class definition so ``runtime_checkable``
# does not include ``__test__`` in the required-attribute set.
TestObjectProtocol.__test__ = False  # type: ignore[attr-defined]


@runtime_checkable
class NNPluginMixin(Protocol):
    """Optional mixin marking a plugin as NN-backed (plan/07 § 7.3.1).

    Concrete plugins combine this mixin with one of the stage Protocols
    (e.g. ``class MyNNPairing(PairingProtocol, NNPluginMixin)``). The
    Pipeline still treats the object through its stage Protocol; the
    learning / visualisation tooling is the only consumer that picks
    up the NN-specific surface declared here.

    Attributes:
        model_architecture: Free-form architecture tag
            (``"mlp_3x64"``, ``"resnet_small"``, custom string).
        weights_path: On-disk path to the weights file. The
            workbench loads weights once after ``configure()`` via
            :meth:`load_weights`.
        framework_origin: Which ML framework the weights came from.
            Constrained to :data:`FrameworkOrigin` so the
            ``workbench-train`` CLI can pick the right importer.
    """

    model_architecture: str
    weights_path: Path
    framework_origin: FrameworkOrigin

    def load_weights(self, path: Path) -> None:
        """Load the model weights from ``path``.

        Called automatically by the Pipeline right after
        ``configure()`` so the plugin enters its first frame with the
        graph already populated. Idempotent — calling twice with the
        same path must be a no-op.
        """

    def declare_internal_probes(self) -> dict[str, type]:
        """Return ``name -> dtype`` for internal observation points.

        Default implementations return ``{}`` (no internal probes).
        The Probe Panel (plan/07 § 7.3.2) uses the result to register
        Internal Probe handles for activations / attention weights /
        feature maps.
        """
