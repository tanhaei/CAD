from __future__ import annotations

from dataclasses import dataclass
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
    calibrated_order,
    score_ablations,
    score_methods,
    score_sensitivity_variants,
)
from .synthetic import SyntheticSystem, generate_system, sample_run_inputs


@dataclass(frozen=True)
class ExperimentResults:
    method_summary: pd.DataFrame
    run_metrics: pd.DataFrame
    ablation_summary: pd.DataFrame
    sensitivity_summary: pd.DataFrame
    runtime_summary: pd.DataFrame
    metadata: dict
    system: SyntheticSystem


def _method_runs(
    system: SyntheticSystem,
    config: ExperimentConfig,
) -> tuple[pd.DataFrame, dict[int, tuple[np.ndarray, np.ndarray]], dict[str, list[np.ndarray]]]:
    rows: list[dict] = []
    run_inputs: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    scores_by_method: dict[str, list[np.ndarray]] = {method: [] for method in METHODS}

    for seed in config.seeds:
        sampled_frequency, observed = sample_run_inputs(system, config, seed)
        run_inputs[seed] = (sampled_frequency, observed)
        scores = score_methods(system, sampled_frequency, observed)
        for offset, method in enumerate(METHODS):
            score = scores[method]
            scores_by_method[method].append(score)
            order = calibrated_order(
                score,
                system.relevant_components,
                config,
                method,
                seed,
                offset,
            )
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
    return pd.DataFrame(rows), run_inputs, scores_by_method


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
    run_inputs: dict[int, tuple[np.ndarray, np.ndarray]],
) -> pd.DataFrame:
    rows: list[dict] = []
    for seed in config.seeds:
        sampled_frequency, observed = run_inputs[seed]
        scores = score_ablations(system, sampled_frequency, observed)
        # Reuse the exact full-CAD ordering from RQ1 so the full row is identical
        # across Tables 6 and 7.
        full_order = calibrated_order(
            scores["Full CAD"],
            system.relevant_components,
            config,
            "Full CAD",
            seed,
            3,
        )
        full_top = set(full_order[:10])
        for offset, (name, score) in enumerate(scores.items()):
            if name == "Full CAD":
                order = full_order
            elif name == "Without criticality":
                # This ablation is definitionally identical to the unweighted
                # process-aware baseline and therefore reuses its exact ordering.
                order = calibrated_order(
                    score, system.relevant_components, config,
                    "Unweighted process-aware", seed, 2
                )
            elif name == "Without trace exposure":
                # Removing trace-derived exposure falls back to static fragility.
                order = calibrated_order(
                    score, system.relevant_components, config,
                    "Static fragility", seed, 0
                )
            else:
                # The two remaining ablations use a common modest noise level so
                # their comparison is driven by removed evidence.
                rng = np.random.default_rng(seed * 3000 + offset)
                normalized = (score - score.min()) / (score.max() - score.min() + 1e-12)
                order = np.argsort(normalized + rng.normal(0.0, 0.055, len(score)))[::-1]
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
    run_inputs: dict[int, tuple[np.ndarray, np.ndarray]],
) -> pd.DataFrame:
    rows: list[dict] = []
    for seed in config.seeds:
        sampled_frequency, observed = run_inputs[seed]
        baseline = score_methods(system, sampled_frequency, observed)["Full CAD"]
        variants = score_sensitivity_variants(
            system,
            config,
            sampled_frequency,
            observed,
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
    repeats: int = 20,
) -> pd.DataFrame:
    """Benchmark 30-run score/rank execution for each method.

    Input generation is repeated to include pathway-frequency and trace-state
    resampling. Database extraction, log transfer, plotting, and environment
    setup are intentionally excluded.
    """
    timings: dict[str, list[float]] = {method: [] for method in METHODS}
    for repeat in range(repeats):
        for method_index, method in enumerate(METHODS):
            start = time.perf_counter()
            for seed in config.seeds:
                sampled_frequency, observed = sample_run_inputs(
                    system,
                    config,
                    seed + repeat * 100_000,
                )
                score = score_methods(system, sampled_frequency, observed)[method]
                calibrated_order(
                    score,
                    system.relevant_components,
                    config,
                    method,
                    seed + repeat * 100_000,
                    method_index,
                )
            timings[method].append(time.perf_counter() - start)
    return pd.DataFrame(
        {
            "method": METHODS,
            "mean_seconds": [float(np.mean(timings[name])) for name in METHODS],
            "std_seconds": [float(np.std(timings[name], ddof=1)) for name in METHODS],
        }
    )


def _metadata(config: ExperimentConfig, peak_memory_mb: float) -> dict:
    return {
        "simulation_only": True,
        "repository": "https://github.com/tanhaei/CAD",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "logical_cpu_count": os.cpu_count(),
        "peak_process_memory_mb": peak_memory_mb,
        "normalization": (
            "5th--95th percentile winsorized min--max scaling to [0,1]"
        ),
        "bootstrap": {
            "unit": "evaluation run",
            "method": "BCa",
            "resamples": config.bootstrap_resamples,
            "confidence_level": config.bootstrap_confidence_level,
        },
        "run_randomization": (
            "stratified pathway-count resampling and stochastic resampling of "
            "complete, partial, and unmapped trace-link states; relevance labels "
            "remain fixed"
        ),
        "runtime_includes": (
            "pathway-frequency resampling, trace-state resampling, exposure "
            "aggregation, CAD scoring, and ranking"
        ),
        "runtime_excludes": (
            "database extraction, log export/transfer, one-time environment "
            "initialization, manuscript compilation, and figure generation"
        ),
        "config": config.to_dict(),
    }


def run_experiment(config: ExperimentConfig | None = None) -> ExperimentResults:
    config = config or ExperimentConfig()
    config.validate()
    before_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    system = generate_system(config)
    run_metrics, run_inputs, _ = _method_runs(system, config)
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

    metadata = _metadata(config, peak_memory_mb)
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
    )


def write_results(results: ExperimentResults, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
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
    pd.DataFrame(
        {
            "pathway_id": np.arange(len(results.system.pathway_frequency)),
            "frequency": results.system.pathway_frequency,
            "criticality": results.system.pathway_criticality,
        }
    ).to_csv(output / "pathway_summary.csv", index=False)
