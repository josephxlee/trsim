"""Paper references (PL-9.2b, plan/19 § 19.9.2).

The Physics Lab Library's "Papers" category points at PDF files in a
known root (typically ``~/.trsim/physics_lab/papers/``). The domain
layer holds the metadata (title / authors / year); the UI hands the
file off to the system's default PDF viewer when the user double-
clicks. PL-9.2b explicitly **excludes** automatic PDF -> code
generation (plan/19 § 19.9.2 form 3, current-tech limitation).

A small companion TOML sidecar (``<file>.toml``) carries human-
readable metadata. PDFs without a sidecar still appear in the Library
with their filename as the only label.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PaperReference:
    """One PDF reference the Library can offer.

    Attributes:
        paper_id: Library label. Defaults to the file stem.
        file_path: Absolute path to the PDF.
        title: Citation title.
        authors: Free-form author list.
        year: Publication year (``-1`` if unknown).
        description: Free-form notes.
        license: License / redistribution status.

    Raises:
        ValueError: Empty paper_id or non-PDF extension.
    """

    paper_id: str
    file_path: Path
    title: str = ""
    authors: str = ""
    year: int = -1
    description: str = ""
    license: str = ""

    def __post_init__(self) -> None:
        if not self.paper_id:
            msg = "PaperReference.paper_id must be non-empty"
            raise ValueError(msg)
        if self.file_path.suffix.lower() != ".pdf":
            msg = f"PaperReference.file_path must be a .pdf file, got {self.file_path.name!r}"
            raise ValueError(msg)


def _read_sidecar_metadata(pdf_path: Path) -> dict[str, object]:
    sidecar = pdf_path.with_suffix(".pdf.toml")
    if not sidecar.is_file():
        return {}
    raw = sidecar.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}


def inspect_pdf(
    path: Path | str,
    *,
    paper_id: str | None = None,
) -> PaperReference:
    """Build a :class:`PaperReference` from a PDF path + sidecar TOML."""
    p = Path(path)
    meta = _read_sidecar_metadata(p)
    year_raw = meta.get("year", -1)
    year = year_raw if isinstance(year_raw, int) else -1
    return PaperReference(
        paper_id=paper_id or str(meta.get("paper_id", p.stem)),
        file_path=p,
        title=str(meta.get("title", "")),
        authors=str(meta.get("authors", "")),
        year=year,
        description=str(meta.get("description", "")),
        license=str(meta.get("license", "")),
    )


def list_papers(root: Path | str) -> tuple[PaperReference, ...]:
    """Scan ``root`` for ``*.pdf`` files and return sorted references."""
    root_path = Path(root)
    if not root_path.is_dir():
        return ()
    out: list[PaperReference] = []
    for pdf_path in sorted(root_path.glob("*.pdf")):
        try:
            out.append(inspect_pdf(pdf_path))
        except (OSError, ValueError):
            continue
    return tuple(sorted(out, key=lambda p: p.paper_id))
