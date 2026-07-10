from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from scipy.stats import bootstrap, kendalltau, spearmanr


@dataclass(frozen=True)
class RankingMetrics:
    p_at_10: float
    r_at_10: float
    average_precision: float
    reciprocal_rank: float

    def as_array(self) -> np.ndarray:
        return np.array(
            [self.p_at_10, self.r_at_10, self.average_precision, self.reciprocal_rank],
            dtype=float,
        )


def ranking_metrics(order: np.ndarray, relevant: np.ndarray) -> RankingMetrics:
    order = np.asarray(order, dtype=int)
    relevant = np.asarray(relevant, dtype=bool)
    if order.shape != (len(relevant),):
        raise ValueError("order must contain one position for every component")
    if len(np.unique(order)) != len(order):
        raise ValueError("order contains duplicate component indices")
    ranked_relevance = relevant[order].astype(int)
    relevant_count = int(relevant.sum())
    if relevant_count == 0:
        raise ValueError("at least one relevant component is required")

    top_k = min(10, len(order))
    true_positive = int(ranked_relevance[:top_k].sum())
    p_at_10 = true_positive / top_k
    r_at_10 = true_positive / relevant_count

    cumulative = np.cumsum(ranked_relevance)
    precision = cumulative / np.arange(1, len(order) + 1)
    average_precision = float((precision * ranked_relevance).sum() / relevant_count)
    first_relevant = int(np.flatnonzero(ranked_relevance)[0])
    reciprocal_rank = 1.0 / (first_relevant + 1)

    return RankingMetrics(p_at_10, r_at_10, average_precision, reciprocal_rank)


def bootstrap_mean_ci(
    values: np.ndarray,
    confidence_level: float = 0.95,
    n_resamples: int = 10_000,
    seed: int = 2026,
) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) < 2:
        raise ValueError("bootstrap values must be one-dimensional with length >= 2")
    if np.allclose(values, values[0]):
        return float(values[0]), float(values[0])
    result = bootstrap(
        (values,),
        np.mean,
        confidence_level=confidence_level,
        n_resamples=n_resamples,
        method="BCa",
        random_state=np.random.default_rng(seed),
        vectorized=False,
    )
    return float(result.confidence_interval.low), float(result.confidence_interval.high)


def cliffs_delta(reference: np.ndarray, comparator: np.ndarray) -> float:
    """Cliff's delta where positive values favor the reference sample."""
    reference = np.asarray(reference, dtype=float)
    comparator = np.asarray(comparator, dtype=float)
    comparisons = np.sign(reference[:, None] - comparator[None, :])
    return float(comparisons.mean())


def effect_size_label(delta: float) -> str:
    magnitude = abs(delta)
    if magnitude < 0.147:
        return "negligible"
    if magnitude < 0.33:
        return "small"
    if magnitude < 0.474:
        return "medium"
    return "large"


def ranking_agreement(
    baseline_score: np.ndarray,
    perturbed_score: np.ndarray,
    k: int = 10,
) -> tuple[int, float, float]:
    baseline_order = np.argsort(baseline_score)[::-1]
    perturbed_order = np.argsort(perturbed_score)[::-1]
    overlap = len(set(baseline_order[:k]) & set(perturbed_order[:k]))
    rho = float(spearmanr(baseline_score, perturbed_score).statistic)
    tau = float(kendalltau(baseline_score, perturbed_score).statistic)
    if math.isnan(rho) or math.isnan(tau):
        raise ValueError("ranking correlation is undefined")
    return overlap, rho, tau
