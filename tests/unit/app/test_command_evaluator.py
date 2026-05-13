"""Unit tests for app.command_evaluator (Phase 3 D3, v0.14 Level 3-2)."""

from __future__ import annotations

import pytest

from workbench.app.command_bus import Command
from workbench.app.command_evaluator import (
    LineageIssue,
    LineageReport,
    check_initial_scan_single_dispatch,
    check_monotonic_sim_time,
    check_tracker_source_provenance,
    evaluate_command_lineage,
)
from workbench.domain.types import CommandSource


def _ui_cmd(name: str, sim_t_s: float) -> Command:
    """Build a MANUAL_USER-sourced command at ``sim_t_s``."""
    return Command(name=name, source=CommandSource.MANUAL_USER, sim_t_s=sim_t_s)


def _tracker_cmd(name: str, *, sim_t_s: float, track_id: int = 1, frame_id: int = 1) -> Command:
    return Command(
        name=name,
        source=CommandSource.TRACKER,
        sim_t_s=sim_t_s,
        source_track_id=track_id,
        source_frame_id=frame_id,
    )


def _initial_scan_cmd(name: str = "positioner.scan") -> Command:
    return Command(name=name, source=CommandSource.INITIAL_SCAN, sim_t_s=0.0)


# ---------------------------------------------------------------------
# check_monotonic_sim_time
# ---------------------------------------------------------------------


def test_monotonic_sim_time_passes_for_increasing_lineage() -> None:
    seq = [_ui_cmd("a", 0.1), _ui_cmd("b", 0.2), _ui_cmd("c", 0.5)]
    assert check_monotonic_sim_time(seq) == ()


def test_monotonic_sim_time_skips_bootstrap_prefix() -> None:
    """``sim_t_s == -1.0`` (CLI bootstrap) is allowed at the front."""
    seq = [
        _ui_cmd("boot", -1.0),
        _ui_cmd("boot2", -1.0),
        _ui_cmd("first", 0.1),
        _ui_cmd("second", 0.2),
    ]
    assert check_monotonic_sim_time(seq) == ()


def test_monotonic_sim_time_flags_time_travel() -> None:
    seq = [
        _ui_cmd("a", 0.1),
        _ui_cmd("b", 0.5),
        _ui_cmd("c", 0.2),  # time travel
    ]
    issues = check_monotonic_sim_time(seq)
    assert len(issues) == 1
    assert issues[0].command_index == 2
    assert issues[0].rule_name == "monotonic_sim_time"


# ---------------------------------------------------------------------
# check_tracker_source_provenance
# ---------------------------------------------------------------------


def test_tracker_source_provenance_passes_for_valid_command() -> None:
    """Valid TRACKER command (both ids set) -> no issues."""
    issues = check_tracker_source_provenance([_tracker_cmd("x", sim_t_s=0.5)])
    assert issues == ()


def test_tracker_source_provenance_ignores_non_tracker_sources() -> None:
    """MANUAL_USER + INITIAL_SCAN commands never trigger this rule."""
    seq = [_ui_cmd("ui", 0.1), _initial_scan_cmd("init")]
    assert check_tracker_source_provenance(seq) == ()


def test_tracker_source_provenance_flags_missing_ids() -> None:
    """A TRACKER command with missing ids (constructed via direct
    field assignment to bypass ``__post_init__``) must surface as
    an issue.
    """
    # `Command.__post_init__` rejects this at construction time, so
    # we use `object.__new__` to simulate a replay-loaded malformed
    # command.
    cmd = object.__new__(Command)
    object.__setattr__(cmd, "name", "tracker.cmd")
    object.__setattr__(cmd, "source", CommandSource.TRACKER)
    object.__setattr__(cmd, "args", {})
    object.__setattr__(cmd, "sim_t_s", 0.1)
    object.__setattr__(cmd, "wall_ns", 0)
    object.__setattr__(cmd, "source_track_id", None)
    object.__setattr__(cmd, "source_frame_id", None)

    issues = check_tracker_source_provenance([cmd])
    assert len(issues) == 1
    assert issues[0].rule_name == "tracker_source_provenance"


# ---------------------------------------------------------------------
# check_initial_scan_single_dispatch
# ---------------------------------------------------------------------


def test_initial_scan_single_dispatch_passes_for_zero_or_one() -> None:
    """0 or 1 INITIAL_SCAN -> no issues."""
    assert check_initial_scan_single_dispatch([_ui_cmd("ui", 0.0)]) == ()
    assert check_initial_scan_single_dispatch([_initial_scan_cmd()]) == ()


def test_initial_scan_single_dispatch_flags_second_occurrence() -> None:
    """Second INITIAL_SCAN command -> one issue at that index."""
    seq = [
        _initial_scan_cmd("scan1"),
        _ui_cmd("between", 0.5),
        _initial_scan_cmd("scan2"),
    ]
    issues = check_initial_scan_single_dispatch(seq)
    assert len(issues) == 1
    assert issues[0].command_index == 2
    assert issues[0].rule_name == "initial_scan_single_dispatch"


def test_initial_scan_single_dispatch_flags_every_extra_occurrence() -> None:
    """3 INITIAL_SCAN commands -> 2 issues (the second + the third)."""
    seq = [
        _initial_scan_cmd("a"),
        _initial_scan_cmd("b"),
        _initial_scan_cmd("c"),
    ]
    issues = check_initial_scan_single_dispatch(seq)
    assert len(issues) == 2


# ---------------------------------------------------------------------
# evaluate_command_lineage
# ---------------------------------------------------------------------


def test_evaluate_returns_valid_report_on_clean_lineage() -> None:
    seq = [
        _initial_scan_cmd(),
        _ui_cmd("ui", 0.1),
        _tracker_cmd("track", sim_t_s=0.2),
        _ui_cmd("ui_late", 0.5),
    ]
    report = evaluate_command_lineage(seq)
    assert isinstance(report, LineageReport)
    assert report.is_valid
    assert report.issues == ()
    assert report.n_commands == 4


def test_evaluate_collects_multiple_issues() -> None:
    """Time-travel + duplicate INITIAL_SCAN -> 2 issues."""
    seq = [
        _initial_scan_cmd("scan1"),
        _ui_cmd("a", 0.5),
        _ui_cmd("b", 0.2),  # time travel
        _initial_scan_cmd("scan2"),  # second initial scan
    ]
    report = evaluate_command_lineage(seq)
    assert not report.is_valid
    assert report.n_commands == 4
    rules = {issue.rule_name for issue in report.issues}
    assert rules == {"monotonic_sim_time", "initial_scan_single_dispatch"}


# ---------------------------------------------------------------------
# LineageReport / LineageIssue
# ---------------------------------------------------------------------


def test_lineage_report_is_valid_property() -> None:
    assert LineageReport(issues=(), n_commands=0).is_valid is True
    issue = LineageIssue(rule_name="x", command_index=0, message="y")
    assert LineageReport(issues=(issue,), n_commands=1).is_valid is False


def test_evaluate_empty_lineage_returns_valid_report() -> None:
    report = evaluate_command_lineage([])
    assert report.is_valid
    assert report.n_commands == 0


@pytest.mark.parametrize("name", ["", " "])
def test_lineage_issue_accepts_arbitrary_strings(name: str) -> None:
    """LineageIssue itself doesn't validate field contents — it's a
    pure container. Field validation belongs to the rules.
    """
    issue = LineageIssue(rule_name=name, command_index=0, message="m")
    assert issue.rule_name == name
