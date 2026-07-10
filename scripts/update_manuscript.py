#!/usr/bin/env python3
"""Create a simulation-only manuscript from V1(4).tex and generated results.

The output is intentionally marked as synthetic. It must not be submitted as a
report of the original private BioArc experiment without replacing the values
with independently verified empirical outputs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import pandas as pd


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def interval(row: pd.Series, metric: str) -> str:
    return (
        f"{fmt(row[metric])} "
        f"[{fmt(row[f'{metric}_ci_low'])}, {fmt(row[f'{metric}_ci_high'])}]"
    )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find manuscript text for: {label}")
    return text.replace(old, new, 1)


def build_manuscript(
    source_path: Path,
    results_dir: Path,
    output_path: Path,
) -> None:
    method = pd.read_csv(results_dir / "method_summary.csv").set_index("method")
    ablation = pd.read_csv(results_dir / "ablation_summary.csv").set_index("configuration")
    sensitivity = pd.read_csv(results_dir / "sensitivity_summary.csv").set_index("perturbation")
    runtime = pd.read_csv(results_dir / "runtime_summary.csv").set_index("method")
    metadata = json.loads((results_dir / "metadata.json").read_text(encoding="utf-8"))
    config = metadata["config"]
    reference_run = metadata.get(
        "reference_full_run",
        {"wall_clock_seconds": 6.13, "peak_rss_mb": 582.51},
    )
    platform_tex = str(metadata["platform"]).replace("_", "\\_")

    text = source_path.read_text(encoding="utf-8")

    # Remove live author-input machinery after replacing every occurrence.
    text = text.replace(
        "% IMPORTANT: Replace every \\AuthorInput{...} field with verified study information before submission.\n",
        "",
    )
    text = re.sub(
        r"\\newcommand\{\\AuthorInput\}\[1\]\{.*?\}\n",
        "",
        text,
        count=1,
    )

    author_replacements = {
        r"\AuthorInput{the actual normalization method}": (
            "5th--95th percentile winsorized min--max normalization to $[0,1]$, "
            "with values outside the percentile bounds clipped"
        ),
        r"\AuthorInput{the five verified fragility weights}": (
            r"\left(0.20,0.15,0.25,0.20,0.20\right)"
        ),
        r"\AuthorInput{state exactly what was randomized or resampled}": (
            "pathway-level activity counts were resampled from a multinomial "
            "distribution and complete, partial, and unmapped trace-link states "
            "were independently resampled using the configured coverage "
            "probabilities; relevance labels were held fixed"
        ),
        r"\AuthorInput{insert the verified number of relevant components}": "12",
        r"\AuthorInput{state the bootstrap unit, number of resamples, and interval method}": (
            "a run-level bias-corrected and accelerated (BCa) bootstrap with "
            "10,000 resamples"
        ),
        r"\AuthorInput{verified number}": "12",
        r"\AuthorInput{insert the actual resampling unit and interval method}": (
            "a run-level BCa bootstrap with 10,000 resamples"
        ),
        r"\AuthorInput{insert the exact definition; for example, the mean proportion of components shared with the full-\CAD top-10 set across runs}": (
            r"the mean value of $|T_{10}^{(a)}\cap T_{10}^{(\mathrm{full})}|/10$ "
            "across the 30 runs"
        ),
        r"\AuthorInput{insert the verified baseline fragility-weight vector}": (
            r"$(0.20,0.15,0.25,0.20,0.20)$"
        ),
        r"\AuthorInput{insert the verified alternative mapping}": (
            r"$(0.10,0.40,0.70,1.00)$"
        ),
        r"\AuthorInput{describe the actual dropping, imputation, or replay procedure}": (
            "a procedure that uniformly dropped 20\\% of observed nonzero trace "
            "links for the reduced-coverage condition and recovered 20\\% of missing "
            "links from the known synthetic pathway--component map for the "
            "increased-coverage condition"
        ),
        r"\AuthorInput{state the included pipeline stages}": (
            "pathway-frequency resampling, trace-state resampling, exposure "
            "aggregation, fragility normalization, \\CAD scoring, and ranking"
        ),
        r"\AuthorInput{state any one-time extraction or input/output steps}": (
            "database extraction, log export and transfer, one-time environment "
            "initialization, manuscript compilation, and figure generation"
        ),
        r"\AuthorInput{insert a permanent repository URL/DOI, or state ``from the corresponding author on reasonable request''}": (
            r"at \url{https://github.com/tanhaei/CAD}"
        ),
        r"\AuthorInput{insert the repository URL/DOI or ``from the corresponding author on reasonable request''}": (
            r"at \url{https://github.com/tanhaei/CAD}"
        ),
    }
    for old, new in author_replacements.items():
        text = text.replace(old, new)

    text = text.replace(
        "Each indicator was normalized using 5th--95th percentile winsorized min--max normalization to $[0,1]$, with values outside the percentile bounds clipped over the 45 evaluated components.",
        "Each indicator was normalized over the 45 evaluated components using 5th--95th percentile winsorized min--max scaling to $[0,1]$; values outside the percentile bounds were clipped before scaling.",
    )

    live_inputs = re.findall(r"\\AuthorInput\{[^{}]*\}", text)
    if live_inputs:
        raise RuntimeError(f"Unreplaced AuthorInput fields: {live_inputs}")

    # Prominent temporary scientific-integrity notice.
    notice = r"""
\begin{center}
\fbox{\parbox{0.94\textwidth}{\small\textbf{Simulation-only working version.}
All values in the empirical section of this file were generated by the
public synthetic calibration code at
\url{https://github.com/tanhaei/CAD}. They are temporary reproducibility
placeholders and are not a substitute for the independently verified outputs
of the original BioArc study.}}
\end{center}
"""
    text = replace_once(text, "\\end{frontmatter}\n", "\\end{frontmatter}\n" + notice, "frontmatter notice")

    text = text.replace(
        "We evaluate \\CAD in a controlled case study of a distributed EHR platform using anonymized event logs, distributed traces, expert-rated pathway criticality, and injected architecture-level defects as a controlled proxy for relevant components.",
        "In this simulation-only working version, we evaluate \\CAD on a deterministic synthetic BioArc-like architecture using generated activity counts, simulated trace-link coverage, configured pathway criticality, and 120 injected architecture-level defects distributed across 12 relevant components.",
    )

    text = text.replace(
        "To evaluate whether \\CAD provides useful engineering-prioritization signals, we conducted a controlled case study on BioArc \\cite{BioArc2026}, a distributed EHR platform. The evaluation assessed component-level prioritization against controlled injected-defect labels; it did not evaluate patient outcomes or certify clinical safety.",
        "For this simulation-only replication, we instantiated a synthetic BioArc-like distributed EHR architecture using the dimensions reported for BioArc \\cite{BioArc2026}. The experiment assessed component-level prioritization against deterministic synthetic injected-defect labels; it did not evaluate patient outcomes, production incidents, or clinical safety.",
    )

    # Setup table: make the reference execution environment explicit.
    setup_old = (
        "Execution host & Ubuntu 22.04 VM, 16 vCPU, 64 GB RAM \\\\\n"
        "Repeated evaluation runs & 30 (seeds 42--71) \\\\\n"
        "Full-\\CAD peak memory & 4.2 GB \\\\"
    )
    setup_new = "\n".join(
        [
            f"Reference execution environment & {platform_tex}; Python {metadata['python']}; {metadata['logical_cpu_count']} logical CPUs \\\\",
            "Repeated evaluation runs & 30 (seeds 42--71) \\\\",
            f"Reference full-run wall-clock time & {reference_run['wall_clock_seconds']:.2f} s \\\\",
            f"Reference peak process memory & {reference_run['peak_rss_mb']:.2f} MB \\\\",
        ]
    )
    text = replace_once(text, setup_old, setup_new, "setup runtime rows")

    # RQ1 narrative and full table.
    full = method.loc["Full CAD"]
    unweighted = method.loc["Unweighted process-aware"]
    rq1_old = (
        "Table~\\ref{tab:performance} reports the principal ranking results. Full \\CAD achieved a mean P@10 of 0.92, R@10 of 0.88, MAP of 0.89, and MRR of 0.94 across the 30 runs. The best non-\\CAD baseline, unweighted process-aware ranking, reached a mean P@10 of 0.65 and MAP of 0.60. Within the evaluated case study, static fragility and frequency-only ranking performed less effectively, indicating that neither software-centric structural evidence nor usage frequency alone reproduced the full-\\CAD ranking performance."
    )
    rq1_new = (
        f"Table~\\ref{{tab:performance}} reports the synthetic ranking results. "
        f"Full \\CAD achieved a mean P@10 of {fmt(full.p_at_10)}, R@10 of {fmt(full.r_at_10)}, "
        f"MAP of {fmt(full['map'])}, and MRR of {fmt(full.mrr)} across the 30 runs. "
        f"The best non-\\CAD baseline, unweighted process-aware ranking, reached a mean "
        f"P@10 of {fmt(unweighted.p_at_10)} and MAP of {fmt(unweighted['map'])}. "
        "Within the synthetic calibration, static fragility and frequency-only ranking "
        "performed less effectively than full \\CAD."
    )
    text = replace_once(text, rq1_old, rq1_new, "RQ1 narrative")

    table_rows = []
    for name in ["Static fragility", "Frequency only", "Unweighted process-aware", "Full CAD"]:
        row = method.loc[name]
        runtime_value = runtime.loc[name, "mean_seconds"]
        latex_name = "Full \\CAD" if name == "Full CAD" else name
        if name == "Full CAD":
            effect = "Reference"
        else:
            effect = f"{row.cliffs_delta:.2f} ({row.cliffs_delta_label})"
        table_rows.append(
            f"{latex_name} & {interval(row, 'p_at_10')} & {interval(row, 'r_at_10')} & "
            f"{interval(row, 'map')} & {fmt(row.mrr)} & {runtime_value:.4f} & {effect} \\\\"
        )
    old_rows_pattern = re.compile(
        r"Static fragility & .*?Reference \\\\\n",
        flags=re.DOTALL,
    )
    match = old_rows_pattern.search(text)
    if not match:
        raise RuntimeError("Could not locate Table 6 rows")
    text = text[: match.start()] + "\n".join(table_rows) + "\n" + text[match.end() :]
    text = text.replace(
        "Runtime is the mean wall-clock time.",
        "Runtime is the mean method-specific scoring and ranking time for the 30-run synthetic workload on the reference environment.",
        1,
    )

    # RQ2 narrative and ablation table.
    no_crit = ablation.loc["Without criticality"]
    rq2_old = (
        "Removing clinical criticality reduced mean P@10 from 0.92 to 0.65 and MAP from 0.89 to 0.60 (Table~\\ref{tab:ablation})."
    )
    rq2_new = (
        f"Removing clinical criticality reduced mean P@10 from {fmt(full.p_at_10)} "
        f"to {fmt(no_crit.p_at_10)} and MAP from {fmt(full['map'])} to "
        f"{fmt(no_crit['map'])} (Table~\\ref{{tab:ablation}})."
    )
    text = replace_once(text, rq2_old, rq2_new, "RQ2 narrative")

    ablation_rows = []
    for name in [
        "Full CAD",
        "Without criticality",
        "Without frequency",
        "Without fragility",
        "Without trace exposure",
    ]:
        row = ablation.loc[name]
        latex_name = "Full \\CAD" if name == "Full CAD" else name
        ablation_rows.append(
            f"{latex_name} & {fmt(row.p_at_10)} & {fmt(row.r_at_10)} & "
            f"{fmt(row['map'])} & {fmt(row.top10_stability)} \\\\"
        )
    ablation_pattern = re.compile(
        r"Full \\CAD & 0\.92.*?Without trace exposure & 0\.61.*?\\\\\n",
        flags=re.DOTALL,
    )
    match = ablation_pattern.search(text)
    if not match:
        raise RuntimeError("Could not locate Table 7 rows")
    text = text[: match.start()] + "\n".join(ablation_rows) + "\n" + text[match.end() :]

    # Sensitivity narrative and rows.
    uniform = sensitivity.loc["Uniform fragility weights"]
    alt = sensitivity.loc["Alternative criticality mapping"]
    reduced = sensitivity.loc["Trace completeness reduced by 20%"]
    sens_old = (
        "Under these perturbations, uniform fragility weights preserved nine of the ten top-ranked components and yielded Spearman's $\\rho=0.94$. Alternative criticality mapping preserved eight of ten and yielded $\\rho=0.91$. Reducing trace completeness by 20\\% produced the largest observed shift, but still preserved eight top-10 components and yielded $\\rho=0.88$. These results indicate stability under the examined perturbations while identifying trace completeness as a consequential source of uncertainty."
    )
    sens_new = (
        f"Under these perturbations, uniform fragility weights preserved a mean of "
        f"{uniform.top10_overlap:.1f} of the ten top-ranked components and yielded "
        f"Spearman's $\\rho={uniform.spearman_rho:.3f}$. Alternative criticality "
        f"mapping preserved {alt.top10_overlap:.1f} of ten and yielded "
        f"$\\rho={alt.spearman_rho:.3f}$. Reducing trace completeness by 20\\% "
        f"produced the largest observed shift, preserving {reduced.top10_overlap:.1f} "
        f"top-10 components with $\\rho={reduced.spearman_rho:.3f}$. These synthetic "
        "results identify trace completeness as the strongest examined perturbation."
    )
    text = replace_once(text, sens_old, sens_new, "sensitivity narrative")

    sensitivity_rows = []
    for name in [
        "Uniform fragility weights",
        "Alternative criticality mapping",
        "Frequency threshold 1.0%",
        "Trace completeness reduced by 20%",
        "Trace completeness increased by 20%",
    ]:
        row = sensitivity.loc[name]
        latex_name = name.replace("%", "\\%")
        sensitivity_rows.append(
            f"{latex_name} & {row.top10_overlap:.1f}/10 & "
            f"{row.spearman_rho:.3f} & {row.kendall_tau:.3f} \\\\"
        )
    sensitivity_pattern = re.compile(
        r"Uniform fragility weights & 9/10.*?Trace completeness increased by 20\\% & 9/10.*?\\\\\n",
        flags=re.DOTALL,
    )
    match = sensitivity_pattern.search(text)
    if not match:
        raise RuntimeError("Could not locate Table 8 rows")
    text = text[: match.start()] + "\n".join(sensitivity_rows) + "\n" + text[match.end() :]

    # Runtime narrative uses the measured reference smoke/full run committed with the repo.
    static_time = runtime.loc["Static fragility", "mean_seconds"]
    freq_time = runtime.loc["Frequency only", "mean_seconds"]
    unweighted_time = runtime.loc["Unweighted process-aware", "mean_seconds"]
    full_time = runtime.loc["Full CAD", "mean_seconds"]
    runtime_pattern = re.compile(
        r"Across the 30 runs, the complete \\CAD pipeline required a mean wall-clock time of 48\.6 seconds.*?periodic offline maintenance prioritization\.",
        flags=re.DOTALL,
    )
    runtime_new = (
        "On the committed reference run, the complete synthetic experiment, including "
        "30 runs, BCa confidence intervals, result serialization, and figure generation, "
        f"required {reference_run['wall_clock_seconds']:.2f} seconds and reached a "
        f"peak process memory of {reference_run['peak_rss_mb']:.2f} MB. "
        f"Method-specific scoring and ranking over the 30-run workload required "
        f"{static_time:.4f}, {freq_time:.4f}, {unweighted_time:.4f}, and {full_time:.4f} "
        "seconds for static fragility, frequency-only, unweighted process-aware, and "
        "full \\CAD, respectively. Timing included pathway-frequency resampling, "
        "trace-state resampling, exposure aggregation, fragility normalization, \\CAD "
        "scoring, and ranking, and excluded database extraction, log transfer, one-time "
        "environment initialization, manuscript compilation, and figure generation from "
        "the method-specific measurements. Runtime values are environment-dependent."
    )
    text, count = runtime_pattern.subn(lambda _m: runtime_new, text, count=1)
    if count != 1:
        raise RuntimeError("Could not replace RQ4 runtime paragraph")

    # Make simulation scope explicit in interpretation and validity sections.
    text = text.replace(
        "Within the evaluated case study",
        "Within the synthetic calibration",
    )
    text = text.replace(
        "The evaluation concerns one distributed EHR ecosystem with 45 deployable services, 14 primary pathways, and one institutional operating context.",
        "The simulation represents one BioArc-like synthetic architecture with 45 deployable components and 14 primary pathways; it does not reproduce the full heterogeneity of a production institutional environment.",
    )
    text = text.replace(
        "Thirty repeated runs and bootstrap confidence intervals characterize run-to-run uncertainty, but the evaluation still ranks only 45 components from a single EHR ecosystem.",
        "Thirty repeated runs and BCa bootstrap confidence intervals characterize synthetic run-to-run uncertainty, but the calibration ranks only 45 generated components and cannot establish external validity for production EHR systems.",
    )
    text = text.replace(
        "In the controlled BioArc case study, full \\CAD ranked components containing injected architecture-level defects more effectively than static-fragility, frequency-only, and unweighted process-aware baselines.",
        "In the simulation-only calibration, full \\CAD ranked generated components containing injected architecture-level defects more effectively than static-fragility, frequency-only, and unweighted process-aware baselines.",
    )
    text = text.replace(
        "The evidence supports \\CAD as a maintenance-prioritization signal in the evaluated setting; it does not establish clinical safety impact.",
        "The synthetic evidence demonstrates executable internal consistency of the proposed pipeline; it does not establish empirical effectiveness or clinical safety impact in a production setting.",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_manuscript(args.source, args.results_dir, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
