from __future__ import annotations

from pathlib import Path

import numpy as np

from cad_sim.config import ExperimentConfig
from cad_sim.scoring import rank_scores, score_methods
from cad_sim.synthetic import generate_system, sample_run_inputs


def test_default_configuration_matches_article_v2() -> None:
    config = ExperimentConfig()
    assert config.n_components == 45
    assert config.n_pathways == 14
    assert config.n_activity_records == 500_000
    assert config.n_runs == 30
    assert list(config.seeds) == list(range(42, 72))
    assert config.n_relevant_components == 12
    assert config.n_injected_defects == 120
    assert config.criticality_band_counts == (4, 5, 3, 2)
    assert config.criticality_mapping == (0.25, 0.50, 0.75, 1.00)
    assert config.alternative_criticality_mapping == (0.10, 0.40, 0.70, 1.00)
    assert config.fragility_weights == (0.20, 0.15, 0.25, 0.20, 0.20)
    assert config.normalization_lower_quantile == 0.05
    assert config.normalization_upper_quantile == 0.95
    assert config.complete_trace_probability == 0.785
    assert config.partial_trace_probability == 0.152
    assert config.unmapped_trace_probability == 0.063
    assert config.complete_case_probability == 0.641
    assert config.process_algorithm == "Inductive Miner"
    assert config.process_noise_threshold == 0.8
    assert config.rare_variant_threshold == 0.005
    assert config.sensitivity_variant_threshold == 0.01
    assert config.bootstrap_resamples == 10_000
    assert config.bootstrap_confidence_level == 0.95


def test_static_baseline_is_not_randomized_by_run_inputs() -> None:
    config = ExperimentConfig()
    system = generate_system(config)
    orders = []
    for seed in (config.first_seed, config.first_seed + 1):
        inputs = sample_run_inputs(system, config, seed)
        score = score_methods(
            system,
            inputs.pathway_frequency,
            inputs.observed_incidence,
        )["Static fragility"]
        orders.append(rank_scores(score))
    np.testing.assert_array_equal(orders[0], orders[1])


def test_removed_document_and_figure_directories_are_absent() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("manuscript", "figures", "diagrams"):
        assert not (root / name).exists()

