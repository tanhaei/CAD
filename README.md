# Clinical-Architectural Debt (CAD): Synthetic Evaluation Package

[![CI](https://github.com/tanhaei/CAD/actions/workflows/ci.yml/badge.svg)](https://github.com/tanhaei/CAD/actions/workflows/ci.yml)

This repository provides an executable synthetic evaluation of the method in:

> **Clinical-Architectural Debt: Process-Aware Maintenance Prioritization for Distributed Electronic Health Record Systems**

Repository: **https://github.com/tanhaei/CAD**

## Scope and scientific-integrity notice

The package contains no patient records, operational BioArc logs, or production traces. It generates a deterministic BioArc-like architecture and resamples pathway activity counts and trace-link states for 30 evaluation runs.

Version 0.2 removes the previous outcome-aware ranking calibration. Ground-truth relevance is now fixed in configuration before scoring, and neither relevance labels nor defect counts are passed to a ranking function. Consequently, the generated values are the direct outputs of the equations and declared perturbations; they are not forced to reproduce a target table.

The corrected article source uses the current generated results. Earlier article/PDF revisions may contain values produced by the removed calibration. In particular, static fragility is fixed across runs under the declared resampling design, so its run-level confidence interval is necessarily degenerate. See `CODE_ARTICLE_ALIGNMENT.md` for the correction record.

## Implemented model

Structural fragility is

\[
F(C_j)=\sum_{r=1}^{5}\alpha_r z_r(C_j),
\]

with 5th-95th percentile winsorized min-max normalization and the fixed weight vector

\[
(0.20,\;0.15,\;0.25,\;0.20,\;0.20).
\]

The full component score is

\[
\operatorname{CAD}(C_j)=F(C_j)\sum_{P_i}f_iK(P_i)\mathbb{I}[C_j\in G(P_i)].
\]

The pathway-component indicator is binary, as specified by the equation. Complete and partial mappings contribute observed membership because both contain at least one reliable runtime assignment; unmapped links contribute zero.

## Default experiment

| Item | Value |
|---|---:|
| Activity-record-equivalent workload | 500,000 |
| Components | 45 |
| Active primary pathways | 14 |
| Fixed relevant components | 12 |
| Injected architecture-level defects | 120 |
| Evaluation runs | 30, seeds 42-71 |
| Criticality bands | 4 low, 5 moderate, 3 high, 2 critical |
| Criticality mapping | 0.25, 0.50, 0.75, 1.00 |
| Complete / partial / unmapped trace probability | 78.5% / 15.2% / 6.3% |
| Bootstrap | run-level BCa, 10,000 resamples |

The configured Inductive Miner name, noise threshold, and case-level completeness value are retained as study metadata. This synthetic package starts from the 14 already-active variants; it does not recreate process discovery from the restricted raw event log.

## Installation and execution

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the complete experiment:

```bash
make experiment
```

Run the automated tests:

```bash
make test
```

Run the short experiment and tests together:

```bash
make smoke
```

Equivalent direct command:

```bash
python scripts/run_experiment.py \
  --config config/synthetic_experiment.json \
  --output-dir results
```

## Generated outputs

- `results/method_summary.csv`: ranking means, BCa intervals, MRR, and Cliff's delta;
- `results/run_metrics.csv`: every run-method observation;
- `results/ablation_summary.csv`: removal of criticality, frequency, fragility, and trace exposure;
- `results/sensitivity_summary.csv`: full-ranking agreement under five perturbations;
- `results/runtime_summary.csv`: environment-dependent method-specific timings;
- `results/component_ground_truth.csv`: fixed component relevance and defect counts;
- `results/defect_ground_truth.csv`: 120 defect-level records with category, pathway, criticality, and test ID;
- `results/pathway_summary.csv`: base pathway frequency and criticality;
- `results/run_pathway_summary.csv`: resampled counts and frequencies for every seed;
- `results/run_trace_coverage.csv`: realized complete, partial, and unmapped link proportions;
- `results/metadata.json`: configuration, environment, timing scope, and reproducibility metadata.

## Current regenerated results

### Ranking effectiveness

| Method | P@10 | R@10 | MAP | MRR |
|---|---:|---:|---:|---:|
| Static fragility | 0.60 | 0.50 | 0.55 | 0.50 |
| Frequency only | 0.49 | 0.41 | 0.53 | 0.95 |
| Unweighted process-aware | 0.68 | 0.56 | 0.81 | 1.00 |
| Full CAD | **0.99** | **0.82** | **0.96** | **1.00** |

### Ablation

| Configuration | P@10 | R@10 | MAP | Top-10 stability |
|---|---:|---:|---:|---:|
| Full CAD | 0.99 | 0.82 | 0.96 | 1.00 |
| Without criticality | 0.68 | 0.56 | 0.81 | 0.67 |
| Without frequency | 0.88 | 0.73 | 0.90 | 0.73 |
| Without fragility | 0.65 | 0.54 | 0.69 | 0.66 |
| Without trace exposure | 0.60 | 0.50 | 0.55 | 0.48 |

### Sensitivity

| Perturbation | Mean top-10 overlap | Spearman rho | Kendall tau |
|---|---:|---:|---:|
| Uniform fragility weights | 9.83/10 | 0.998 | 0.979 |
| Alternative criticality mapping | 8.30/10 | 0.969 | 0.871 |
| Frequency threshold 1.0% | 10.00/10 | 1.000 | 0.995 |
| Trace completeness reduced by 20% | 7.93/10 | 0.871 | 0.766 |
| Trace completeness increased by 20% | 9.97/10 | 0.991 | 0.980 |

## Evaluation definitions

- **P@10:** relevant components among the first ten positions divided by 10.
- **R@10:** relevant components among the first ten positions divided by the 12 relevant components.
- **Average precision:** precision at each relevant rank over the complete 45-component order.
- **MAP:** mean average precision across 30 runs.
- **MRR:** mean reciprocal rank of the first relevant component.
- **Top-10 stability:** mean proportion shared with the corresponding full-CAD top 10.
- **Cliff's delta:** run-level average-precision comparison between full CAD and a baseline.

## Limitations

- This is a synthetic internal-consistency evaluation, not evidence of clinical safety or production effectiveness.
- The active pathway set is generated directly; raw-log extraction and Inductive Miner execution are outside this public package.
- Trace states are sampled over the synthetic pathway-component map rather than production activity spans.
- Runtime values depend on the execution environment.

Code is released under the MIT License. Citation metadata are provided in `CITATION.cff`.
