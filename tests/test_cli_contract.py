from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import pytest
from cad_sim.manuscript import render_results

ROOT = Path(__file__).resolve().parents[1]


def test_quick_cli_exports_consistent_metadata_and_latex(tmp_path):
    command = subprocess.run([sys.executable, str(ROOT / 'scripts/run_experiment.py'), '--quick', '--output-dir', str(tmp_path)], capture_output=True, text=True)
    assert command.returncode == 0, command.stderr
    metadata = json.loads((tmp_path / 'metadata.json').read_text())
    snapshot = json.loads((tmp_path / 'article_values.json').read_text())
    assert snapshot['metadata'] == metadata
    assert metadata['end_to_end_wall_clock_seconds'] > 0
    assert metadata['config']['n_runs'] == 3
    assert (tmp_path / 'manuscript_results.tex').read_text() == render_results(tmp_path)


def test_updater_rejects_unrelated_result_directory_before_mutating(tmp_path):
    spec = importlib.util.spec_from_file_location('cad_update', ROOT / 'scripts/update_manuscript.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    source = tmp_path / 'V3.tex'
    source.write_text(r'\input{git/results/manuscript_results.tex}')
    unrelated = tmp_path / 'unrelated'; unrelated.mkdir()
    with pytest.raises(ValueError, match='results_dir must match'):
        module.build_manuscript(source, unrelated, source)
    assert not list(unrelated.iterdir())
