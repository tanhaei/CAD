#!/usr/bin/env bash
# Deprecated: the reduced package contains no Mermaid sources.
# Reproduce V3 vector diagrams with the supplied ReportLab authoring script.
set -euo pipefail
CAD_PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAD_FIGURE_SCRIPT="$CAD_PACKAGE_ROOT/../reviewer-revision/revise_figures.py"
if [[ ! -f "$CAD_FIGURE_SCRIPT" ]]; then
  echo "V3 figure authoring is supplied separately as reviewer-revision/revise_figures.py." >&2
  exit 2
fi
exec python "$CAD_FIGURE_SCRIPT"
