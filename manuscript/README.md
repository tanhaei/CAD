# Manuscript files

- `V1_source_with_author_inputs.tex`: untouched uploaded source used as the transformation input.
- `V1_simulated.tex`: generated simulation-only manuscript with all `\AuthorInput` fields filled and empirical tables replaced by the committed synthetic outputs.
- `references.bib`: bibliography supplied with the manuscript.
- `figures/`: manuscript graphics and generated charts.

Regenerate `V1_simulated.tex` from repository root:

```bash
python scripts/update_manuscript.py \
  --source manuscript/V1_source_with_author_inputs.tex \
  --results-dir results \
  --output manuscript/V1_simulated.tex
```

The simulation-only file is not a substitute for verified production-study values.
