#!/usr/bin/env python
"""Collect official seed-level metrics listed in the frozen registry.

This is a conservative collector for local full workspaces. It reads existing
metrics tables and does not train models.

Usage:
  python scripts/collect_seed_metrics.py --project-root . --registry results/source_data/PAPER1_FROZEN_MODEL_REGISTRY.tsv --output-dir results/source_data
  python scripts/collect_seed_metrics.py --raw-metrics results/source_data/PAPER1_7MODEL_RAW_SEED_METRICS.tsv --output-dir results/source_data
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--registry", default="results/source_data/PAPER1_FROZEN_MODEL_REGISTRY.tsv")
    parser.add_argument("--raw-metrics", default="results/source_data/PAPER1_7MODEL_RAW_SEED_METRICS.tsv")
    parser.add_argument("--output-dir", default="results/source_data")
    parser.add_argument("--allow-missing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    registry = Path(args.registry)
    if not registry.is_absolute():
        registry = root / registry
    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    reg = pd.read_csv(registry, sep="\t")
    raw_metrics = Path(args.raw_metrics)
    if not raw_metrics.is_absolute():
        raw_metrics = root / raw_metrics

    if "source_file" not in reg.columns:
        if not raw_metrics.exists():
            print(f"ERROR registry has no source_file column and raw metrics are missing: {raw_metrics}")
            return 1
        out = pd.read_csv(raw_metrics, sep="\t")
        expected_models = set(reg["model_name"].astype(str))
        observed_models = set(out["model_name"].astype(str)) if "model_name" in out.columns else set()
        missing_models = sorted(expected_models - observed_models)
        if missing_models:
            print(f"WARN raw metrics missing registry model(s): {missing_models}")
            if not args.allow_missing:
                return 1
        out_path = out_dir / "COLLECTED_OFFICIAL_SEED_METRICS.tsv"
        out.to_csv(out_path, sep="\t", index=False)
        print(f"Saved curated raw seed metrics copy: {out_path}")
        return 0

    rows = []
    missing = []
    for rec in reg.to_dict(orient="records"):
        source_file = rec.get("source_file")
        if not source_file or pd.isna(source_file):
            missing.append((rec.get("model_name"), "missing source_file in registry"))
            continue
        path = root / str(source_file)
        if not path.exists():
            missing.append((rec.get("model_name"), str(path)))
            continue
        table = pd.read_csv(path, sep="\t")
        table.insert(0, "source_file", str(source_file))
        table.insert(0, "source_root", str(rec.get("formal_root", "")))
        table.insert(0, "task_type", str(rec.get("task_type", "")))
        table.insert(0, "model_name", str(rec.get("model_name", "")))
        rows.append(table)

    if missing:
        for model, path in missing:
            print(f"WARN missing metrics for {model}: {path}")
        if not args.allow_missing:
            return 1

    if not rows:
        print("No metrics collected.")
        return 0 if args.allow_missing else 1

    out = pd.concat(rows, ignore_index=True)
    out_path = out_dir / "COLLECTED_OFFICIAL_SEED_METRICS.tsv"
    out.to_csv(out_path, sep="\t", index=False)
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
