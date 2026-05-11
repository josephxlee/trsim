"""Plugin Protocols for DLC authors — 11 stable contracts (plan/17 § 17.4.1).

These protocols are the **stable Public API**. Domain refactors must not
break them — DLC packages depend only on this module. See plan/02 § 2.6b
for the SDK Layer contract and plan/19 § 19.8 for ``PhysicsModelProtocol``.

The protocol bodies are intentionally minimal in Phase 0.4 — concrete
``def`` signatures are filled in during Phase 2 (Domain Contracts) when
the data types they exchange (Detection / Track / etc.) become concrete.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

# Framework-origin tag carried by every NN plugin (plan/07 § 7.3.1).
FrameworkOrigin = Literal["tensorflow", "pytorch", "numpy_only"]


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
    """Physics model plugin for Physics Lab Validation Bench (plan/19 § 19.8, v0.40).

    Categories: ``propagation``, ``reflection``, ``dynamics``, ``atmosphere``, ``antenna``.
    Validation Bench ensures only models passing 17+ regression scenarios + analytic
    formula comparison can be used in main simulation (plan/06 § 6.7 v0.40 변경).
    """


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
