"""PaperReference domain tests (PL-9.2b, plan/19 § 19.9.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.domain.physics_lab import (
    PaperReference,
    inspect_pdf,
    list_papers,
)


def _make_pdf(path: Path, content: bytes = b"%PDF-1.4\n%%EOF\n") -> None:
    """Write a placeholder PDF — only the extension matters for the
    metadata path; the loader never parses PDF content.
    """
    path.write_bytes(content)


# ---------------------------------------------------------------------
# Dataclass validation
# ---------------------------------------------------------------------


def test_dataclass_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match=r"paper_id must be non-empty"):
        PaperReference(paper_id="", file_path=Path("x.pdf"))


def test_dataclass_rejects_non_pdf_extension() -> None:
    with pytest.raises(ValueError, match=r"must be a \.pdf file"):
        PaperReference(paper_id="x", file_path=Path("doc.docx"))


def test_dataclass_accepts_uppercase_extension() -> None:
    PaperReference(paper_id="x", file_path=Path("doc.PDF"))


# ---------------------------------------------------------------------
# inspect_pdf
# ---------------------------------------------------------------------


def test_inspect_pdf_default_id_is_file_stem(tmp_path: Path) -> None:
    path = tmp_path / "p838.pdf"
    _make_pdf(path)
    ref = inspect_pdf(path)
    assert ref.paper_id == "p838"
    assert ref.title == ""


def test_inspect_pdf_overrides_paper_id(tmp_path: Path) -> None:
    path = tmp_path / "p838.pdf"
    _make_pdf(path)
    ref = inspect_pdf(path, paper_id="ITU-R-P838")
    assert ref.paper_id == "ITU-R-P838"


def test_inspect_pdf_reads_sidecar_metadata(tmp_path: Path) -> None:
    path = tmp_path / "p838.pdf"
    _make_pdf(path)
    sidecar = tmp_path / "p838.pdf.toml"
    sidecar.write_text(
        'paper_id = "ITU-R-P838"\n'
        'title = "Rain attenuation"\n'
        'authors = "ITU-R"\n'
        "year = 2005\n"
        'description = "Reference for rain model"\n'
        'license = "ITU public"\n',
        encoding="utf-8",
    )
    ref = inspect_pdf(path)
    assert ref.paper_id == "ITU-R-P838"
    assert ref.title == "Rain attenuation"
    assert ref.year == 2005


# ---------------------------------------------------------------------
# list_papers
# ---------------------------------------------------------------------


def test_list_returns_empty_when_root_missing(tmp_path: Path) -> None:
    assert list_papers(tmp_path / "no-such") == ()


def test_list_returns_sorted_papers(tmp_path: Path) -> None:
    for stem in ("zulu", "alpha", "bravo"):
        _make_pdf(tmp_path / f"{stem}.pdf")
    papers = list_papers(tmp_path)
    assert [p.paper_id for p in papers] == ["alpha", "bravo", "zulu"]


def test_list_skips_non_pdf_files(tmp_path: Path) -> None:
    _make_pdf(tmp_path / "doc.pdf")
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    papers = list_papers(tmp_path)
    assert [p.paper_id for p in papers] == ["doc"]
