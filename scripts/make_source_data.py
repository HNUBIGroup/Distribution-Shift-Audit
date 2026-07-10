#!/usr/bin/env python
"""Stage curated Paper1 source-data assets for GitHub/release packaging.

Usage:
  python scripts/make_source_data.py --project-root . --output-dir results/source_data
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_SOURCE_DIR = "outputs/paper1_data_refresh_20260710"
FILES = {
    "PAPER1_FROZEN_MODEL_REGISTRY.tsv": "PAPER1_FROZEN_MODEL_REGISTRY.tsv",
    "PAPER1_7MODEL_AUDIT_SUMMARY.tsv": "PAPER1_7MODEL_AUDIT_SUMMARY.tsv",
    "PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv": "PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv",
    "PAPER1_7MODEL_RAW_SEED_METRICS.tsv": "PAPER1_7MODEL_RAW_SEED_METRICS.tsv",
    "Fig4_similarity_stratified_final.tsv": "Fig4_similarity_stratified_final.tsv",
    "Fig4_similarity_stratified_seed_metrics.tsv": "Fig4_similarity_stratified_seed_metrics.tsv",
    "Fig5_CDA_random_baseline_loss_final.tsv": "Fig5_CDA_random_baseline_loss_final.tsv",
    "Source_Data_Paper1_20260710_with_Fig4_similarity.xlsx": "Source_Data_Paper1_20260710.xlsx",
    "Supplementary_Data_Paper1_20260710.xlsx": "Supplementary_Data_Paper1_20260710.xlsx",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", default="results/source_data")
    parser.add_argument("--allow-missing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    source_dir = Path(args.source_dir)
    if not source_dir.is_absolute():
        source_dir = root / source_dir
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = []
    for src_name, dst_name in FILES.items():
        src = source_dir / src_name
        dst = output_dir / dst_name
        if not src.exists():
            missing.append(str(src))
            continue
        shutil.copy2(src, dst)
        print(f"Copied: {src} -> {dst}")

    if missing:
        for path in missing:
            print(f"WARN missing source-data asset: {path}")
        if not args.allow_missing:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

