from dataclasses import replace
import numpy as np
import pytest
from cad_sim.config import ExperimentConfig
from cad_sim.synthetic import generate_system, sample_run_inputs, winsorized_minmax
from cad_sim.scoring import score_methods, score_density_exclusion, fragility_without_indicator, rank_scores
from cad_sim.metrics import ranking_metrics
from cad_sim.experiment import run_experiment, write_results


def test_labels_and_multiplicities_do_not_change_any_predictor_or_score():
    base = ExperimentConfig()
    other = replace(base, relevant_component_ids=tuple(range(12)), n_injected_defects=240)
    first, second = generate_system(base), generate_system(other)
    for name in ("raw_indicators", "indicators", "fragility", "pathway_frequency", "pathway_criticality", "pathway_component_incidence"):
        np.testing.assert_array_equal(getattr(first, name), getattr(second, name))
    a, b = sample_run_inputs(first, base, 42), sample_run_inputs(second, other, 42)
    for name, score in score_methods(first, a.pathway_frequency, a.observed_incidence).items():
        np.testing.assert_array_equal(score, score_methods(second, b.pathway_frequency, b.observed_incidence)[name])
    assert not np.array_equal(first.relevant_components, second.relevant_components)


def test_density_exclusion_uses_renormalized_remaining_weights():
    indicators = np.array([[1., 0., 100., 0., 0.], [0., 1., 0., 1., 1.]])
    result = fragility_without_indicator(indicators, (0.2, 0.15, 0.25, 0.2, 0.2), 2)
    np.testing.assert_allclose(result, [4/15, 1/5 + 8/15])
    changed = indicators.copy(); changed[:, 2] = [-999, 888]
    np.testing.assert_array_equal(result, fragility_without_indicator(changed, (0.2, 0.15, 0.25, 0.2, 0.2), 2))


def test_density_ablation_retains_the_original_incidence_and_inputs():
    config = ExperimentConfig(); system = generate_system(config)
    incidence = system.pathway_component_incidence.copy()
    inputs = sample_run_inputs(system, config, 42)
    observed = inputs.observed_incidence.copy()
    result = score_density_exclusion(system, inputs.pathway_frequency, inputs.observed_incidence, config)
    np.testing.assert_array_equal(system.pathway_component_incidence, incidence)
    np.testing.assert_array_equal(inputs.observed_incidence, observed)
    assert len(result) == 3
    np.testing.assert_array_equal(result["Full CAD"], score_methods(system, inputs.pathway_frequency, observed)["Full CAD"])


@pytest.mark.parametrize("field,value", [("fragility_weights", (float('nan'), .15, .25, .2, .2)), ("complete_trace_probability", float('nan')), ("n_runs", 1), ("n_runs", 2.5), ("system_seed", -1), ("relevant_component_ids", (3.5, 6, 10, 14, 20, 29, 30, 31, 32, 33, 35, 43)), ("criticality_band_counts", (4.5, 4.5, 3, 2))])
def test_invalid_configuration_is_rejected_before_simulation(field, value):
    with pytest.raises(ValueError): replace(ExperimentConfig(), **{field: value}).validate()


def test_nonfinite_indicators_and_noninteger_rank_indices_are_rejected():
    with pytest.raises(ValueError): winsorized_minmax(np.array([[np.nan, 1.]]))
    with pytest.raises(ValueError): ranking_metrics(np.arange(12)+0.5, np.ones(12, dtype=bool))


def test_unexposed_labeled_components_export_without_invented_pathways(tmp_path):
    config = replace(ExperimentConfig(), n_pathways=1, criticality_band_counts=(0, 0, 0, 1), n_runs=2, bootstrap_resamples=100)
    results = run_experiment(config)
    write_results(results, tmp_path)
    import pandas as pd
    records = pd.read_csv(tmp_path / "defect_ground_truth.csv")
    assert records["affected_pathway_id"].isna().any()
    assert not records["test_executed"].any()
    assert not records["executable_fault"].any()
    assert len(records) == 120


def test_all_relevant_recall_at_ten_has_the_declared_ceiling():
    metrics = ranking_metrics(np.arange(45), np.arange(45) < 12)
    assert metrics.p_at_10 == 1
    assert metrics.r_at_10 == 10/12


def test_tie_breaking_does_not_consume_labels():
    np.testing.assert_array_equal(rank_scores(np.zeros(12)), np.arange(12))
