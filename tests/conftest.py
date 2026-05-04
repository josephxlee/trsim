"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from workbench.domain.types import PositionENU


@pytest.fixture
def sample_position() -> PositionENU:
    """A sample ENU position for tests."""
    return PositionENU(x=100.0, y=200.0, z=10.0)
