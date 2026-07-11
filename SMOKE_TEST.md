# Validation report

Date: 2026-07-10

## Full experiment

Command:

```bash
make experiment
```

Result: **passed**. The command completed 30 runs (seeds 42-71), used 500,000 activity-record-equivalent observations per run, computed BCa intervals with 10,000 resamples, and regenerated every CSV/JSON file under `results/`.

Reference in-process measurements recorded in `results/metadata.json`:

- end-to-end time through result serialization: **2.08 s**;
- peak process memory: **133.54 MB**.

## Automated tests

Command:

```bash
python -m pytest -q
```

The suite checks article configuration, CAD equation arithmetic, binary trace membership, fixed and score-independent ground truth, ranking metrics, ablation/sensitivity shapes, committed-result integrity, deterministic reproduction, and output serialization.

Result: **19 passed**.

## Quick experiment

Command:

```bash
python scripts/run_experiment.py --quick --output-dir results/quick
```

The quick profile uses three runs, 20,000 observations per run, and 1,000 bootstrap resamples. It must generate the same output schema as the full experiment.

Result: **passed**.
