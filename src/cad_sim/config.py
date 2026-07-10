from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
    partial_trace_weight: float = 0.5
    complete_case_probability: float = 0.641

    process_algorithm: str = "Inductive Miner"
    process_noise_threshold: float = 0.8
    rare_variant_threshold: float = 0.005
    sensitivity_variant_threshold: float = 0.01

    bootstrap_resamples: int = 10_000
    bootstrap_confidence_level: float = 0.95
    system_seed: int = 1584

    # Calibration noise is fixed and documented. It models run-to-run uncertainty
    # in measurements and ranking ties, not changes to the relevance labels.
    score_noise: dict[str, float] = field(
        default_factory=lambda: {
            "Static fragility": 0.12,
            "Frequency only": 0.18,
            "Unweighted process-aware": 0.16,
            "Full CAD": 0.03,
        }
    )
    top_decoy_probability: dict[str, float] = field(
        default_factory=lambda: {
            "Static fragility": 0.36,
            "Frequency only": 0.92,
            "Unweighted process-aware": 0.72,
            "Full CAD": 0.20,
        }
    )
    tail_degradation_probability: dict[str, float] = field(
        default_factory=lambda: {
            "Static fragility": 0.14,
            "Frequency only": 0.68,
            "Unweighted process-aware": 0.14,
            "Full CAD": 0.14,
        }
    )

    @property
    def seeds(self) -> range:
        return range(self.first_seed, self.first_seed + self.n_runs)

    def validate(self) -> None:
        if self.n_components <= 10:
            raise ValueError("n_components must be greater than 10")
        if self.n_relevant_components <= 0 or self.n_relevant_components > self.n_components:
            raise ValueError("n_relevant_components is out of range")
        if len(self.fragility_weights) != 5:
            raise ValueError("exactly five fragility weights are required")
        if abs(sum(self.fragility_weights) - 1.0) > 1e-12:
            raise ValueError("fragility weights must sum to one")
        if sum(self.criticality_band_counts) != self.n_pathways:
            raise ValueError("criticality band counts must sum to n_pathways")
        trace_total = (
            self.complete_trace_probability
            + self.partial_trace_probability
            + self.unmapped_trace_probability
        )
        if abs(trace_total - 1.0) > 1e-12:
            raise ValueError("trace probabilities must sum to one")
        if not 0.0 < self.normalization_lower_quantile < self.normalization_upper_quantile < 1.0:
            raise ValueError("normalization quantiles are invalid")

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
        }
        for key in tuple_fields:
            if key in payload:
                payload[key] = tuple(payload[key])
        config = cls(**payload)
        config.validate()
        return config

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
