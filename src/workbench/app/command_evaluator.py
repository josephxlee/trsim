"""Command Lineage evaluator (Phase 3 D3, plan/04 § 4.3, v0.14 Level 3-2).

The :class:`CommandBus` (``app/command_bus.py``) records every
dispatched command into an ordered ``_lineage`` list. This module
provides the offline / post-run **evaluator** that walks that list
and reports invariants violations:

- :func:`check_monotonic_sim_time` — ``sim_t_s`` must not decrease
  across the lineage (a TIME_TRAVEL command source would be a bug).
  Bootstrap entries with ``sim_t_s == -1.0`` are skipped.
- :func:`check_tracker_source_provenance` — every ``TRACKER`` source
  command must carry ``source_track_id`` *and* ``source_frame_id``.
  Already enforced at construction time by ``Command.__post_init__``,
  but the evaluator re-checks for replayed lineages loaded from
  disk (where the constructor never ran).
- :func:`check_initial_scan_single_dispatch` — ``INITIAL_SCAN``
  source must dispatch exactly once at Target-Run start (per
  ``CommandSource`` doc in ``domain/types.py``). Multiple
  INITIAL_SCAN commands indicate a Run-restart-without-clear bug.

Aggregate API:

- :class:`LineageIssue` — single violation (rule_name + index +
  message).
- :class:`LineageReport.is_valid` — Run-replay UI gates on this.
- :func:`evaluate_command_lineage(commands)` — runs every check
  and bundles the results.

The evaluator is intentionally pure (no event_bus / command_bus
coupling) so it slots into any controller / CLI / replay tool.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from workbench.app.command_bus import Command
from workbench.domain.types import CommandSource


@dataclass(frozen=True, slots=True)
class LineageIssue:
    """One Lineage Level 3-2 violation.

    Attributes:
        rule_name: Short tag identifying the rule
            (``"monotonic_sim_time"`` etc.).
        command_index: Position of the offending command in the
            input sequence.
        message: One-line diagnostic.
    """

    rule_name: str
    command_index: int
    message: str


@dataclass(frozen=True, slots=True)
class LineageReport:
    """Aggregate of every :class:`LineageIssue` found.

    Attributes:
        issues: Tuple of issues in command-order. Empty = valid lineage.
        n_commands: Total commands evaluated (lets the UI display
            ``"42 commands, 0 issues"`` style summaries).
    """

    issues: tuple[LineageIssue, ...]
    n_commands: int

    @property
    def is_valid(self) -> bool:
        """``True`` if every check passed."""
        return not self.issues


def evaluate_command_lineage(commands: Sequence[Command]) -> LineageReport:
    """Run every Lineage Level 3-2 invariant against ``commands``.

    Args:
        commands: Ordered sequence of :class:`Command` instances —
            typically ``CommandBus.lineage()`` or a replay-loaded list.

    Returns:
        :class:`LineageReport` carrying every violation found.
    """
    issues: list[LineageIssue] = []
    issues.extend(check_monotonic_sim_time(commands))
    issues.extend(check_tracker_source_provenance(commands))
    issues.extend(check_initial_scan_single_dispatch(commands))
    return LineageReport(issues=tuple(issues), n_commands=len(commands))


# ---------------------------------------------------------------------
# Individual rules
# ---------------------------------------------------------------------


def check_monotonic_sim_time(commands: Sequence[Command]) -> tuple[LineageIssue, ...]:
    """``sim_t_s`` must not decrease across the lineage.

    Bootstrap commands with ``sim_t_s == -1.0`` (dispatched before
    the SimulationClock starts) are skipped — they're allowed at the
    start of the lineage as long as they're contiguous.
    """
    issues: list[LineageIssue] = []
    last_t = -1.0  # sentinel: skipped during the bootstrap prefix
    for i, cmd in enumerate(commands):
        if cmd.sim_t_s < 0:
            continue
        if cmd.sim_t_s < last_t:
            issues.append(
                LineageIssue(
                    rule_name="monotonic_sim_time",
                    command_index=i,
                    message=(
                        f"command {cmd.name!r} sim_t_s={cmd.sim_t_s} < "
                        f"previous {last_t} (time travel)"
                    ),
                )
            )
        else:
            last_t = cmd.sim_t_s
    return tuple(issues)


def check_tracker_source_provenance(
    commands: Sequence[Command],
) -> tuple[LineageIssue, ...]:
    """Every ``TRACKER`` source command must carry both ids.

    Catches replay-loaded lineages where the constructor's
    ``__post_init__`` never ran (e.g. JSON load reconstructed via
    ``object.__new__``).
    """
    issues: list[LineageIssue] = []
    for i, cmd in enumerate(commands):
        if cmd.source is not CommandSource.TRACKER:
            continue
        if cmd.source_track_id is None or cmd.source_frame_id is None:
            issues.append(
                LineageIssue(
                    rule_name="tracker_source_provenance",
                    command_index=i,
                    message=(
                        f"TRACKER command {cmd.name!r} missing source_track_id / source_frame_id"
                    ),
                )
            )
    return tuple(issues)


def check_initial_scan_single_dispatch(
    commands: Sequence[Command],
) -> tuple[LineageIssue, ...]:
    """``INITIAL_SCAN`` source must dispatch at most once.

    ``CommandSource`` docs say "exactly once at Target Run start";
    every additional occurrence is flagged at the offending index.
    Zero occurrences is allowed (the Run-start scan may have been
    suppressed by configuration).
    """
    issues: list[LineageIssue] = []
    seen = 0
    for i, cmd in enumerate(commands):
        if cmd.source is not CommandSource.INITIAL_SCAN:
            continue
        seen += 1
        if seen > 1:
            issues.append(
                LineageIssue(
                    rule_name="initial_scan_single_dispatch",
                    command_index=i,
                    message=(
                        f"INITIAL_SCAN command {cmd.name!r} dispatched "
                        f"{seen} times (expected at most 1)"
                    ),
                )
            )
    return tuple(issues)
