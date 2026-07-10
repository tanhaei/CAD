from __future__ import annotations

from pathlib import Path


def test_simulation_manuscript_has_no_live_author_inputs() -> None:
    path = Path(__file__).resolve().parents[1] / "manuscript" / "V1_simulated.tex"
    text = path.read_text(encoding="utf-8")
    assert "\\AuthorInput{" not in text
    assert "Simulation-only working version" in text
    assert "https://github.com/tanhaei/CAD" in text


def test_manuscript_assets_exist() -> None:
    root = Path(__file__).resolve().parents[1] / "manuscript"
    for filename in (
        "fig01_bioarc_overview.pdf",
        "fig02_cad_pipeline.pdf",
        "bioarc_service_external.pdf",
        "bioarc_observability_sync.pdf",
        "references.bib",
    ):
        assert (root / filename).exists(), filename
