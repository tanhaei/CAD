from __future__ import annotations

import numpy as np

from cad_sim.config import ExperimentConfig
from cad_sim.synthetic import generate_system, winsorized_minmax


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
    assert np.isclose(system.pathway_frequency.sum(), 1.0)


def test_winsorized_minmax_bounds() -> None:
    values = np.arange(100, dtype=float).reshape(20, 5)
    scaled = winsorized_minmax(values)
    assert scaled.shape == values.shape
    assert np.all(scaled >= 0.0)
    assert np.all(scaled <= 1.0)
