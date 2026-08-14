"""Machine-readable values used by the corrected V2 article.

The article reports rounded values, while this module preserves the full
precision committed in the result tables.  JSON serialization is deliberately
strict: non-finite pandas values (for example, the reference row's undefined
Cliff's delta) become ``null`` rather than the non-standard token ``NaN``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from .experiment import ExperimentResults


ARTICLE_REVISION = "V2 (2026-08-14)"
SUMMARY_FILES = {
    "method_summary": "method_summary.csv",
    "ablation_summary": "ablation_summary.csv",
    "sensitivity_summary": "sensitivity_summary.csv",
    "runtime_summary": "runtime_summary.csv",
}


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Return JSON-safe records, mapping pandas NaN values to JSON null."""
    return json.loads(frame.to_json(orient="records", double_precision=15))


def article_values_payload(results: ExperimentResults) -> dict[str, Any]:
    """Build the article-value snapshot from an in-memory experiment."""
    return {
        "schema_version": 1,
        "article_revision": ARTICLE_REVISION,
        "method_summary": _records(results.method_summary),
        "ablation_summary": _records(results.ablation_summary),
        "sensitivity_summary": _records(results.sensitivity_summary),
        "runtime_summary": _records(results.runtime_summary),
        "metadata": results.metadata,
    }


def committed_article_values_payload(results_dir: str | Path) -> dict[str, Any]:
    """Build the snapshot from the committed CSV and metadata artifacts."""
    results_path = Path(results_dir)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "article_revision": ARTICLE_REVISION,
    }
    for key, filename in SUMMARY_FILES.items():
        payload[key] = _records(pd.read_csv(results_path / filename))
    payload["metadata"] = json.loads(
        (results_path / "metadata.json").read_text(encoding="utf-8")
    )
    return payload


def _write_payload(payload: dict[str, Any], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_article_values(results: ExperimentResults, path: str | Path) -> None:
    """Write article values directly from an experiment result object."""
    _write_payload(article_values_payload(results), path)


def sync_committed_article_values(
    results_dir: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    """Synchronize ``article_values.json`` from committed result artifacts."""
    results_path = Path(results_dir)
    output = Path(output_path) if output_path else results_path / "article_values.json"
    _write_payload(committed_article_values_payload(results_path), output)
    return output
