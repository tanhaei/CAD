from __future__ import annotations

import numpy as np

from cad_sim.config import ExperimentConfig
from cad_sim.synthetic import (
    TRACE_COMPLETE,
    TRACE_NOT_APPLICABLE,
    TRACE_PARTIAL,
    TRACE_UNMAPPED,
    generate_system,
    sample_run_inputs,
    winsorized_minmax,
)


def test_default_config_is_valid() -> None:
    config = ExperimentConfig()
    config.validate()
    assert np.isclose(sum(config.fragility_weights), 1.0)
    assert sum(config.criticality_band_counts) == config.n_pathways


def test_synthetic_ground_truth_counts() -> None:
    config = ExperimentConfig()
    system = generate_system(config)
    assert system.indicators.shape == (45, 5)
    assert system.pathway_component_incidence.shape == (14, 45)
    assert int(system.relevant_components.sum()) == 12
    assert int(system.defect_counts.sum()) == 120
    assert np.all(system.defect_counts[~system.relevant_components] == 0)
    assert np.all(system.defect_counts[system.relevant_components] >= 1)
    assert set(np.flatnonzero(system.relevant_components)) == set(
        config.relevant_component_ids
    )
    assert np.isclose(system.pathway_frequency.sum(), 1.0)
    assert np.all(system.pathway_frequency >= config.rare_variant_threshold)


def test_winsorized_minmax_bounds() -> None:
    values = np.arange(100, dtype=float).reshape(20, 5)
    scaled = winsorized_minmax(values)
    assert scaled.shape == values.shape
    assert np.all(scaled >= 0.0)
    assert np.all(scaled <= 1.0)


def test_run_inputs_follow_binary_cad_membership() -> None:
    config = ExperimentConfig()
    system = generate_system(config)
    inputs = sample_run_inputs(system, config, seed=config.first_seed)

    assert int(inputs.pathway_counts.sum()) == config.n_activity_records
    assert np.isclose(inputs.pathway_frequency.sum(), 1.0)
    assert set(np.unique(inputs.observed_incidence)).issubset({0.0, 1.0})
    assert set(np.unique(inputs.trace_states)).issubset(
        {
            TRACE_NOT_APPLICABLE,
            TRACE_UNMAPPED,
            TRACE_PARTIAL,
            TRACE_COMPLETE,
        }
    )
    partial = inputs.trace_states == TRACE_PARTIAL
    unmapped = inputs.trace_states == TRACE_UNMAPPED
    assert np.all(inputs.observed_incidence[partial] == 1.0)
    assert np.all(inputs.observed_incidence[unmapped] == 0.0)
