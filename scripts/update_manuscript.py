#!/usr/bin/env python3
"""Refresh V3 computed inputs without rewriting scientific claims.

Only a V3 source containing the shared result-input contract is accepted.
Historical draft rewriting and invented timing fallbacks are not supported.
"""
from pathlib import Path
import argparse
from cad_sim.manuscript import write_manuscript_results, audit_manuscript


def build_manuscript(source_path: Path, results_dir: Path, output_path: Path) -> None:
    text = source_path.read_text()
    contract = r"\input{git/results/manuscript_results.tex}"
    if contract not in text:
        raise ValueError("Expected V3 shared-result input; V1/V2 templates are unsupported")
    expected_input = output_path.parent / "git/results/manuscript_results.tex"
    if expected_input.resolve() != (results_dir / "manuscript_results.tex").resolve():
        raise ValueError("results_dir must match the computed input used by the output manuscript")
    write_manuscript_results(results_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.resolve() != output_path.resolve():
        output_path.write_text(text)
    audit_manuscript(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_manuscript(args.source, args.results_dir, args.output)
    print(f"Updated computed inputs for {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
