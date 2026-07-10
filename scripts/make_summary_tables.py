#!/usr/bin/env python
"""Create mean/sd summary tables from seed-level metrics.

Usage:
  python scripts/make_summary_tables.py --raw-metrics results/source_data/PAPER1_7MODEL_RAW_SEED_METRICS.tsv --output-dir results/source_data
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_METRICS = ["AUROC", "AUPR", "ACC", "F1", "MCC", "Brier", "ECE", "NLL", "loss"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-metrics", default="results/source_data/PAPER1_7MODEL_RAW_SEED_METRICS.tsv")
    parser.add_argument("--output-dir", default="results/source_data")
    parser.add_argument("--output-name", default="PAPER1_7MODEL_SUMMARY_MEAN_SD_REBUILT.tsv")
    return parser.parse_args()


def find_col(df: pd.DataFrame, name: str) -> str | None:
    lower = {str(c).lower(): c for c in df.columns}
    return lower.get(name.lower())


def main() -> int:
    args = parse_args()
    raw_path = Path(args.raw_metrics)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(raw_path, sep="\t")

    group_cols = [c for c in ["model_name", "task_type", "dataset", "setting"] if c in df.columns]
    if not group_cols:
        raise SystemExit("No grouping columns found.")

    rows = []
    for keys, g in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_cols, keys))
        row["n_success"] = int(len(g))
        for metric in DEFAULT_METRICS:
            col = find_col(g, metric)
            if col is None:
                continue
            vals = pd.to_numeric(g[col], errors="coerce").dropna()
            row[f"{metric}_mean"] = vals.mean() if len(vals) else pd.NA
            row[f"{metric}_sd"] = vals.std(ddof=1) if len(vals) > 1 else pd.NA
        rows.append(row)

    out = pd.DataFrame(rows)
    out_path = out_dir / args.output_name
    out.to_csv(out_path, sep="\t", index=False)
    print(f"Saved: {out_path}")
    print(out.head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

