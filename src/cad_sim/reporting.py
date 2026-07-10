from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

from .experiment import ExperimentResults

mpl.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def _save(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_method_summary(results: ExperimentResults, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    frame = results.method_summary
    metrics = ["p_at_10", "r_at_10", "map", "mrr"]
    labels = ["P@10", "R@10", "MAP", "MRR"]
    x = np.arange(len(frame))
    width = 0.19
    fig, ax = plt.subplots(figsize=(9.0, 5.1))
    for index, (column, label) in enumerate(zip(metrics, labels)):
        ax.bar(x + (index - 1.5) * width, frame[column], width, label=label)
    ax.set_xticks(x, frame["method"], rotation=12, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Mean score across 30 runs")
    ax.set_title("Synthetic CAD ranking effectiveness")
    ax.grid(axis="y", linewidth=0.6, alpha=0.35)
    ax.legend(ncol=4)
    _save(fig, output, "ranking_effectiveness")


def plot_ablation(results: ExperimentResults, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    frame = results.ablation_summary
    metrics = ["p_at_10", "r_at_10", "map", "top10_stability"]
    labels = ["P@10", "R@10", "MAP", "Top-10 stability"]
    x = np.arange(len(frame))
    width = 0.19
    fig, ax = plt.subplots(figsize=(9.3, 5.2))
    for index, (column, label) in enumerate(zip(metrics, labels)):
        ax.bar(x + (index - 1.5) * width, frame[column], width, label=label)
    ax.set_xticks(x, frame["configuration"], rotation=14, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Mean score across 30 runs")
    ax.set_title("Synthetic CAD ablation analysis")
    ax.grid(axis="y", linewidth=0.6, alpha=0.35)
    ax.legend(ncol=2)
    _save(fig, output, "ablation_analysis")


def plot_sensitivity(results: ExperimentResults, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    frame = results.sensitivity_summary
    y = np.arange(len(frame))
    height = 0.22
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    ax.barh(y - height, frame["top10_overlap"] / 10.0, height, label="Top-10 overlap / 10")
    ax.barh(y, frame["spearman_rho"], height, label="Spearman rho")
    ax.barh(y + height, frame["kendall_tau"], height, label="Kendall tau")
    ax.set_yticks(y, frame["perturbation"])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Agreement with unperturbed full CAD")
    ax.set_title("Synthetic CAD sensitivity analysis")
    ax.grid(axis="x", linewidth=0.6, alpha=0.35)
    ax.legend()
    _save(fig, output, "sensitivity_analysis")


def plot_precision_recall(results: ExperimentResults, output_dir: str | Path) -> None:
    """Plot PR points from the 30 synthetic ranked outputs.

    This is generated from run-level synthetic rankings, not reconstructed from
    a previous manuscript image.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    run_metrics = results.run_metrics
    fig, ax = plt.subplots(figsize=(7.4, 5.1))
    for method, subset in run_metrics.groupby("method", sort=False):
        # P@10/R@10 is one operating point per run; include the mean point and
        # a light run-level cloud instead of inventing unavailable raw thresholds.
        ax.scatter(
            subset["r_at_10"],
            subset["p_at_10"],
            alpha=0.18,
            s=22,
        )
        ax.scatter(
            [subset["r_at_10"].mean()],
            [subset["p_at_10"].mean()],
            s=70,
            label=method,
        )
    ax.set_xlabel("Recall at 10")
    ax.set_ylabel("Precision at 10")
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.05)
    ax.set_title("Synthetic run-level ranking operating points")
    ax.grid(True, linewidth=0.6, alpha=0.35)
    ax.legend(loc="lower right")
    _save(fig, output, "ranking_operating_points")


def write_manuscript_values(results: ExperimentResults, path: str | Path) -> None:
    payload = {
        "method_summary": results.method_summary.to_dict(orient="records"),
        "ablation_summary": results.ablation_summary.to_dict(orient="records"),
        "sensitivity_summary": results.sensitivity_summary.to_dict(orient="records"),
        "runtime_summary": results.runtime_summary.to_dict(orient="records"),
        "metadata": results.metadata,
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def generate_all_figures(results: ExperimentResults, output_dir: str | Path) -> None:
    plot_method_summary(results, output_dir)
    plot_ablation(results, output_dir)
    plot_sensitivity(results, output_dir)
    plot_precision_recall(results, output_dir)
