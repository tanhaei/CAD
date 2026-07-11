from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from cad_sim.config import ExperimentConfig


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def test_committed_results_match_default_run_shape() -> None:
    config = ExperimentConfig()
    metrics = pd.read_csv(RESULTS / "run_metrics.csv")
    assert len(metrics) == config.n_runs * 4
    assert set(metrics["seed"]) == set(config.seeds)
    assert metrics.groupby("method").size().eq(config.n_runs).all()

    metadata = json.loads((RESULTS / "metadata.json").read_text(encoding="utf-8"))
    expected_config = json.loads(json.dumps(config.to_dict()))
    assert metadata["config"] == expected_config
    assert metadata["end_to_end_wall_clock_seconds"] >= metadata[
        "analysis_wall_clock_seconds"
    ]
    for forbidden in (
        "score_noise",
        "top_decoy_probability",
        "tail_degradation_probability",
    ):
        assert forbidden not in metadata["config"]


def test_committed_ground_truth_follows_injection_protocol() -> None:
    config = ExperimentConfig()
    components = pd.read_csv(RESULTS / "component_ground_truth.csv")
    defects = pd.read_csv(RESULTS / "defect_ground_truth.csv")

    relevant = components.loc[components["relevant"] == 1, "component_id"]
    assert set(relevant) == set(config.relevant_component_ids)
    assert len(defects) == config.n_injected_defects
    assert defects["defect_id"].is_unique
    assert set(defects["component_id"]) == set(config.relevant_component_ids)
    assert {
        "category",
        "affected_pathway_id",
        "criticality_band",
        "related_test_id",
    }.issubset(defects.columns)


def test_static_baseline_interval_is_degenerate_without_extra_noise() -> None:
    summary = pd.read_csv(RESULTS / "method_summary.csv").set_index("method")
    static = summary.loc["Static fragility"]
    for metric in ("p_at_10", "r_at_10", "map"):
        assert np.isclose(static[metric], static[f"{metric}_ci_low"])
        assert np.isclose(static[metric], static[f"{metric}_ci_high"])


def test_trace_coverage_rows_are_valid_probabilities() -> None:
    coverage = pd.read_csv(RESULTS / "run_trace_coverage.csv")
    total = (
        coverage["complete_fraction"]
        + coverage["partial_fraction"]
        + coverage["unmapped_fraction"]
    )
    assert np.allclose(total, 1.0)
