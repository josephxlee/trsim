"""``ProfileMode`` enum + parse helper tests (Phase 3 Q4)."""

from __future__ import annotations

import pytest

from workbench.domain.timing import (
    DEFAULT_PROFILE_MODE,
    PROFILE_MODES_IN_DISPLAY_ORDER,
    ProfileMode,
    parse_profile_mode,
)


def test_default_is_off() -> None:
    """Production ``trsim run`` should default to zero probe overhead."""
    assert DEFAULT_PROFILE_MODE is ProfileMode.OFF
    assert DEFAULT_PROFILE_MODE.value == "off"


def test_display_order_increasing_intrusiveness() -> None:
    assert PROFILE_MODES_IN_DISPLAY_ORDER == (
        ProfileMode.OFF,
        ProfileMode.EXPLICIT,
        ProfileMode.LIVE,
    )


def test_string_values_match_plan() -> None:
    """plan/18 § 18.17.5 specifies the TOML strings."""
    assert ProfileMode.OFF.value == "off"
    assert ProfileMode.EXPLICIT.value == "explicit"
    assert ProfileMode.LIVE.value == "live"


def test_parse_profile_mode_round_trip() -> None:
    for mode in PROFILE_MODES_IN_DISPLAY_ORDER:
        assert parse_profile_mode(mode.value) is mode


def test_parse_profile_mode_case_insensitive() -> None:
    assert parse_profile_mode("OFF") is ProfileMode.OFF
    assert parse_profile_mode("Explicit") is ProfileMode.EXPLICIT
    assert parse_profile_mode("LIVE") is ProfileMode.LIVE


def test_parse_profile_mode_strips_whitespace() -> None:
    assert parse_profile_mode(" off ") is ProfileMode.OFF
    assert parse_profile_mode("\tlive\n") is ProfileMode.LIVE


def test_parse_profile_mode_unknown_raises() -> None:
    with pytest.raises(ValueError, match=r"unknown profile mode 'super'"):
        parse_profile_mode("super")


def test_parse_profile_mode_empty_raises() -> None:
    with pytest.raises(ValueError, match=r"unknown profile mode ''"):
        parse_profile_mode("")


def test_profile_mode_str_inherits_value() -> None:
    """ProfileMode is a StrEnum, so members compare equal to their value."""
    assert ProfileMode.OFF == "off"
    assert ProfileMode.LIVE == "live"
