#!/usr/bin/env bash
# Minimal packaging smoke test. This does not train models or run formal experiments.
#
# Usage:
#   bash scripts/run_smoke_test.sh

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

cd "$PROJECT_ROOT"

python scripts/check_environment.py --warn-only
python scripts/verify_official_assets.py --project-root "$PROJECT_ROOT" --allow-missing
python scripts/make_summary_tables.py \
  --raw-metrics results/source_data/PAPER1_7MODEL_RAW_SEED_METRICS.tsv \
  --output-dir results/source_data \
  --output-name SMOKE_SUMMARY_REBUILT.tsv

rm -f results/source_data/SMOKE_SUMMARY_REBUILT.tsv

echo "Packaging smoke test PASS"
