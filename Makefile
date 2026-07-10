.PHONY: install experiment quick test smoke clean

install:
	python -m pip install -e ".[dev]"

experiment:
	python scripts/run_experiment.py --config config/synthetic_experiment.json --output-dir results --figures-dir figures
	python scripts/update_manuscript.py --source manuscript/V1_source_with_author_inputs.tex --results-dir results --output manuscript/V1_simulated.tex

quick:
	python scripts/run_experiment.py --quick --output-dir results/quick --figures-dir figures/quick

test:
	python -m pytest -q

smoke: quick test

clean:
	rm -rf results/quick figures/quick .pytest_cache
