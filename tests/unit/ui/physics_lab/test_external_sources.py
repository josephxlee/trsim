"""LibraryWidget Measured Data + Papers integration (PL-9.2a/b)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")
pytest.importorskip("h5py")

import h5py

from workbench.domain.physics_lab import (
    MeasuredDataset,
    PaperReference,
)
from workbench.ui.physics_lab import LibraryWidget, PhysicsLabWorkspace

pytestmark = pytest.mark.qt


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def _write_pdf(path: Path) -> None:
    path.write_bytes(b"%PDF-1.4\n%%EOF\n")


# ---------------------------------------------------------------------
# LibraryWidget — set_measured_datasets + set_papers
# ---------------------------------------------------------------------


def test_set_measured_datasets_populates_category(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    datasets = (
        MeasuredDataset(
            dataset_id="b737",
            file_path=tmp_path / "b737.csv",
            file_format="csv",
            columns=("angle", "rcs"),
            n_rows=361,
        ),
    )
    lib.set_measured_datasets(datasets)
    assert lib.measured_category().childCount() == 1
    label = lib.measured_category().child(0).text(0)
    assert lib.measured_for(label) == datasets[0]


def test_set_measured_datasets_replaces_previous(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    a = MeasuredDataset(
        dataset_id="a", file_path=tmp_path / "a.csv", file_format="csv", columns=("x",)
    )
    b = MeasuredDataset(
        dataset_id="b", file_path=tmp_path / "b.csv", file_format="csv", columns=("x",)
    )
    lib.set_measured_datasets((a,))
    lib.set_measured_datasets((b,))
    assert lib.measured_category().childCount() == 1
    only_child = lib.measured_category().child(0).text(0)
    assert lib.measured_for(only_child) == b


def test_set_papers_populates_category(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    papers = (
        PaperReference(
            paper_id="ITU-R-P838",
            file_path=tmp_path / "p838.pdf",
            title="Rain attenuation",
        ),
    )
    lib.set_papers(papers)
    assert lib.papers_category().childCount() == 1
    label = lib.papers_category().child(0).text(0)
    assert "ITU-R-P838" in label
    assert "Rain attenuation" in label
    assert lib.paper_for(label) == papers[0]


def test_select_measured_emits_signal(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    dataset = MeasuredDataset(
        dataset_id="x", file_path=tmp_path / "x.csv", file_format="csv", columns=("a",)
    )
    lib.set_measured_datasets((dataset,))
    received: list[MeasuredDataset] = []
    lib.measured_dataset_selected.connect(received.append)
    label = lib.measured_category().child(0).text(0)
    lib.select_label(label)
    assert received == [dataset]


def test_select_paper_emits_signal(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    paper = PaperReference(paper_id="x", file_path=tmp_path / "x.pdf")
    lib.set_papers((paper,))
    received: list[PaperReference] = []
    lib.paper_selected.connect(received.append)
    label = lib.papers_category().child(0).text(0)
    lib.select_label(label)
    assert received == [paper]


def test_leaf_labels_spans_all_five_categories(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    lib.set_measured_datasets(
        (
            MeasuredDataset(
                dataset_id="ds",
                file_path=tmp_path / "x.csv",
                file_format="csv",
                columns=("a",),
            ),
        )
    )
    lib.set_papers((PaperReference(paper_id="pap", file_path=tmp_path / "x.pdf"),))
    labels = lib.leaf_labels()
    # Bouncing Ball + 9 Test Objects + 2 Models + 1 measured + 1 paper = 14.
    assert len(labels) == 14


# ---------------------------------------------------------------------
# Workspace integration — measured_root + papers_root
# ---------------------------------------------------------------------


def test_workspace_construction_loads_measured_from_root(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    measured = tmp_path / "measured"
    measured.mkdir()
    _write_csv(measured / "foo.csv", "a,b", ["1,2"])
    ws = PhysicsLabWorkspace(
        enable_3d_viewer=False,
        measured_root=measured,
    )
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.library_panel().measured_category().childCount() == 1


def test_workspace_construction_loads_papers_from_root(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    papers = tmp_path / "papers"
    papers.mkdir()
    _write_pdf(papers / "p838.pdf")
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, papers_root=papers)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.library_panel().papers_category().childCount() == 1


def test_workspace_refresh_measured_picks_up_new_file(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    measured = tmp_path / "measured"
    measured.mkdir()
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.library_panel().measured_category().childCount() == 0
    _write_csv(measured / "new.csv", "a,b", ["1,2"])
    ws.refresh_measured_datasets()
    assert ws.library_panel().measured_category().childCount() == 1


def test_workspace_refresh_papers_picks_up_new_file(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    papers = tmp_path / "papers"
    papers.mkdir()
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, papers_root=papers)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.library_panel().papers_category().childCount() == 0
    _write_pdf(papers / "new.pdf")
    ws.refresh_papers()
    assert ws.library_panel().papers_category().childCount() == 1


def test_workspace_hdf5_dataset_loads(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    measured = tmp_path / "measured"
    measured.mkdir()
    with h5py.File(measured / "rcs.h5", "w") as f:
        f.create_dataset("angle", data=np.array([0.0, 1.0, 2.0]))
        f.create_dataset("rcs", data=np.array([10.0, 20.0, 30.0]))
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, measured_root=measured)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    cat = ws.library_panel().measured_category()
    assert cat.childCount() == 1
    label = cat.child(0).text(0)
    assert "(hdf5)" in label
    dataset = ws.library_panel().measured_for(label)
    assert dataset is not None
    assert dataset.file_format == "hdf5"
    assert set(dataset.columns) == {"angle", "rcs"}
