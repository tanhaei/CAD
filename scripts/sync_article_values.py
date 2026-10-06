#!/usr/bin/env python3
"""Synchronize the machine-readable V3 article values from committed results."""

from __future__ import annotations

import argparse
from pathlib import Path

from cad_sim.article import sync_committed_article_values
from cad_sim.manuscript import write_manuscript_results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Directory containing the committed CSV and metadata artifacts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: RESULTS_DIR/article_values.json).",
    )
    args = parser.parse_args(argv)
    output = sync_committed_article_values(args.results_dir, args.output)
    write_manuscript_results(args.results_dir)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
