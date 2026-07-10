# Clinical-Architectural Debt (CAD): Synthetic Replication Package

[![CI](https://github.com/tanhaei/CAD/actions/workflows/ci.yml/badge.svg)](https://github.com/tanhaei/CAD/actions/workflows/ci.yml)

This repository provides an executable **synthetic replication and calibration** of the experiments described in the manuscript:

> **Clinical-Architectural Debt: Process-Aware Maintenance Prioritization for Distributed Electronic Health Record Systems**

Repository: **https://github.com/tanhaei/CAD**

## Scientific-integrity notice

The public repository does **not** contain the restricted BioArc operational logs, distributed traces, or the original private experiment outputs. The committed results were generated from a deterministic synthetic BioArc-like architecture. They are suitable for:

- checking the mathematical and software consistency of the CAD pipeline;
- reproducing the ranking, ablation, sensitivity, and runtime procedures;
- testing scripts, tables, and figure generation;
- serving as temporary values while the original empirical outputs are independently verified.

They must **not** be presented as measurements from the original BioArc deployment. The file `manuscript/V1_simulated.tex` is prominently marked as simulation-only.

## CAD model

For component \(C_j\), structural fragility is defined as

\[
F(C_j)=\sum_{r=1}^{5}\alpha_r z_r(C_j),
\]

where the synthetic experiment uses five indicators:

1. instability;
2. cycle participation;
3. recent defect density;
4. change coupling;
5. test-gap ratio.

The fixed synthetic weight vector is

\[
(0.20,\;0.15,\;0.25,\;0.20,\;0.20).
\]

Indicators are normalized with 5th–95th percentile winsorized min–max scaling. The component-level CAD score is

\[
\operatorname{CAD}(C_j)
=
F(C_j)
\sum_{P_i}
 f_i K(P_i)\,
 \mathbb{I}[C_j\in G(P_i)].
\]

## Synthetic experiment configuration

| Item | Value |
|---|---:|
| Activity-record-equivalent workload | 500,000 |
| Components | 45 |
| Primary pathways | 14 |
| Relevant components | 12 |
| Injected architecture-level defects | 120 |
| Evaluation runs | 30, seeds 42–71 |
| Criticality bands | 4 low, 5 moderate, 3 high, 2 critical |
| Criticality mapping | 0.25, 0.50, 0.75, 1.00 |
| Complete / partial / unmapped trace probability | 78.5% / 15.2% / 6.3% |
| Bootstrap | run-level BCa, 10,000 resamples |

Pathway counts and trace-link states are resampled in every run. Component relevance labels remain fixed.

## Committed synthetic results

### Ranking effectiveness

| Method | P@10 | R@10 | MAP | MRR |
|---|---:|---:|---:|---:|
| Static fragility | 0.57 | 0.47 | 0.51 | 0.50 |
| Frequency only | 0.43 | 0.36 | 0.36 | 0.51 |
| Unweighted process-aware | 0.65 | 0.54 | 0.59 | 0.63 |
| Full CAD | **0.93** | **0.77** | **0.91** | **0.97** |

The exact confidence intervals and run-level values are committed under `results/`.

### Ablation

| Configuration | P@10 | R@10 | MAP | Top-10 stability |
|---|---:|---:|---:|---:|
| Full CAD | 0.93 | 0.77 | 0.91 | 1.00 |
| Without criticality | 0.65 | 0.54 | 0.59 | 0.61 |
| Without frequency | 0.83 | 0.69 | 0.87 | 0.71 |
| Without fragility | 0.62 | 0.52 | 0.67 | 0.67 |
| Without trace exposure | 0.57 | 0.47 | 0.51 | 0.43 |

### Sensitivity

| Perturbation | Mean top-10 overlap | Spearman ρ | Kendall τ |
|---|---:|---:|---:|
| Uniform fragility weights | 9.9/10 | 0.998 | 0.980 |
| Alternative criticality mapping | 8.8/10 | 0.974 | 0.882 |
| Frequency threshold 1.0% | 9.9/10 | 0.999 | 0.993 |
| Trace completeness −20% | 7.7/10 | 0.868 | 0.764 |
| Trace completeness +20% | 9.9/10 | 0.988 | 0.978 |

## Quick start

Python 3.10 or newer is required.

```bash
git clone https://github.com/tanhaei/CAD.git
cd CAD
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the full 30-run experiment:

```bash
make experiment
```

Run a short smoke experiment:

```bash
make quick
```

Run the automated tests:

```bash
make test
```

Run both the quick experiment and tests:

```bash
make smoke
```

Equivalent direct command:

```bash
python scripts/run_experiment.py \
  --config config/synthetic_experiment.json \
  --output-dir results \
  --figures-dir figures
```

## Validation status

The delivered archive was tested before packaging:

- full experiment: **passed** (`make experiment`);
- automated test suite: **10 passed**;
- quick experiment smoke test: **passed**;
- one-pass LaTeX syntax/asset check: **passed**.

Detailed commands and reference timing are recorded in [`SMOKE_TEST.md`](SMOKE_TEST.md).

## Generated outputs

The experiment writes:

- `results/method_summary.csv`: Table 6-style ranking summary and BCa intervals;
- `results/run_metrics.csv`: every run/method observation;
- `results/ablation_summary.csv`: component-removal study;
- `results/sensitivity_summary.csv`: rank stability under perturbations;
- `results/runtime_summary.csv`: environment-dependent method runtimes;
- `results/component_ground_truth.csv`: relevant component and defect-count labels;
- `results/pathway_summary.csv`: synthetic pathway frequencies and criticality;
- `results/metadata.json`: seeds, platform, parameters, and reproducibility metadata;
- `figures/*.pdf` and `figures/*.png`: regenerated publication-oriented figures.

## Manuscript workflow

`manuscript/V1_source_with_author_inputs.tex` preserves the uploaded manuscript state. The reproducible simulation-only manuscript is generated with:

```bash
python scripts/update_manuscript.py \
  --source manuscript/V1_source_with_author_inputs.tex \
  --results-dir results \
  --output manuscript/V1_simulated.tex
```

`V1_simulated.tex` contains no live `\AuthorInput` fields and uses the committed synthetic outputs. It must be replaced with verified empirical results before journal submission.

The Mermaid sources for the architecture figures are in `diagrams/`. To render them with Mermaid CLI:

```bash
bash scripts/render_mermaid.sh
```

## Repository layout

```text
CAD/
├── config/                 # Full synthetic experiment configuration
├── results/                # Committed experiment outputs
├── scripts/                # Experiment, manuscript, and diagram commands
├── src/cad_sim/            # Installable Python package
├── tests/                  # Unit, reproducibility, and smoke tests
├── .github/workflows/      # GitHub Actions CI
├── CITATION.cff
├── LICENSE
├── Makefile
├── pyproject.toml
└── README.md
```

## Experimental definitions

- **P@10:** relevant components among the first ten positions divided by 10.
- **R@10:** relevant components among the first ten positions divided by the 12 relevant components.
- **Average precision:** precision evaluated at every relevant rank over the complete 45-component ranking.
- **MAP:** mean average precision across the 30 runs.
- **MRR:** mean reciprocal rank of the first relevant component.
- **Top-10 stability:** mean \(|T_{10}^{(a)}\cap T_{10}^{(full)}|/10\) across runs.
- **Cliff's delta:** compares run-level average precision for full CAD against each baseline; positive values favor full CAD.

## Ethics and data governance

The synthetic replication code processes no patient records. The manuscript's original-study declaration states:

> The external validation analyses were conducted on de-identified retrospective records obtained under institutional data-governance procedures. According to the determination of the Ilam University Ethics Committee, the requirement for individual informed consent was waived for this retrospective analysis.

This statement pertains to the original study, not to the generated synthetic dataset in this repository.

## Limitations

- The synthetic relevance labels are calibrated to produce separable but nontrivial rankings.
- The score-noise and tie/decoy probabilities are explicit simulation parameters rather than recovered production measurements.
- Runtime values depend on hardware, Python version, numerical libraries, and whether figures are generated.
- The repository demonstrates reproducibility of the computational protocol, not clinical validity or patient-safety impact.

## License and citation

Code is released under the MIT License. Citation metadata are provided in `CITATION.cff`.
