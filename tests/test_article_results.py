from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def _reject_nonstandard_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def test_article_v3_ranking_and_runtime_values_match_committed_results() -> None:
    methods = pd.read_csv(RESULTS / "method_summary.csv").set_index("method")
    order = [
        "Static fragility",
        "Frequency only",
        "Unweighted process-aware",
        "Full CAD",
    ]
    expected_metrics = np.array(
        [
            [0.60, 0.50, 0.55, 0.50],
            [0.49, 0.41, 0.53, 0.95],
            [0.68, 0.56, 0.81, 1.00],
            [0.99, 0.82, 0.96, 1.00],
        ]
    )
    actual_metrics = methods.loc[
        order, ["p_at_10", "r_at_10", "map", "mrr"]
    ].to_numpy()
    np.testing.assert_allclose(np.round(actual_metrics, 2), expected_metrics)

    expected_intervals = np.array(
        [
            [0.60, 0.60, 0.50, 0.50, 0.55, 0.55],
            [0.46, 0.51, 0.39, 0.43, 0.51, 0.54],
            [0.66, 0.69, 0.55, 0.58, 0.79, 0.82],
            [0.97, 1.00, 0.81, 0.83, 0.95, 0.97],
        ]
    )
    interval_columns = [
        "p_at_10_ci_low",
        "p_at_10_ci_high",
        "r_at_10_ci_low",
        "r_at_10_ci_high",
        "map_ci_low",
        "map_ci_high",
    ]
    np.testing.assert_allclose(
        np.round(methods.loc[order, interval_columns].to_numpy(), 2),
        expected_intervals,
    )

    runtime = pd.read_csv(RESULTS / "runtime_summary.csv").set_index("method")
    assert np.isfinite(runtime.loc[order, "mean_seconds"]).all()
    assert (runtime.loc[order, "mean_seconds"] > 0).all()



def test_article_v3_ablation_and_sensitivity_values_match() -> None:
    ablation = pd.read_csv(RESULTS / "ablation_summary.csv").set_index(
        "configuration"
    )
    ablation_order = [
        "Full CAD",
        "Without criticality",
        "Without frequency",
        "Without fragility",
        "Without trace exposure",
    ]
    expected_ablation = np.array(
        [
            [0.99, 0.82, 0.96, 1.00],
            [0.68, 0.56, 0.81, 0.67],
            [0.88, 0.73, 0.90, 0.73],
            [0.65, 0.54, 0.69, 0.66],
            [0.60, 0.50, 0.55, 0.48],
        ]
    )
    np.testing.assert_allclose(
        np.round(
            ablation.loc[
                ablation_order,
                ["p_at_10", "r_at_10", "map", "top10_stability"],
            ].to_numpy(),
            2,
        ),
        expected_ablation,
    )

    sensitivity = pd.read_csv(RESULTS / "sensitivity_summary.csv").set_index(
        "perturbation"
    )
    sensitivity_order = [
        "Uniform fragility weights",
        "Alternative criticality mapping",
        "Frequency threshold 1.0%",
        "Independent deletion of observed links (p=0.20)",
        "Oracle recovery of missing true links (p=0.20)",
    ]
    expected_overlap = np.array([9.83, 8.30, 10.00, 7.93, 9.97])
    expected_correlations = np.array(
        [
            [0.998, 0.979],
            [0.969, 0.871],
            [1.000, 0.995],
            [0.871, 0.766],
            [0.991, 0.980],
        ]
    )
    np.testing.assert_allclose(
        np.round(sensitivity.loc[sensitivity_order, "top10_overlap"], 2),
        expected_overlap,
    )
    np.testing.assert_allclose(
        np.round(
            sensitivity.loc[
                sensitivity_order, ["spearman_rho", "kendall_tau"]
            ].to_numpy(),
            3,
        ),
        expected_correlations,
    )


def test_article_values_json_is_strict_and_mirrors_primary_outputs() -> None:
    raw = (RESULTS / "article_values.json").read_text(encoding="utf-8")
    payload = json.loads(raw, parse_constant=_reject_nonstandard_constant)
    assert payload["schema_version"] == 1
    assert payload["article_revision"] == "V3 (2026-10-06)"

    files = {
        "method_summary": "method_summary.csv",
        "ablation_summary": "ablation_summary.csv",
        "sensitivity_summary": "sensitivity_summary.csv",
        "runtime_summary": "runtime_summary.csv",
        "density_ablation_summary": "density_ablation_summary.csv",
    }
    for key, filename in files.items():
        expected = pd.read_csv(RESULTS / filename)
        actual = pd.DataFrame(payload[key])
        pd.testing.assert_frame_equal(
            actual,
            expected,
            check_dtype=False,
            check_exact=False,
            rtol=1e-13,
            atol=1e-15,
        )

    expected_metadata = json.loads(
        (RESULTS / "metadata.json").read_text(encoding="utf-8")
    )
    assert payload["metadata"] == expected_metadata
    for forbidden in (
        "score_noise",
        "top_decoy_probability",
        "tail_degradation_probability",
        "partial_trace_weight",
    ):
        assert forbidden not in raw
