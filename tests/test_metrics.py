from __future__ import annotations

import numpy as np

from cad_sim.metrics import ranking_metrics, ranking_agreement, cliffs_delta


def test_ranking_metrics_are_consistent() -> None:
    relevant = np.array([1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0], dtype=bool)
    order = np.arange(len(relevant))
    metrics = ranking_metrics(order, relevant)
    assert metrics.p_at_10 == 0.3
    assert metrics.r_at_10 == 1.0
    assert 0.0 < metrics.average_precision <= 1.0
    assert metrics.reciprocal_rank == 1.0


def test_ranking_agreement_identity() -> None:
    score = np.linspace(0, 1, 45)
    overlap, rho, tau = ranking_agreement(score, score)
    assert overlap == 10
    assert np.isclose(rho, 1.0)
    assert np.isclose(tau, 1.0)


def test_cliffs_delta_sign() -> None:
    better = np.array([0.8, 0.9, 1.0])
    worse = np.array([0.1, 0.2, 0.3])
    assert cliffs_delta(better, worse) == 1.0
    assert cliffs_delta(worse, better) == -1.0
