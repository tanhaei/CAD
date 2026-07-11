from __future__ import annotations

import numpy as np

from .config import ExperimentConfig
from .synthetic import SyntheticSystem


METHODS = (
    "Static fragility",
    "Frequency only",
    "Unweighted process-aware",
    "Full CAD",
)


def score_methods(
    system: SyntheticSystem,
    sampled_frequency: np.ndarray,
    observed_incidence: np.ndarray,
) -> dict[str, np.ndarray]:
    frequency_exposure = (sampled_frequency[:, None] * observed_incidence).sum(axis=0)
    critical_exposure = (
        (sampled_frequency * system.pathway_criticality)[:, None]
        * observed_incidence
    ).sum(axis=0)
    return {
        "Static fragility": system.fragility.copy(),
        "Frequency only": frequency_exposure,
        "Unweighted process-aware": system.fragility * frequency_exposure,
        "Full CAD": system.fragility * critical_exposure,
    }


def score_method(
    method: str,
    system: SyntheticSystem,
    sampled_frequency: np.ndarray,
    observed_incidence: np.ndarray,
) -> np.ndarray:
    """Compute one method without evaluating the other baselines."""
    if method == "Static fragility":
        return system.fragility.copy()
    frequency_exposure = (sampled_frequency[:, None] * observed_incidence).sum(axis=0)
    if method == "Frequency only":
        return frequency_exposure
    if method == "Unweighted process-aware":
        return system.fragility * frequency_exposure
    if method == "Full CAD":
        critical_exposure = (
            (sampled_frequency * system.pathway_criticality)[:, None]
            * observed_incidence
        ).sum(axis=0)
        return system.fragility * critical_exposure
    raise ValueError(f"unknown ranking method: {method}")


def score_ablations(
    system: SyntheticSystem,
    sampled_frequency: np.ndarray,
    observed_incidence: np.ndarray,
) -> dict[str, np.ndarray]:
    weighted = (
        (sampled_frequency * system.pathway_criticality)[:, None]
        * observed_incidence
    ).sum(axis=0)
    unweighted = (sampled_frequency[:, None] * observed_incidence).sum(axis=0)
    no_frequency = (
        system.pathway_criticality[:, None] * observed_incidence
    ).mean(axis=0)
    return {
        "Full CAD": system.fragility * weighted,
        "Without criticality": system.fragility * unweighted,
        "Without frequency": system.fragility * no_frequency,
        "Without fragility": weighted,
        # Without trace-derived component exposure, the score falls back to the
        # component-only structural signal.
        "Without trace exposure": system.fragility.copy(),
    }


def score_sensitivity_variants(
    system: SyntheticSystem,
    config: ExperimentConfig,
    sampled_frequency: np.ndarray,
    observed_incidence: np.ndarray,
    seed: int,
) -> dict[str, np.ndarray]:
    base_exposure = (
        (sampled_frequency * system.pathway_criticality)[:, None]
        * observed_incidence
    ).sum(axis=0)

    uniform_fragility = system.indicators @ (np.ones(5) / 5.0)

    mapping = {
        float(old): float(new)
        for old, new in zip(
            config.criticality_mapping,
            config.alternative_criticality_mapping,
        )
    }
    alternative_criticality = np.array(
        [mapping[float(value)] for value in system.pathway_criticality]
    )
    alternative_exposure = (
        (sampled_frequency * alternative_criticality)[:, None]
        * observed_incidence
    ).sum(axis=0)

    threshold_frequency = sampled_frequency.copy()
    threshold_frequency[threshold_frequency < config.sensitivity_variant_threshold] = 0.0
    if threshold_frequency.sum() == 0:
        threshold_frequency = sampled_frequency.copy()
    threshold_frequency /= threshold_frequency.sum()
    threshold_exposure = (
        (threshold_frequency * system.pathway_criticality)[:, None]
        * observed_incidence
    ).sum(axis=0)

    reduce_rng = np.random.default_rng(seed + 10_000)
    reduced = observed_incidence.copy()
    nonzero = reduced > 0
    reduced[nonzero & (reduce_rng.random(reduced.shape) < 0.20)] = 0.0
    reduced_exposure = (
        (sampled_frequency * system.pathway_criticality)[:, None] * reduced
    ).sum(axis=0)

    increase_rng = np.random.default_rng(seed + 20_000)
    increased = observed_incidence.copy()
    missing = (
        (system.pathway_component_incidence == 1)
        & (increased == 0)
    )
    increased[
        missing & (increase_rng.random(increased.shape) < 0.20)
    ] = 1.0
    increased_exposure = (
        (sampled_frequency * system.pathway_criticality)[:, None] * increased
    ).sum(axis=0)

    return {
        "Uniform fragility weights": uniform_fragility * base_exposure,
        "Alternative criticality mapping": system.fragility * alternative_exposure,
        "Frequency threshold 1.0%": system.fragility * threshold_exposure,
        "Trace completeness reduced by 20%": system.fragility * reduced_exposure,
        "Trace completeness increased by 20%": system.fragility * increased_exposure,
    }


def rank_scores(score: np.ndarray) -> np.ndarray:
    """Return a descending, deterministic component order.

    Component IDs break exact score ties. Ground-truth relevance is deliberately
    absent from this function so evaluation labels cannot influence ranking.
    """
    score = np.asarray(score, dtype=float)
    if score.ndim != 1 or not np.isfinite(score).all():
        raise ValueError("score must be a finite one-dimensional array")
    component_ids = np.arange(len(score))
    return np.lexsort((component_ids, -score))
