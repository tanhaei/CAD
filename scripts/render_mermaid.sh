#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/manuscript/figures"

render() {
  local input="$1"
  local output="$2"
  npx -y @mermaid-js/mermaid-cli \
    --input "$ROOT/diagrams/$input" \
    --output "$ROOT/manuscript/figures/$output" \
    --backgroundColor transparent
}

render fig01_bioarc_overview.mmd fig01_bioarc_overview.svg
render fig02_cad_pipeline.mmd fig02_cad_pipeline.svg
render figA1_bioarc_external_integrations.mmd figA1_bioarc_external_integrations.svg
render figA2_observability_sync.mmd figA2_observability_sync.svg

echo "Rendered Mermaid diagrams to manuscript/figures/."
