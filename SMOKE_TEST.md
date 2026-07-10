# Smoke-test report

Date: 2026-07-10

## Full experiment

Command:

```bash
make experiment
```

Result: **passed**

Reference environment reported by the generated metadata:

- Python 3.13.5
- Linux x86_64
- 56 logical CPUs visible to the container
- wall-clock time: 6.13 seconds
- maximum resident set size: 596,492 KiB (582.51 MiB)

The command regenerated all CSV/JSON results, four pairs of PDF/PNG charts, and `manuscript/V1_simulated.tex`.

## Automated tests

Command:

```bash
python -m pytest -q
```

Result:

```text
..........                                                               [100%]
10 passed in 4.43s
```

The tests cover metric definitions, normalization bounds, ground-truth counts, deterministic reproducibility, output-file generation, manuscript placeholder removal, and asset availability.

## Quick experiment

Command:

```bash
python scripts/run_experiment.py --quick \
  --output-dir results/quick \
  --figures-dir figures/quick
```

Result: **passed**. The quick profile completed three runs with 20,000 activity-record-equivalent observations and generated all expected outputs.

## LaTeX syntax smoke test

Command:

```bash
cd manuscript
pdflatex -interaction=nonstopmode -halt-on-error V1_simulated.tex
```

Result: **passed** for a one-pass syntax and asset check. Full bibliography resolution requires a normal BibTeX-enabled LaTeX environment.
