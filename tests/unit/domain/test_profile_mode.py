"""Profile mode toggle tests (Phase 3 Q4, plan/03 § 3.5.0c)."""

from __future__ import annotations

import pytest

from workbench.domain.timing import ProfileGate, ProfileMode

# ---------------------------------------------------------------------
# ProfileMode enum
# ---------------------------------------------------------------------


def test_profile_mode_has_three_members() -> None:
    assert {m.value for m in ProfileMode} == {"off", "explicit", "live"}


def test_profile_mode_constructor_accepts_string() -> None:
    assert ProfileMode("off") is ProfileMode.OFF
    assert ProfileMode("explicit") is ProfileMode.EXPLICIT
    assert ProfileMode("live") is ProfileMode.LIVE


def test_profile_mode_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        ProfileMode("verbose")


# ---------------------------------------------------------------------
# ProfileGate behavior
# ---------------------------------------------------------------------


def test_gate_defaults_to_live() -> None:
    gate = ProfileGate()
    assert gate.mode is ProfileMode.LIVE
    assert gate.should_record() is True


def test_gate_off_never_records() -> None:
    gate = ProfileGate(mode=ProfileMode.OFF)
    for _ in range(5):
        assert gate.should_record() is False


def test_gate_off_ignores_allow_next_frame() -> None:
    """Arming the gate in OFF mode must not flip should_record()."""
    gate = ProfileGate(mode=ProfileMode.OFF)
    gate.allow_next_frame()
    assert gate.should_record() is False


def test_gate_live_always_records_regardless_of_arming() -> None:
    gate = ProfileGate(mode=ProfileMode.LIVE)
    gate.allow_next_frame()  # No-op
    for _ in range(5):
        assert gate.should_record() is True


def test_gate_explicit_starts_disarmed() -> None:
    gate = ProfileGate(mode=ProfileMode.EXPLICIT)
    assert gate.should_record() is False


def test_gate_explicit_one_shot_then_disarmed() -> None:
    gate = ProfileGate(mode=ProfileMode.EXPLICIT)
    gate.allow_next_frame()
    assert gate.should_record() is True
    # Latch consumed -> next call is False until re-arming.
    assert gate.should_record() is False


def test_gate_explicit_re_arm_works() -> None:
    gate = ProfileGate(mode=ProfileMode.EXPLICIT)
    for _ in range(3):
        gate.allow_next_frame()
        assert gate.should_record() is True
        assert gate.should_record() is False


def test_set_mode_clears_pending_one_shot() -> None:
    gate = ProfileGate(mode=ProfileMode.EXPLICIT)
    gate.allow_next_frame()
    # Switching mode clears the latch.
    gate.set_mode(ProfileMode.OFF)
    assert gate.should_record() is False
    gate.set_mode(ProfileMode.EXPLICIT)
    # The previous arm did not survive the mode change.
    assert gate.should_record() is False


def test_set_mode_switches_behavior_inline() -> None:
    gate = ProfileGate(mode=ProfileMode.OFF)
    assert gate.should_record() is False
    gate.set_mode(ProfileMode.LIVE)
    assert gate.should_record() is True
    gate.set_mode(ProfileMode.OFF)
    assert gate.should_record() is False
