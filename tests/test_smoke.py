from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from cad_sim.config import ExperimentConfig
from cad_sim.experiment import run_experiment, write_results


def test_quick_experiment_smoke(tmp_path: Path) -> None:
    config = replace(
        ExperimentConfig(),
        n_runs=3,
        n_activity_records=20_000,
        bootstrap_resamples=500,
    )
    results = run_experiment(config)

    assert len(results.method_summary) == 4
    assert len(results.ablation_summary) == 5
    assert len(results.sensitivity_summary) == 5
    assert len(results.runtime_summary) == 4
    assert results.method_summary["p_at_10"].between(0, 1).all()
    assert results.method_summary["r_at_10"].between(0, 1).all()
    assert results.method_summary["map"].between(0, 1).all()

    result_dir = tmp_path / "results"
    write_results(results, result_dir)

    expected_results = {
        "method_summary.csv",
        "run_metrics.csv",
        "ablation_summary.csv",
        "sensitivity_summary.csv",
        "runtime_summary.csv",
        "metadata.json",
        "component_ground_truth.csv",
        "defect_ground_truth.csv",
        "pathway_summary.csv",
        "run_pathway_summary.csv",
        "run_trace_coverage.csv",
    }
    assert expected_results.issubset({path.name for path in result_dir.iterdir()})

    defects = pd.read_csv(result_dir / "defect_ground_truth.csv")
    assert len(defects) == config.n_injected_defects
    assert set(defects["component_id"]) == set(config.relevant_component_ids)

    pathways = pd.read_csv(result_dir / "run_pathway_summary.csv")
    counts_by_seed = pathways.groupby("seed")["activity_count"].sum()
    assert (counts_by_seed == config.n_activity_records).all()


def test_full_reproducibility_for_core_metrics() -> None:
    config = replace(
        ExperimentConfig(),
        n_runs=4,
        n_activity_records=30_000,
        bootstrap_resamples=500,
    )
    first = run_experiment(config).method_summary.drop(
        columns=["cliffs_delta_label"]
    )
    second = run_experiment(config).method_summary.drop(
        columns=["cliffs_delta_label"]
    )
    pd.testing.assert_frame_equal(first, second)
