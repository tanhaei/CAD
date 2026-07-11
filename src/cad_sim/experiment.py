from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import json
import os
import platform
import resource
import time

import numpy as np
import pandas as pd

from .config import ExperimentConfig
from .metrics import (
    bootstrap_mean_ci,
    cliffs_delta,
    effect_size_label,
    ranking_agreement,
    ranking_metrics,
)
from .scoring import (
    METHODS,
    rank_scores,
    score_ablations,
    score_method,
    score_methods,
    score_sensitivity_variants,
)
from .synthetic import (
    TRACE_COMPLETE,
    TRACE_PARTIAL,
    TRACE_UNMAPPED,
    RunInputs,
    SyntheticSystem,
    generate_system,
    sample_run_inputs,
    winsorized_minmax,
)

RUNTIME_BENCHMARK_REPEATS = 20


@dataclass(frozen=True)
class ExperimentResults:
    method_summary: pd.DataFrame
    run_metrics: pd.DataFrame
    ablation_summary: pd.DataFrame
    sensitivity_summary: pd.DataFrame
    runtime_summary: pd.DataFrame
    metadata: dict
    system: SyntheticSystem
    run_inputs: dict[int, RunInputs]


def _method_runs(
    system: SyntheticSystem,
    config: ExperimentConfig,
) -> tuple[pd.DataFrame, dict[int, RunInputs]]:
    rows: list[dict] = []
    run_inputs: dict[int, RunInputs] = {}

    for seed in config.seeds:
        inputs = sample_run_inputs(system, config, seed)
        run_inputs[seed] = inputs
        scores = score_methods(
            system,
            inputs.pathway_frequency,
            inputs.observed_incidence,
        )
        for method in METHODS:
            score = scores[method]
            order = rank_scores(score)
            metric = ranking_metrics(order, system.relevant_components)
            rows.append(
                {
                    "seed": seed,
                    "method": method,
                    "p_at_10": metric.p_at_10,
                    "r_at_10": metric.r_at_10,
                    "average_precision": metric.average_precision,
                    "reciprocal_rank": metric.reciprocal_rank,
                }
            )
    return pd.DataFrame(rows), run_inputs


def _summarize_methods(
    run_metrics: pd.DataFrame,
    config: ExperimentConfig,
) -> pd.DataFrame:
    full_ap = run_metrics.loc[
        run_metrics["method"] == "Full CAD", "average_precision"
    ].to_numpy()
    rows: list[dict] = []
    for index, method in enumerate(METHODS):
        subset = run_metrics.loc[run_metrics["method"] == method]
        row: dict[str, float | str] = {"method": method}
        for metric_name, column in (
            ("p_at_10", "p_at_10"),
            ("r_at_10", "r_at_10"),
            ("map", "average_precision"),
            ("mrr", "reciprocal_rank"),
        ):
            values = subset[column].to_numpy()
            row[metric_name] = float(values.mean())
            if metric_name in {"p_at_10", "r_at_10", "map"}:
                low, high = bootstrap_mean_ci(
                    values,
                    confidence_level=config.bootstrap_confidence_level,
                    n_resamples=config.bootstrap_resamples,
                    seed=config.system_seed + index,
                )
                row[f"{metric_name}_ci_low"] = low
                row[f"{metric_name}_ci_high"] = high
        if method == "Full CAD":
            row["cliffs_delta"] = np.nan
            row["cliffs_delta_label"] = "reference"
        else:
            comparator = subset["average_precision"].to_numpy()
            delta = cliffs_delta(full_ap, comparator)
            row["cliffs_delta"] = delta
            row["cliffs_delta_label"] = effect_size_label(delta)
        rows.append(row)
    return pd.DataFrame(rows)


def _ablation_runs(
    system: SyntheticSystem,
    config: ExperimentConfig,
    run_inputs: dict[int, RunInputs],
) -> pd.DataFrame:
    rows: list[dict] = []
    for seed in config.seeds:
        inputs = run_inputs[seed]
        scores = score_ablations(
            system,
            inputs.pathway_frequency,
            inputs.observed_incidence,
        )
        full_order = rank_scores(scores["Full CAD"])
        full_top = set(full_order[:10])
        for name, score in scores.items():
            order = full_order if name == "Full CAD" else rank_scores(score)
            metric = ranking_metrics(order, system.relevant_components)
            overlap = len(full_top & set(order[:10])) / 10.0
            rows.append(
                {
                    "seed": seed,
                    "configuration": name,
                    "p_at_10": metric.p_at_10,
                    "r_at_10": metric.r_at_10,
                    "map": metric.average_precision,
                    "top10_stability": overlap,
                }
            )
    return pd.DataFrame(rows)


def _summarize_ablation(ablation_runs: pd.DataFrame) -> pd.DataFrame:
    order = (
        "Full CAD",
        "Without criticality",
        "Without frequency",
        "Without fragility",
        "Without trace exposure",
    )
    rows = []
    for name in order:
        subset = ablation_runs.loc[ablation_runs["configuration"] == name]
        rows.append(
            {
                "configuration": name,
                "p_at_10": float(subset["p_at_10"].mean()),
                "r_at_10": float(subset["r_at_10"].mean()),
                "map": float(subset["map"].mean()),
                "top10_stability": float(subset["top10_stability"].mean()),
            }
        )
    return pd.DataFrame(rows)


def _sensitivity_runs(
    system: SyntheticSystem,
    config: ExperimentConfig,
    run_inputs: dict[int, RunInputs],
) -> pd.DataFrame:
    rows: list[dict] = []
    for seed in config.seeds:
        inputs = run_inputs[seed]
        baseline = score_methods(
            system,
            inputs.pathway_frequency,
            inputs.observed_incidence,
        )["Full CAD"]
        variants = score_sensitivity_variants(
            system,
            config,
            inputs.pathway_frequency,
            inputs.observed_incidence,
            seed,
        )
        for name, score in variants.items():
            overlap, rho, tau = ranking_agreement(baseline, score)
            rows.append(
                {
                    "seed": seed,
                    "perturbation": name,
                    "top10_overlap": overlap,
                    "spearman_rho": rho,
                    "kendall_tau": tau,
                }
            )
    return pd.DataFrame(rows)


def _summarize_sensitivity(sensitivity_runs: pd.DataFrame) -> pd.DataFrame:
    order = (
        "Uniform fragility weights",
        "Alternative criticality mapping",
        "Frequency threshold 1.0%",
        "Trace completeness reduced by 20%",
        "Trace completeness increased by 20%",
    )
    rows = []
    for name in order:
        subset = sensitivity_runs.loc[sensitivity_runs["perturbation"] == name]
        rows.append(
            {
                "perturbation": name,
                "top10_overlap": float(subset["top10_overlap"].mean()),
                "spearman_rho": float(subset["spearman_rho"].mean()),
                "kendall_tau": float(subset["kendall_tau"].mean()),
            }
        )
    return pd.DataFrame(rows)


def _benchmark_methods(
    system: SyntheticSystem,
    config: ExperimentConfig,
    repeats: int = RUNTIME_BENCHMARK_REPEATS,
) -> pd.DataFrame:
    """Benchmark 30-run score/rank execution for each method.

    Input generation is repeated to include pathway-frequency and trace-state
    resampling. Database extraction, log transfer, plotting, and environment
    setup are intentionally excluded.
    """
    timings: dict[str, list[float]] = {method: [] for method in METHODS}
    for repeat in range(repeats):
        for method in METHODS:
            start = time.perf_counter()
            normalized_indicators = winsorized_minmax(
                system.raw_indicators,
                config.normalization_lower_quantile,
                config.normalization_upper_quantile,
            )
            benchmark_system = replace(
                system,
                indicators=normalized_indicators,
                fragility=(
                    normalized_indicators
                    @ np.asarray(config.fragility_weights, dtype=float)
                ),
            )
            for seed in config.seeds:
                inputs = sample_run_inputs(
                    benchmark_system,
                    config,
                    seed + repeat * 100_000,
                )
                score = score_method(
                    method,
                    benchmark_system,
                    inputs.pathway_frequency,
                    inputs.observed_incidence,
                )
                rank_scores(score)
            timings[method].append(time.perf_counter() - start)
    return pd.DataFrame(
        {
            "method": METHODS,
            "mean_seconds": [float(np.mean(timings[name])) for name in METHODS],
            "std_seconds": [float(np.std(timings[name], ddof=1)) for name in METHODS],
        }
    )


def _metadata(
    config: ExperimentConfig,
    peak_memory_mb: float,
    analysis_wall_clock_seconds: float,
) -> dict:
    return {
        "simulation_only": True,
        "repository": "https://github.com/tanhaei/CAD",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "logical_cpu_count": os.cpu_count(),
        "peak_process_memory_mb": peak_memory_mb,
        "analysis_wall_clock_seconds": analysis_wall_clock_seconds,
        "normalization": (
            "5th--95th percentile winsorized min--max scaling to [0,1]"
        ),
        "bootstrap": {
            "unit": "evaluation run",
            "method": "BCa",
            "resamples": config.bootstrap_resamples,
            "confidence_level": config.bootstrap_confidence_level,
        },
        "synthetic_scope": {
            "active_pathways_generated_directly": True,
            "process_discovery_executed": False,
            "case_level_trace_completeness_simulated": False,
            "configured_process_algorithm": config.process_algorithm,
            "configured_process_noise_threshold": config.process_noise_threshold,
            "reported_complete_case_probability": config.complete_case_probability,
        },
        "run_randomization": (
            "multinomial pathway-count resampling and stochastic resampling of "
            "complete, partial, and unmapped trace-link states; relevance labels "
            "remain fixed"
        ),
        "runtime_includes": (
            "fragility normalization, pathway-frequency resampling, trace-state "
            "resampling, exposure aggregation, method-specific scoring, and ranking"
        ),
        "runtime_excludes": (
            "database extraction, log export/transfer, one-time environment "
            "initialization, and result serialization"
        ),
        "runtime_benchmark": {
            "repeats": RUNTIME_BENCHMARK_REPEATS,
            "evaluation_runs_per_repeat": config.n_runs,
        },
        "config": config.to_dict(),
    }


def run_experiment(config: ExperimentConfig | None = None) -> ExperimentResults:
    started_at = time.perf_counter()
    config = config or ExperimentConfig()
    config.validate()
    before_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    system = generate_system(config)
    run_metrics, run_inputs = _method_runs(system, config)
    method_summary = _summarize_methods(run_metrics, config)

    ablation_runs = _ablation_runs(system, config, run_inputs)
    ablation_summary = _summarize_ablation(ablation_runs)

    sensitivity_runs = _sensitivity_runs(system, config, run_inputs)
    sensitivity_summary = _summarize_sensitivity(sensitivity_runs)

    runtime_summary = _benchmark_methods(system, config)

    after_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB; macOS reports bytes. This repository's CI and the
    # supplied smoke test use Linux, but handle both conventions defensively.
    raw_peak = max(before_peak, after_peak)
    peak_memory_mb = raw_peak / 1024.0
    if peak_memory_mb > 100_000:
        peak_memory_mb = raw_peak / (1024.0 * 1024.0)

    analysis_wall_clock_seconds = time.perf_counter() - started_at
    metadata = _metadata(
        config,
        peak_memory_mb,
        analysis_wall_clock_seconds,
    )
    metadata["relevant_component_ids"] = [
        int(index) for index in np.flatnonzero(system.relevant_components)
    ]
    metadata["defect_count_total"] = int(system.defect_counts.sum())

    return ExperimentResults(
        method_summary=method_summary,
        run_metrics=run_metrics,
        ablation_summary=ablation_summary,
        sensitivity_summary=sensitivity_summary,
        runtime_summary=runtime_summary,
        metadata=metadata,
        system=system,
        run_inputs=run_inputs,
    )


DEFECT_CATEGORIES = (
    "dependency misuse",
    "unstable service interaction",
    "schema/contract inconsistency",
    "missing fallback",
    "test-gap exposure",
    "observability gap",
)
CRITICALITY_BANDS = ("Low", "Moderate", "High", "Critical")


def _criticality_band(score: float, mapping: tuple[float, ...]) -> str:
    distances = np.abs(np.asarray(mapping, dtype=float) - score)
    return CRITICALITY_BANDS[int(np.argmin(distances))]


def _defect_ground_truth(results: ExperimentResults) -> pd.DataFrame:
    """Expand component counts into the defect-level schema in the manuscript."""
    rows: list[dict] = []
    defect_number = 1
    mapping = tuple(results.metadata["config"]["criticality_mapping"])
    for component_id, count in enumerate(results.system.defect_counts):
        if count == 0:
            continue
        pathways = np.flatnonzero(
            results.system.pathway_component_incidence[:, component_id]
        )
        if not len(pathways):
            raise RuntimeError(
                f"relevant component {component_id} has no pathway exposure"
            )
        for local_index in range(int(count)):
            pathway_id = int(pathways[local_index % len(pathways)])
            criticality = float(results.system.pathway_criticality[pathway_id])
            rows.append(
                {
                    "defect_id": f"D-{defect_number:03d}",
                    "component_id": component_id,
                    "category": DEFECT_CATEGORIES[
                        (component_id + local_index) % len(DEFECT_CATEGORIES)
                    ],
                    "affected_pathway_id": pathway_id,
                    "criticality_band": _criticality_band(criticality, mapping),
                    "criticality_score": criticality,
                    "related_test_id": f"T-C{component_id:02d}-{local_index + 1:03d}",
                }
            )
            defect_number += 1
    return pd.DataFrame(rows)


def _run_pathway_summary(results: ExperimentResults) -> pd.DataFrame:
    rows: list[dict] = []
    for seed, inputs in results.run_inputs.items():
        for pathway_id, (count, frequency) in enumerate(
            zip(inputs.pathway_counts, inputs.pathway_frequency)
        ):
            rows.append(
                {
                    "seed": seed,
                    "pathway_id": pathway_id,
                    "activity_count": int(count),
                    "frequency": float(frequency),
                }
            )
    return pd.DataFrame(rows)


def _run_trace_coverage(results: ExperimentResults) -> pd.DataFrame:
    rows: list[dict] = []
    for seed, inputs in results.run_inputs.items():
        states = inputs.trace_states
        applicable = states >= TRACE_UNMAPPED
        total = int(applicable.sum())
        counts = {
            "complete": int((states == TRACE_COMPLETE).sum()),
            "partial": int((states == TRACE_PARTIAL).sum()),
            "unmapped": int((states == TRACE_UNMAPPED).sum()),
        }
        rows.append(
            {
                "seed": seed,
                "trace_links": total,
                "complete_links": counts["complete"],
                "partial_links": counts["partial"],
                "unmapped_links": counts["unmapped"],
                "complete_fraction": counts["complete"] / total,
                "partial_fraction": counts["partial"] / total,
                "unmapped_fraction": counts["unmapped"] / total,
            }
        )
    return pd.DataFrame(rows)


def write_results(results: ExperimentResults, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    defect_ground_truth = _defect_ground_truth(results)
    run_pathways = _run_pathway_summary(results)
    trace_coverage = _run_trace_coverage(results)
    results.metadata["realized_trace_coverage_mean"] = {
        "complete": float(trace_coverage["complete_fraction"].mean()),
        "partial": float(trace_coverage["partial_fraction"].mean()),
        "unmapped": float(trace_coverage["unmapped_fraction"].mean()),
    }
    results.method_summary.to_csv(output / "method_summary.csv", index=False)
    results.run_metrics.to_csv(output / "run_metrics.csv", index=False)
    results.ablation_summary.to_csv(output / "ablation_summary.csv", index=False)
    results.sensitivity_summary.to_csv(output / "sensitivity_summary.csv", index=False)
    results.runtime_summary.to_csv(output / "runtime_summary.csv", index=False)
    (output / "metadata.json").write_text(
        json.dumps(results.metadata, indent=2), encoding="utf-8"
    )
    pd.DataFrame(
        {
            "component_id": np.arange(len(results.system.relevant_components)),
            "relevant": results.system.relevant_components.astype(int),
            "injected_defects": results.system.defect_counts,
            "fragility": results.system.fragility,
        }
    ).to_csv(output / "component_ground_truth.csv", index=False)
    defect_ground_truth.to_csv(output / "defect_ground_truth.csv", index=False)
    pd.DataFrame(
        {
            "pathway_id": np.arange(len(results.system.pathway_frequency)),
            "frequency": results.system.pathway_frequency,
            "criticality": results.system.pathway_criticality,
            "criticality_band": [
                _criticality_band(float(score), tuple(results.metadata["config"]["criticality_mapping"]))
                for score in results.system.pathway_criticality
            ],
        }
    ).to_csv(output / "pathway_summary.csv", index=False)
    run_pathways.to_csv(output / "run_pathway_summary.csv", index=False)
    trace_coverage.to_csv(output / "run_trace_coverage.csv", index=False)
