from __future__ import annotations

import numpy as np

from cad_sim.scoring import METHODS, rank_scores, score_method, score_methods
from cad_sim.synthetic import SyntheticSystem


def _small_system() -> SyntheticSystem:
    indicators = np.zeros((3, 5), dtype=float)
    return SyntheticSystem(
        raw_indicators=indicators.copy(),
        indicators=indicators,
        fragility=np.array([0.2, 0.4, 0.8]),
        pathway_criticality=np.array([1.0, 0.5]),
        pathway_frequency=np.array([0.25, 0.75]),
        pathway_component_incidence=np.array(
            [[1, 0, 1], [0, 1, 1]], dtype=np.int8
        ),
        relevant_components=np.array([False, True, False]),
        defect_counts=np.array([0, 1, 0]),
    )


def test_full_cad_matches_manuscript_equation() -> None:
    system = _small_system()
    frequency = np.array([0.25, 0.75])
    observed = system.pathway_component_incidence.astype(float)

    scores = score_methods(system, frequency, observed)
    expected = np.array([0.05, 0.15, 0.50])
    np.testing.assert_allclose(scores["Full CAD"], expected)


def test_method_specific_scoring_matches_batch_scoring() -> None:
    system = _small_system()
    frequency = np.array([0.25, 0.75])
    observed = system.pathway_component_incidence.astype(float)
    batch = score_methods(system, frequency, observed)

    for method in METHODS:
        np.testing.assert_allclose(
            score_method(method, system, frequency, observed),
            batch[method],
        )


def test_ranking_uses_scores_only_and_has_stable_ties() -> None:
    score = np.array([0.5, 0.8, 0.8, 0.1])
    np.testing.assert_array_equal(rank_scores(score), np.array([1, 2, 0, 3]))

