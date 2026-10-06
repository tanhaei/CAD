from pathlib import Path
import pytest
from cad_sim.manuscript import audit_manuscript, render_results

ROOT = Path(__file__).resolve().parents[1]


def test_generated_values_match_committed_results() -> None:
    assert (ROOT / "results/manuscript_results.tex").read_text() == render_results(ROOT / "results")


def test_current_manuscript_references_assets_and_has_no_draft_instructions() -> None:
    path = ROOT.parent / "V3.tex"
    if not path.exists():
        pytest.skip("V3 manuscript is a separate artifact; reduced standalone package contains code and results")
    report = audit_manuscript(path)
    assert report["tables"] == 10
    assert report["figures"] == 4
    assert report["all_objects_referenced"]
