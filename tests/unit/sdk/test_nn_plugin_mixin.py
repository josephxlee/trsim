"""NNPluginMixin Protocol tests (Phase 6.2)."""

from __future__ import annotations

from pathlib import Path

from workbench.sdk.protocols import NNPluginMixin, PairingProtocol


class _MinimalNNPairing:
    """Concrete NN-backed Pairing — minimal implementation for the
    runtime-checkable Protocol surface (plan/07 § 7.3.1)."""

    model_architecture: str
    weights_path: Path
    framework_origin: str

    def __init__(self, weights: Path) -> None:
        self.model_architecture = "mlp_3x64"
        self.weights_path = weights
        self.framework_origin = "numpy_only"
        self._loaded: Path | None = None

    def load_weights(self, path: Path) -> None:
        self._loaded = path

    def declare_internal_probes(self) -> dict[str, type]:
        return {"layer1_activation": object}


class _BarePairing:
    """Pairing-shaped plugin that does NOT implement the NN mixin."""


def test_minimal_nn_pairing_satisfies_nn_plugin_mixin() -> None:
    plugin = _MinimalNNPairing(Path("./weights/pairing.npz"))
    assert isinstance(plugin, NNPluginMixin)


def test_bare_pairing_does_not_satisfy_nn_plugin_mixin() -> None:
    """A plugin without the model_architecture / weights_path / etc.
    surface must not satisfy the runtime-checkable mixin.
    """
    plugin = _BarePairing()
    assert not isinstance(plugin, NNPluginMixin)


def test_nn_plugin_mixin_does_not_force_pairing_protocol() -> None:
    """The NN mixin is orthogonal to the stage Protocol: a class can
    satisfy NNPluginMixin without being a Pairing plugin (and vice
    versa).
    """
    plugin = _MinimalNNPairing(Path("./weights/pairing.npz"))
    # Stage protocol is empty in the SDK MVP, so any object satisfies
    # it. The point of this test is to lock the orthogonality contract
    # — if PairingProtocol grows required methods later, the
    # _MinimalNNPairing fixture above will fail this isinstance check
    # until it provides them, surfacing the breakage explicitly.
    assert isinstance(plugin, PairingProtocol)


def test_load_weights_is_callable_on_instance() -> None:
    """The Pipeline invokes ``plugin.load_weights(path)`` once after
    configure(). The Protocol body is empty; concrete plugins provide
    the implementation. Verify the call goes through.
    """
    p = Path("./weights/pairing.npz")
    plugin = _MinimalNNPairing(p)
    plugin.load_weights(p)
    # The fixture records the loaded path so we can assert the call
    # actually reached the implementation.
    assert plugin._loaded == p


def test_declare_internal_probes_returns_dict() -> None:
    plugin = _MinimalNNPairing(Path("./weights/pairing.npz"))
    probes = plugin.declare_internal_probes()
    assert isinstance(probes, dict)
    assert "layer1_activation" in probes
