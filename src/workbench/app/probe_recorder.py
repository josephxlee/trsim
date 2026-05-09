"""ProbeRecorder — Stage I/O probe to CSV (plan/04 § 4.3, v0.14).

Phase 3.2 — minimum-viable probe that records ``(sim_t_s, **payload)``
rows into an in-memory buffer, then exports CSV. Real-time probes
(the Stage I/O Panel in Phase 4) attach via :meth:`record`; the CLI
also uses it to dump tracker / detector outputs at run end.

CSV header is the union of every key seen across rows; cells missing
in a given row are left empty. Order: ``sim_t_s`` first, then keys
in first-seen order.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ProbeRow:
    """One recorded sample (sim_t_s + arbitrary payload keys)."""

    sim_t_s: float
    payload: dict[str, object]


@dataclass(slots=True)
class ProbeRecorder:
    """In-memory probe buffer with CSV export."""

    _rows: list[ProbeRow] = field(default_factory=list)

    def record(self, sim_t_s: float, payload: dict[str, object]) -> None:
        """Append one row.

        Args:
            sim_t_s: Sample time [s]. Must be >= 0.
            payload: Arbitrary scalar payload (``str(value)`` is used at
                CSV time, so any type that round-trips through str() works).

        Raises:
            ValueError: If ``sim_t_s < 0``.
        """
        if sim_t_s < 0.0:
            msg = f"sim_t_s must be >= 0, got {sim_t_s}"
            raise ValueError(msg)
        self._rows.append(ProbeRow(sim_t_s=sim_t_s, payload=dict(payload)))

    def __len__(self) -> int:
        return len(self._rows)

    @property
    def rows(self) -> tuple[ProbeRow, ...]:
        """Snapshot of recorded rows."""
        return tuple(self._rows)

    def clear(self) -> None:
        """Drop every recorded row."""
        self._rows.clear()

    # --- CSV export ----------------------------------------------------

    def to_csv_string(self) -> str:
        """Render the buffer as a CSV string.

        Header: ``sim_t_s`` first, then every payload key in
        first-seen order. Returns an empty string if no rows recorded.
        """
        if not self._rows:
            return ""
        # Build header: sim_t_s first, then keys in first-seen order.
        seen: dict[str, None] = {}
        for r in self._rows:
            for k in r.payload:
                seen.setdefault(k, None)
        header = ["sim_t_s", *seen.keys()]

        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(header)
        for r in self._rows:
            row_cells = [f"{r.sim_t_s:.9f}"]
            for k in seen:
                v = r.payload.get(k, "")
                row_cells.append(str(v))
            writer.writerow(row_cells)
        return buf.getvalue()

    def write_csv(self, path: Path | str) -> int:
        """Write the buffer to ``path`` as CSV. Returns row count."""
        text = self.to_csv_string()
        Path(path).write_text(text, encoding="utf-8")
        return len(self._rows)
