"""Unit tests for app.timing.frame_boundary_detector (Phase 5.12)."""

from __future__ import annotations

from workbench.app.timing.frame_boundary_detector import FrameBoundaryDetector


def test_default_frame_id_is_zero() -> None:
    fbd = FrameBoundaryDetector()
    assert fbd.frame_id == 0


def test_on_track_output_increments_counter() -> None:
    fbd = FrameBoundaryDetector()
    assert fbd.on_track_output() is True
    assert fbd.frame_id == 1
    fbd.on_track_output()
    fbd.on_track_output()
    assert fbd.frame_id == 3


def test_reset_returns_to_zero() -> None:
    fbd = FrameBoundaryDetector()
    for _ in range(5):
        fbd.on_track_output()
    assert fbd.frame_id == 5
    fbd.reset()
    assert fbd.frame_id == 0


def test_reset_then_increment_starts_fresh() -> None:
    fbd = FrameBoundaryDetector()
    for _ in range(10):
        fbd.on_track_output()
    fbd.reset()
    fbd.on_track_output()
    assert fbd.frame_id == 1


def test_explicit_initial_frame_id() -> None:
    """Constructor honours the frame_id keyword (post-Run resume)."""
    fbd = FrameBoundaryDetector(frame_id=42)
    assert fbd.frame_id == 42
    fbd.on_track_output()
    assert fbd.frame_id == 43


def test_every_call_returns_true_at_mvp() -> None:
    """Multi-target / batched output cases are MVP+alpha."""
    fbd = FrameBoundaryDetector()
    results = [fbd.on_track_output() for _ in range(20)]
    assert all(results)


# ---------- 5.12b — monotonicity + reset semantics ----------


def test_frame_id_monotonically_strictly_increases() -> None:
    """Each ``on_track_output()`` adds exactly 1; the sequence
    0, 1, 2, ... 9 must be strictly increasing.
    """
    fbd = FrameBoundaryDetector()
    sequence: list[int] = [fbd.frame_id]
    for _ in range(10):
        fbd.on_track_output()
        sequence.append(fbd.frame_id)
    assert sequence == list(range(11))


def test_reset_is_idempotent() -> None:
    """Two consecutive reset() calls are safe and leave frame_id at 0."""
    fbd = FrameBoundaryDetector()
    for _ in range(3):
        fbd.on_track_output()
    fbd.reset()
    fbd.reset()
    assert fbd.frame_id == 0


def test_reset_drops_back_to_zero_even_after_explicit_initial_id() -> None:
    """Reset always returns to 0 regardless of the explicit initial
    id supplied at construction time. Pins the "post-Run boundary"
    semantics (next Run starts at frame 0, not the previous frame_id).
    """
    fbd = FrameBoundaryDetector(frame_id=100)
    fbd.on_track_output()
    fbd.on_track_output()
    assert fbd.frame_id == 102
    fbd.reset()
    assert fbd.frame_id == 0


def test_increment_after_explicit_initial_id_is_linear() -> None:
    """Explicit initial id of 42 + N calls -> 42 + N. Generalises the
    existing single-step test.
    """
    fbd = FrameBoundaryDetector(frame_id=42)
    for _ in range(7):
        fbd.on_track_output()
    assert fbd.frame_id == 49
