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
    raw_indicators: np.ndarray
    indicators: np.ndarray
    fragility: np.ndarray
    pathway_criticality: np.ndarray
    pathway_frequency: np.ndarray
    pathway_component_incidence: np.ndarray
    relevant_components: np.ndarray
    defect_counts: np.ndarray


TRACE_NOT_APPLICABLE = -1
TRACE_UNMAPPED = 0
TRACE_PARTIAL = 1
TRACE_COMPLETE = 2


@dataclass(frozen=True)
class RunInputs:
    pathway_counts: np.ndarray
    pathway_frequency: np.ndarray
    observed_incidence: np.ndarray
    trace_states: np.ndarray


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
    # The configured 14 pathways are the active primary set after the 0.5%
    # filter. Generate directly on the probability simplex with that lower
    # bound instead of clipping and renormalizing (which could reintroduce
    # below-threshold values).
    remaining_mass = 1.0 - config.n_pathways * config.rare_variant_threshold
    frequency = (
        config.rare_variant_threshold
        + remaining_mass * rng.dirichlet(base_concentration)
    )

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

    relevant = np.zeros(config.n_components, dtype=bool)
    relevant[np.asarray(config.relevant_component_ids, dtype=int)] = True

    # Allocate at least one defect to every pre-specified relevant component.
    # The remaining defect multiplicities use a dedicated random stream and do
    # not depend on any CAD or baseline score.
    defect_rng = np.random.default_rng(config.system_seed + 1)
    relevant_ids = np.flatnonzero(relevant)
    remaining_defects = config.n_injected_defects - len(relevant_ids)
    relevant_counts = np.ones(len(relevant_ids), dtype=int)
    if remaining_defects:
        probabilities = defect_rng.dirichlet(np.ones(len(relevant_ids)))
        relevant_counts += defect_rng.multinomial(remaining_defects, probabilities)
    defect_counts = np.zeros(config.n_components, dtype=int)
    defect_counts[relevant_ids] = relevant_counts

    return SyntheticSystem(
        raw_indicators=raw,
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
) -> RunInputs:
    """Resample pathway counts and trace-link states for one run."""
    rng = np.random.default_rng(seed)
    pathway_counts = rng.multinomial(config.n_activity_records, system.pathway_frequency)
    sampled_frequency = pathway_counts / pathway_counts.sum()

    incidence = system.pathway_component_incidence
    draw = rng.random(incidence.shape)
    trace_states = np.full(incidence.shape, TRACE_NOT_APPLICABLE, dtype=np.int8)
    complete = (incidence == 1) & (draw < config.complete_trace_probability)
    partial = (
        (incidence == 1)
        & (draw >= config.complete_trace_probability)
        & (
            draw
            < config.complete_trace_probability + config.partial_trace_probability
        )
    )
    unmapped = (incidence == 1) & ~(complete | partial)
    trace_states[complete] = TRACE_COMPLETE
    trace_states[partial] = TRACE_PARTIAL
    trace_states[unmapped] = TRACE_UNMAPPED

    # Equation (8) uses a binary membership indicator. A partially mapped
    # activity has at least one reliable runtime assignment, so its observed
    # membership remains one; an unmapped activity contributes zero.
    observed = (complete | partial).astype(float)
    return RunInputs(
        pathway_counts=pathway_counts,
        pathway_frequency=sampled_frequency,
        observed_incidence=observed,
        trace_states=trace_states,
    )
