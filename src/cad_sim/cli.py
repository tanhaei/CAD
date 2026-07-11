from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from .config import ExperimentConfig
from .experiment import run_experiment, write_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the reproducible synthetic CAD experiment."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="JSON configuration file. Defaults to built-in full settings.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use 3 runs, 20,000 activity records, and 1,000 bootstrap resamples.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    command_started_at = time.perf_counter()
    args = build_parser().parse_args(argv)
    config = ExperimentConfig.from_json(args.config) if args.config else ExperimentConfig()
    if args.quick:
        payload = config.to_dict()
        payload.update(
            {
                "n_runs": 3,
                "n_activity_records": 20_000,
                "bootstrap_resamples": 1_000,
            }
        )
        # Convert JSON-like lists back to tuples.
        for key in (
            "criticality_mapping",
            "alternative_criticality_mapping",
            "criticality_band_counts",
            "fragility_weights",
            "relevant_component_ids",
        ):
            payload[key] = tuple(payload[key])
        config = ExperimentConfig(**payload)

    results = run_experiment(config)
    write_results(results, args.output_dir)
    results.metadata["end_to_end_wall_clock_seconds"] = (
        time.perf_counter() - command_started_at
    )
    (args.output_dir / "metadata.json").write_text(
        json.dumps(results.metadata, indent=2),
        encoding="utf-8",
    )
    print(results.method_summary.to_string(index=False))
    print("\nAblation")
    print(results.ablation_summary.to_string(index=False))
    print("\nSensitivity")
    print(results.sensitivity_summary.to_string(index=False))
    print("\nRuntime")
    print(results.runtime_summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
