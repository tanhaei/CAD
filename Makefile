.PHONY: install experiment article-values quick test smoke clean

install:
	python -m pip install -e ".[dev]"

experiment:
	python scripts/run_experiment.py --config config/synthetic_experiment.json --output-dir results

article-values:
	python scripts/sync_article_values.py --results-dir results

quick:
	python scripts/run_experiment.py --quick --output-dir results/quick

test:
	python -m pytest -q

smoke: quick test

clean:
	rm -rf results/quick .pytest_cache
