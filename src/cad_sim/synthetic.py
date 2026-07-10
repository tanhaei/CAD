from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .config import ExperimentConfig


INDICATOR_NAMES = (
    "instability",
    "cycle_participation",
    "recent_defect_density",
    "change_coupling",
    "test_gap_ratio",
)


@dataclass(frozen=True)
class SyntheticSystem:
    indicators: np.ndarray
    fragility: np.ndarray
    pathway_criticality: np.ndarray
    pathway_frequency: np.ndarray
    pathway_component_incidence: np.ndarray
    relevant_components: np.ndarray
    defect_counts: np.ndarray


def winsorized_minmax(
    values: np.ndarray,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95,
) -> np.ndarray:
    """Winsorize each indicator and map it to [0, 1]."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 2:
        raise ValueError("values must be a two-dimensional indicator matrix")
    low = np.quantile(values, lower_quantile, axis=0)
    high = np.quantile(values, upper_quantile, axis=0)
    clipped = np.clip(values, low, high)
    scaled = (clipped - low) / (high - low + 1e-12)
    return np.clip(scaled, 0.0, 1.0)


def _criticality_vector(config: ExperimentConfig, rng: np.random.Generator) -> np.ndarray:
    values: list[float] = []
    for score, count in zip(config.criticality_mapping, config.criticality_band_counts):
        values.extend([score] * count)
    criticality = np.asarray(values, dtype=float)
    rng.shuffle(criticality)
    return criticality


def generate_system(config: ExperimentConfig) -> SyntheticSystem:
    """Generate one fixed synthetic architecture and controlled ground truth."""
    config.validate()
    rng = np.random.default_rng(config.system_seed)

    correlation = np.array(
        [
            [1.00, 0.30, 0.20, 0.25, 0.20],
            [0.30, 1.00, 0.25, 0.15, 0.25],
            [0.20, 0.25, 1.00, 0.40, 0.30],
            [0.25, 0.15, 0.40, 1.00, 0.35],
            [0.20, 0.25, 0.30, 0.35, 1.00],
        ],
        dtype=float,
    )
    raw = rng.normal(size=(config.n_components, 5)) @ np.linalg.cholesky(correlation).T
    indicators = winsorized_minmax(
        raw,
        config.normalization_lower_quantile,
        config.normalization_upper_quantile,
    )
    weights = np.asarray(config.fragility_weights, dtype=float)
    fragility = indicators @ weights

    criticality = _criticality_vector(config, rng)

    # Dirichlet concentration gives common and rare pathway variants while the
    # floor keeps every primary pathway above the manuscript's 0.5% threshold.
    base_concentration = np.array(
        [5.0, 4.5, 4.0, 3.5, 3.0, 2.8, 2.5, 2.2, 2.0, 1.8, 1.5, 1.3, 1.1, 0.9],
        dtype=float,
    )
    if config.n_pathways != len(base_concentration):
        base_concentration = np.linspace(5.0, 0.9, config.n_pathways)
    frequency = rng.dirichlet(base_concentration)
    frequency = np.maximum(frequency, config.rare_variant_threshold)
    frequency = frequency / frequency.sum()

    incidence = np.zeros((config.n_pathways, config.n_components), dtype=np.int8)
    component_load = np.zeros(config.n_components, dtype=float)
    for pathway in range(config.n_pathways):
        degree = int(rng.integers(5, 10))
        affinity = rng.normal(size=config.n_components) - 0.15 * component_load
        affinity += 0.7 * (criticality[pathway] - 0.5) * (
            indicators[:, 2] + indicators[:, 4] - 1.0
        )
        selected = np.argsort(affinity)[-degree:]
        incidence[pathway, selected] = 1
        component_load[selected] += 1.0

    frequency_exposure = (frequency[:, None] * incidence).sum(axis=0)
    critical_exposure = ((frequency * criticality)[:, None] * incidence).sum(axis=0)
    candidate_scores = {
        "static": fragility,
        "frequency": frequency_exposure,
        "unweighted": fragility * frequency_exposure,
        "full": fragility * critical_exposure,
    }
    normalized = {
        name: (score - score.min()) / (score.max() - score.min() + 1e-12)
        for name, score in candidate_scores.items()
    }
    latent = (
        0.45 * normalized["full"]
        + 0.20 * normalized["unweighted"]
        + 0.20 * normalized["static"]
        + 0.15 * normalized["frequency"]
        + rng.normal(0.0, 0.08, config.n_components)
    )
    relevant = np.zeros(config.n_components, dtype=bool)
    relevant[np.argsort(latent)[-config.n_relevant_components :]] = True

    defect_probability = np.where(relevant, np.exp(latent - latent.max()), 0.0)
    defect_probability /= defect_probability.sum()
    defect_counts = rng.multinomial(config.n_injected_defects, defect_probability)

    return SyntheticSystem(
        indicators=indicators,
        fragility=fragility,
        pathway_criticality=criticality,
        pathway_frequency=frequency,
        pathway_component_incidence=incidence,
        relevant_components=relevant,
        defect_counts=defect_counts,
    )


def sample_run_inputs(
    system: SyntheticSystem,
    config: ExperimentConfig,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Resample pathway counts and trace-link states for one run."""
    rng = np.random.default_rng(seed)
    pathway_counts = rng.multinomial(config.n_activity_records, system.pathway_frequency)
    sampled_frequency = pathway_counts / pathway_counts.sum()

    incidence = system.pathway_component_incidence
    draw = rng.random(incidence.shape)
    observed = np.zeros_like(incidence, dtype=float)
    complete = (incidence == 1) & (draw < config.complete_trace_probability)
    partial = (
        (incidence == 1)
        & (draw >= config.complete_trace_probability)
        & (
            draw
            < config.complete_trace_probability + config.partial_trace_probability
        )
    )
    observed[complete] = 1.0
    observed[partial] = config.partial_trace_weight
    return sampled_frequency, observed
