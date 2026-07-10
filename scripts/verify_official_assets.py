#!/usr/bin/env python
"""Verify Paper1 official frozen/fixed-final result assets.

Usage:
  python scripts/verify_official_assets.py --project-root .
  python scripts/verify_official_assets.py --project-root . --allow-missing
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_REGISTRY = "results/source_data/PAPER1_FROZEN_MODEL_REGISTRY.tsv"
EXCLUDED_TERMS = ("smoke", "pilot", "failed", "partial", "stale", "recovered", "tmp", "temp")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Project root containing official result roots.")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY, help="Frozen model registry TSV.")
    parser.add_argument("--allow-missing", action="store_true", help="Warn instead of failing when full formal roots are absent.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = root / registry_path
    if not registry_path.exists():
        print(f"ERROR missing registry: {registry_path}")
        return 1

    df = pd.read_csv(registry_path, sep="\t")
    required_cols = {"model_name", "formal_root", "status_marker", "use_for_source_data"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        print(f"ERROR registry missing columns: {sorted(missing_cols)}")
        return 1

    failures = 0
    for row in df.to_dict(orient="records"):
        model = row["model_name"]
        formal_root = root / str(row["formal_root"])
        status_marker = root / str(row["status_marker"])
        use = str(row.get("use_for_source_data", "")).upper()
        print(f"\n[{model}]")
        print(f"formal_root: {formal_root}")
        if use != "YES":
            failures += 1
            print(f"ERROR use_for_source_data is not YES: {use}")
        for label, path in [("formal_root", formal_root), ("status_marker", status_marker)]:
            if path.exists():
                print(f"OK {label}: {path}")
            else:
                msg = f"MISSING {label}: {path}"
                if args.allow_missing:
                    print(f"WARN {msg}")
                else:
                    print(f"ERROR {msg}")
                    failures += 1

    bad_registry_rows = df[df["formal_root"].astype(str).str.contains("|".join(EXCLUDED_TERMS), case=False, regex=True, na=False)]
    if not bad_registry_rows.empty:
        print("\nERROR registry formal roots contain excluded terms:")
        print(bad_registry_rows[["model_name", "formal_root"]].to_string(index=False))
        failures += len(bad_registry_rows)

    bisgtar = df[df["model_name"].astype(str).str.contains("Bi-SGTAR", case=False, regex=False, na=False)]
    if bisgtar.empty or "bisgtar_masked_pairloss_fixedfinal_20260706" not in str(bisgtar.iloc[0]["formal_root"]):
        print("ERROR Bi-SGTAR registry row is not the fixed-final E200 official root.")
        failures += 1
    else:
        print("\nOK Bi-SGTAR uses fixed-final E200 official root.")

    if failures:
        print(f"\nVerification completed with {failures} issue(s).")
        return 1
    print("\nVerification PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

