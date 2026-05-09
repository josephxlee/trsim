"""FrameProfiler — accumulate stage timing samples + compute percentiles.

Phase 3.6 — sink that pairs with :class:`StageTimingProbe`. Holds
per-stage sample lists and produces avg / p50 / p95 / p99 reports.

Warmup (plan/18 § 18.17 Q-RT7): the first ``warmup_samples`` per
stage are discarded from percentile computation — JIT / cache-warm
artefacts otherwise inflate the worst-case tail.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

DEFAULT_WARMUP_SAMPLES: int = 10
"""Plan/18 § 18.17 Q-RT7 recommendation."""


@dataclass(frozen=True, slots=True)
class StageReport:
    """Per-stage timing summary (one entry per stage_name).

    Attributes:
        stage_name: Stage identifier.
        n_samples: Total samples recorded (including warmup).
        n_post_warmup: Samples used in percentile computation.
        avg_ms: Mean post-warmup duration in milliseconds.
        p50_ms: Median post-warmup duration.
        p95_ms: 95th percentile.
        p99_ms: 99th percentile.
    """

    stage_name: str
    n_samples: int
    n_post_warmup: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


@dataclass(slots=True)
class FrameProfiler:
    """Accumulator for :class:`StageTimingProbe` samples.

    Attributes:
        warmup_samples: Number of leading samples to ignore per stage
            when computing percentiles. Default
            :data:`DEFAULT_WARMUP_SAMPLES` (10).
    """

    warmup_samples: int = DEFAULT_WARMUP_SAMPLES
    _samples: dict[str, list[int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.warmup_samples < 0:
            msg = f"warmup_samples must be >= 0, got {self.warmup_samples}"
            raise ValueError(msg)

    def record_sample(self, stage_name: str, elapsed_ns: int) -> None:
        """Append one duration sample to ``stage_name``'s list.

        Args:
            stage_name: Stage identifier.
            elapsed_ns: Duration in nanoseconds. Must be >= 0.

        Raises:
            ValueError: If ``stage_name`` is empty or ``elapsed_ns < 0``.
        """
        if not stage_name:
            msg = "stage_name must be a non-empty string"
            raise ValueError(msg)
        if elapsed_ns < 0:
            msg = f"elapsed_ns must be >= 0, got {elapsed_ns}"
            raise ValueError(msg)
        self._samples.setdefault(stage_name, []).append(int(elapsed_ns))

    def stages(self) -> tuple[str, ...]:
        """Stage names recorded so far, alphabetically sorted."""
        return tuple(sorted(self._samples.keys()))

    def report(self, stage_name: str) -> StageReport:
        """Build a :class:`StageReport` for one stage.

        Raises:
            KeyError: If ``stage_name`` has no samples.
        """
        try:
            samples = list(self._samples[stage_name])
        except KeyError as exc:
            msg = f"no samples recorded for stage {stage_name!r}"
            raise KeyError(msg) from exc
        n_total = len(samples)
        post = samples[self.warmup_samples :] if n_total > self.warmup_samples else []
        n_post = len(post)
        if n_post == 0:
            return StageReport(
                stage_name=stage_name,
                n_samples=n_total,
                n_post_warmup=0,
                avg_ms=float("nan"),
                p50_ms=float("nan"),
                p95_ms=float("nan"),
                p99_ms=float("nan"),
            )
        sorted_post = sorted(post)
        return StageReport(
            stage_name=stage_name,
            n_samples=n_total,
            n_post_warmup=n_post,
            avg_ms=_ns_mean_to_ms(post),
            p50_ms=_percentile_ms(sorted_post, 50.0),
            p95_ms=_percentile_ms(sorted_post, 95.0),
            p99_ms=_percentile_ms(sorted_post, 99.0),
        )

    def report_all(self) -> tuple[StageReport, ...]:
        """Reports for every recorded stage, alphabetical."""
        return tuple(self.report(name) for name in self.stages())

    def reset(self) -> None:
        """Drop every recorded sample (typically between runs)."""
        self._samples.clear()


def _ns_mean_to_ms(samples: list[int]) -> float:
    return (sum(samples) / len(samples)) / 1e6


def _percentile_ms(sorted_ns: list[int], pct: float) -> float:
    """Linear-interpolation percentile in ``[min, max]`` (NumPy style).

    ``sorted_ns`` MUST be sorted ascending. ``pct`` in [0, 100].
    """
    if not sorted_ns:
        return float("nan")
    if len(sorted_ns) == 1:
        return sorted_ns[0] / 1e6
    rank = (pct / 100.0) * (len(sorted_ns) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_ns[lower] / 1e6
    weight = rank - lower
    interp_ns = sorted_ns[lower] * (1.0 - weight) + sorted_ns[upper] * weight
    return interp_ns / 1e6
