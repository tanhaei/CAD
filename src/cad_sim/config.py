from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class ExperimentConfig:
    """Configuration for the reproducible synthetic CAD experiment."""

    n_components: int = 45
    n_pathways: int = 14
    n_activity_records: int = 500_000
    n_runs: int = 30
    first_seed: int = 42
    n_relevant_components: int = 12
    n_injected_defects: int = 120
    # Fixed before scoring, as required by the manuscript's injected-defect
    # protocol. Keeping the IDs in configuration prevents outcome labels from
    # being derived from, or fed back into, any ranking method.
    relevant_component_ids: tuple[int, ...] = (
        3,
        6,
        10,
        14,
        20,
        29,
        30,
        31,
        32,
        33,
        35,
        43,
    )

    criticality_mapping: tuple[float, float, float, float] = (
        0.25,
        0.50,
        0.75,
        1.00,
    )
    alternative_criticality_mapping: tuple[float, float, float, float] = (
        0.10,
        0.40,
        0.70,
        1.00,
    )
    criticality_band_counts: tuple[int, int, int, int] = (4, 5, 3, 2)

    fragility_weights: tuple[float, float, float, float, float] = (
        0.20,
        0.15,
        0.25,
        0.20,
        0.20,
    )
    normalization_lower_quantile: float = 0.05
    normalization_upper_quantile: float = 0.95

    complete_trace_probability: float = 0.785
    partial_trace_probability: float = 0.152
    unmapped_trace_probability: float = 0.063
    complete_case_probability: float = 0.641

    process_algorithm: str = "Inductive Miner"
    process_noise_threshold: float = 0.8
    rare_variant_threshold: float = 0.005
    sensitivity_variant_threshold: float = 0.01

    bootstrap_resamples: int = 10_000
    bootstrap_confidence_level: float = 0.95
    system_seed: int = 1584

    @property
    def seeds(self) -> range:
        return range(self.first_seed, self.first_seed + self.n_runs)

    def validate(self) -> None:
        if self.n_components <= 10:
            raise ValueError("n_components must be greater than 10")
        if self.n_pathways <= 0:
            raise ValueError("n_pathways must be positive")
        if self.n_activity_records <= 0:
            raise ValueError("n_activity_records must be positive")
        if self.n_runs <= 0:
            raise ValueError("n_runs must be positive")
        if self.n_relevant_components <= 0 or self.n_relevant_components > self.n_components:
            raise ValueError("n_relevant_components is out of range")
        if len(self.relevant_component_ids) != self.n_relevant_components:
            raise ValueError(
                "relevant_component_ids must contain n_relevant_components IDs"
            )
        if len(set(self.relevant_component_ids)) != len(self.relevant_component_ids):
            raise ValueError("relevant_component_ids must be unique")
        if any(
            component_id < 0 or component_id >= self.n_components
            for component_id in self.relevant_component_ids
        ):
            raise ValueError("relevant_component_ids contains an out-of-range ID")
        if self.n_injected_defects < self.n_relevant_components:
            raise ValueError(
                "n_injected_defects must assign at least one defect to every "
                "relevant component"
            )
        if len(self.criticality_mapping) != 4:
            raise ValueError("exactly four criticality scores are required")
        if len(self.alternative_criticality_mapping) != 4:
            raise ValueError("exactly four alternative criticality scores are required")
        for name, mapping in (
            ("criticality_mapping", self.criticality_mapping),
            ("alternative_criticality_mapping", self.alternative_criticality_mapping),
        ):
            if any(score < 0.0 or score > 1.0 for score in mapping):
                raise ValueError(f"{name} values must be in [0, 1]")
            if tuple(sorted(mapping)) != mapping:
                raise ValueError(f"{name} must be nondecreasing")
        if len(self.fragility_weights) != 5:
            raise ValueError("exactly five fragility weights are required")
        if any(weight < 0.0 for weight in self.fragility_weights):
            raise ValueError("fragility weights must be nonnegative")
        if abs(sum(self.fragility_weights) - 1.0) > 1e-12:
            raise ValueError("fragility weights must sum to one")
        if len(self.criticality_band_counts) != 4:
            raise ValueError("exactly four criticality-band counts are required")
        if any(count < 0 for count in self.criticality_band_counts):
            raise ValueError("criticality-band counts must be nonnegative")
        if sum(self.criticality_band_counts) != self.n_pathways:
            raise ValueError("criticality band counts must sum to n_pathways")
        trace_total = (
            self.complete_trace_probability
            + self.partial_trace_probability
            + self.unmapped_trace_probability
        )
        if abs(trace_total - 1.0) > 1e-12:
            raise ValueError("trace probabilities must sum to one")
        if any(
            probability < 0.0 or probability > 1.0
            for probability in (
                self.complete_trace_probability,
                self.partial_trace_probability,
                self.unmapped_trace_probability,
                self.complete_case_probability,
            )
        ):
            raise ValueError("trace and case probabilities must be in [0, 1]")
        if not 0.0 < self.normalization_lower_quantile < self.normalization_upper_quantile < 1.0:
            raise ValueError("normalization quantiles are invalid")
        if not 0.0 <= self.rare_variant_threshold < 1.0:
            raise ValueError("rare_variant_threshold must be in [0, 1)")
        if self.n_pathways * self.rare_variant_threshold >= 1.0:
            raise ValueError(
                "rare_variant_threshold is too large for the configured pathways"
            )
        if not self.rare_variant_threshold <= self.sensitivity_variant_threshold < 1.0:
            raise ValueError(
                "sensitivity_variant_threshold must be at least the primary "
                "threshold and less than one"
            )
        if not 0.0 <= self.process_noise_threshold <= 1.0:
            raise ValueError("process_noise_threshold must be in [0, 1]")
        if self.bootstrap_resamples <= 0:
            raise ValueError("bootstrap_resamples must be positive")
        if not 0.0 < self.bootstrap_confidence_level < 1.0:
            raise ValueError("bootstrap_confidence_level must be in (0, 1)")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, path: str | Path) -> "ExperimentConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        # JSON arrays need to become tuples for frozen dataclass consistency.
        tuple_fields = {
            "criticality_mapping",
            "alternative_criticality_mapping",
            "criticality_band_counts",
            "fragility_weights",
            "relevant_component_ids",
        }
        for key in tuple_fields:
            if key in payload:
                payload[key] = tuple(payload[key])
        config = cls(**payload)
        config.validate()
        return config

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
