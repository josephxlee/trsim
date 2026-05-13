"""Physics-model registry tests (Phase 9 H2)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from workbench.app.physics_lab import (
    BouncingBallModel,
    FreeSpaceLossModel,
    GravityOnlyModel,
    builtin_physics_models,
    default_physics_models,
    physics_models_from,
    register_physics_model,
    registered_physics_models,
    unregister_all_physics_models,
)
from workbench.domain.physics_lab import PhysicsParam
from workbench.sdk.protocols import PhysicsModelProtocol


@pytest.fixture(autouse=True)
def _isolate_registry() -> None:
    """Each test starts with an empty plug-in registry."""
    unregister_all_physics_models()


# ---------------------------------------------------------------------
# Built-in factory
# ---------------------------------------------------------------------


def test_builtin_physics_models_returns_three_in_fixed_order() -> None:
    models = builtin_physics_models()
    assert len(models) == 3
    assert isinstance(models[0], GravityOnlyModel)
    assert isinstance(models[1], BouncingBallModel)
    assert isinstance(models[2], FreeSpaceLossModel)


def test_builtin_factory_returns_fresh_instances_per_call() -> None:
    a = builtin_physics_models()
    b = builtin_physics_models()
    for ai, bi in zip(a, b, strict=True):
        assert ai is not bi
        assert type(ai) is type(bi)


def test_builtin_models_satisfy_protocol() -> None:
    for model in builtin_physics_models():
        assert isinstance(model, PhysicsModelProtocol)


# ---------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------


class _StubModel:
    """Minimal PhysicsModelProtocol implementation for tests."""

    def __init__(self, name: str = "stub") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> str:
        return "other"

    @property
    def parameters(self) -> Sequence[PhysicsParam]:
        return ()

    @property
    def time_mode(self) -> str:
        return "static"

    @property
    def visualization(self) -> str:
        return "2d"

    def compute(
        self,
        state: Mapping[str, Any],
        params: Mapping[str, float],
        dt_s: float | None,
    ) -> Mapping[str, Any]:
        return dict(state)


def test_register_physics_model_appends_to_registry() -> None:
    stub = _StubModel("my_stub_a")
    register_physics_model(stub)
    assert stub in registered_physics_models()


def test_registered_physics_models_does_not_include_builtins() -> None:
    assert registered_physics_models() == ()
    register_physics_model(_StubModel("my_stub_b"))
    assert len(registered_physics_models()) == 1
    assert not any(isinstance(m, GravityOnlyModel) for m in registered_physics_models())


def test_register_rejects_non_protocol() -> None:
    with pytest.raises(TypeError, match=r"PhysicsModelProtocol"):
        register_physics_model("not a model")  # type: ignore[arg-type]


def test_register_rejects_duplicate_with_builtin_name() -> None:
    with pytest.raises(ValueError, match=r"already registered"):
        register_physics_model(_StubModel(name=GravityOnlyModel().name))


def test_register_rejects_duplicate_of_plugin_name() -> None:
    register_physics_model(_StubModel("dup_name"))
    with pytest.raises(ValueError, match=r"already registered"):
        register_physics_model(_StubModel("dup_name"))


def test_unregister_all_clears_plugin_only() -> None:
    register_physics_model(_StubModel("clearable"))
    assert registered_physics_models()
    unregister_all_physics_models()
    assert registered_physics_models() == ()
    # Built-ins still accessible.
    assert len(builtin_physics_models()) == 3


# ---------------------------------------------------------------------
# Default assembly
# ---------------------------------------------------------------------


def test_default_physics_models_is_builtins_when_no_plugins() -> None:
    defaults = default_physics_models()
    assert len(defaults) == 3
    builtin_names = {m.name for m in builtin_physics_models()}
    assert {m.name for m in defaults} == builtin_names


def test_default_physics_models_appends_plugins_in_insertion_order() -> None:
    a = _StubModel("plugin_a")
    b = _StubModel("plugin_b")
    register_physics_model(a)
    register_physics_model(b)
    defaults = default_physics_models()
    assert len(defaults) == 5
    # Built-ins first, plug-ins in insertion order.
    assert defaults[3].name == "plugin_a"
    assert defaults[4].name == "plugin_b"


def test_default_physics_models_returns_tuple_not_list() -> None:
    assert isinstance(default_physics_models(), tuple)


# ---------------------------------------------------------------------
# Custom assembly
# ---------------------------------------------------------------------


def test_physics_models_from_builtins_only() -> None:
    models = physics_models_from(include_builtins=True)
    assert len(models) == 3


def test_physics_models_from_without_builtins() -> None:
    models = physics_models_from(include_builtins=False)
    assert models == ()


def test_physics_models_from_with_extra_keeps_order() -> None:
    s = _StubModel("custom_x")
    models = physics_models_from(include_builtins=True, extra=(s,))
    assert len(models) == 4
    assert models[-1] is s


def test_physics_models_from_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match=r"Duplicate physics-model names"):
        physics_models_from(
            include_builtins=True,
            extra=(_StubModel(name=GravityOnlyModel().name),),
        )
