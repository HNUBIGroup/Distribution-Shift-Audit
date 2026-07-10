#!/usr/bin/env python
"""Recompute Paper1 Fig.4b/c similarity-stratified source data.

This script is intentionally read-only for formal run directories. It uses
final ISG drug_cold predictions plus provenance-verified drug SMILES assets.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from sklearn.metrics import average_precision_score, roc_auc_score


ROOT = Path(__file__).resolve().parents[1]
FINAL_ROOT = ROOT / "formal_runs" / "isg_clean_fixedfinal_20260706"
RUN_ROOT = FINAL_ROOT / "04_formal_runs"
OUT_DIR = ROOT / "outputs" / "paper1_data_refresh_20260710"
SOURCE_XLSX = OUT_DIR / "Source_Data_Paper1_20260710.xlsx"
SOURCE_XLSX_WITH_FIG4 = OUT_DIR / "Source_Data_Paper1_20260710_with_Fig4_similarity.xlsx"

DATASETS = ("MDR", "MDS")
SEEDS = tuple(range(25))
BINS = ("High", "Medium", "Low")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_col(df: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    lower = {str(c).lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    raise KeyError(f"Missing one of {candidates}; available={list(df.columns)}")


def sim_bin(x: float) -> str:
    if pd.isna(x):
        return "Missing"
    if x >= 0.70:
        return "High"
    if x >= 0.40:
        return "Medium"
    return "Low"


def safe_metric_values(y_true: pd.Series, y_score: pd.Series) -> dict[str, float]:
    y = y_true.astype(int).to_numpy()
    s = y_score.astype(float).to_numpy()
    n = len(y)
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    prevalence = float(n_pos / n) if n else math.nan

    out = {
        "n_test_pairs": int(n),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "prevalence": prevalence,
        "AUROC": math.nan,
        "AUPR_raw": math.nan,
        "AUPR_normalized": math.nan,
    }
    if n == 0 or n_pos == 0 or n_neg == 0:
        return out

    auroc = float(roc_auc_score(y, s))
    aupr = float(average_precision_score(y, s))
    norm_aupr = float((aupr - prevalence) / (1.0 - prevalence)) if prevalence < 1.0 else math.nan
    out.update({"AUROC": auroc, "AUPR_raw": aupr, "AUPR_normalized": norm_aupr})
    return out


def mean_or_nan(values: pd.Series) -> float:
    vals = pd.to_numeric(values, errors="coerce").dropna()
    return float(vals.mean()) if len(vals) else math.nan


def sd_or_nan(values: pd.Series) -> float:
    vals = pd.to_numeric(values, errors="coerce").dropna()
    return float(vals.std(ddof=1)) if len(vals) > 1 else math.nan


def fmt4(x: float) -> str:
    if pd.isna(x):
        return "NA"
    return f"{float(x):.4f}"


def markdown_table(df: pd.DataFrame) -> str:
    text_df = df.copy()
    text_df = text_df.where(pd.notna(text_df), "")
    headers = [str(c) for c in text_df.columns]
    rows = [[str(v) for v in row] for row in text_df.to_numpy()]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_missing_asset_report(rows: list[dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = OUT_DIR / "MISSING_ASSET_REPORT.md"
    df = pd.DataFrame(rows)
    lines = [
        "# MISSING_ASSET_REPORT",
        "",
        "Fig.4b/c similarity-stratified source data was not generated because required assets were missing or invalid.",
        "",
    ]
    if not df.empty:
        lines.append(markdown_table(df))
        lines.append("")
    report.write_text("\n".join(lines), encoding="utf-8")
    df.to_csv(OUT_DIR / "MISSING_ASSET_REPORT.tsv", sep="\t", index=False)
    print(f"MISSING_ASSET_REPORT: {report}")


def load_drug_assets() -> tuple[dict[str, pd.DataFrame], dict[str, dict[int, object]], pd.DataFrame]:
    missing: list[dict[str, str]] = []
    drug_tables: dict[str, pd.DataFrame] = {}
    fps_by_dataset: dict[str, dict[int, object]] = {}
    provenance_rows: list[dict[str, object]] = []

    for dataset in DATASETS:
        input_prov = RUN_ROOT / dataset / "drug_cold" / "seed_0" / "input_provenance.json"
        if not input_prov.exists():
            missing.append({"dataset": dataset, "asset": str(input_prov), "reason": "missing input_provenance.json"})
            continue

        prov = json.loads(input_prov.read_text(encoding="utf-8"))
        hashes = prov.get("feature_asset_hashes", {})
        drug_candidates = [Path(p) for p in hashes if f"/data/{dataset}/drug_" in p and Path(p).suffix.lower() in {".xlsx", ".xls"}]
        if not drug_candidates:
            missing.append({"dataset": dataset, "asset": str(input_prov), "reason": "no drug Excel asset in feature_asset_hashes"})
            continue

        drug_path = drug_candidates[0]
        expected_hash = hashes[str(drug_path)]
        if not drug_path.exists():
            missing.append({"dataset": dataset, "asset": str(drug_path), "reason": "drug Excel asset missing"})
            continue

        actual_hash = sha256_file(drug_path)
        if actual_hash != expected_hash:
            missing.append({
                "dataset": dataset,
                "asset": str(drug_path),
                "reason": f"sha256 mismatch expected={expected_hash} actual={actual_hash}",
            })
            continue

        df = pd.read_excel(drug_path)
        drugbank_col = find_col(df, ("DrugBank_ID", "DrugBank ID", "drugbank_id", "DrugBank"))
        smiles_col = find_col(df, ("SMILES", "smiles"))
        df = df[[drugbank_col, smiles_col]].rename(columns={drugbank_col: "DrugBank_ID", smiles_col: "SMILES"}).copy()
        df.insert(0, "drug_index", range(len(df)))
        df.insert(0, "dataset", dataset)

        fps: dict[int, object] = {}
        bad_smiles: list[int] = []
        for row in df.itertuples(index=False):
            mol = Chem.MolFromSmiles(str(row.SMILES))
            if mol is None:
                bad_smiles.append(int(row.drug_index))
                fps[int(row.drug_index)] = None
                continue
            fps[int(row.drug_index)] = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)

        if bad_smiles:
            missing.append({
                "dataset": dataset,
                "asset": str(drug_path),
                "reason": "unparseable SMILES at drug_index " + ",".join(map(str, bad_smiles[:20])),
            })
            continue

        drug_tables[dataset] = df
        fps_by_dataset[dataset] = fps
        provenance_rows.append({
            "dataset": dataset,
            "drug_asset_path": str(drug_path),
            "drug_asset_sha256": actual_hash,
            "n_drugs": len(df),
            "fingerprint": "RDKit Morgan radius=2 nBits=2048",
            "provenance_file": str(input_prov),
        })

    if missing:
        write_missing_asset_report(missing)
        raise SystemExit(2)

    return drug_tables, fps_by_dataset, pd.DataFrame(provenance_rows)


def compute_similarity_data(
    drug_tables: dict[str, pd.DataFrame],
    fps_by_dataset: dict[str, dict[int, object]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    seed_rows: list[dict[str, object]] = []
    drug_rows: list[dict[str, object]] = []

    for dataset in DATASETS:
        all_drugs = set(drug_tables[dataset]["drug_index"].astype(int))
        drug_meta = drug_tables[dataset].set_index("drug_index").to_dict(orient="index")

        for seed in SEEDS:
            seed_dir = RUN_ROOT / dataset / "drug_cold" / f"seed_{seed}"
            pred_path = seed_dir / "predictions.tsv"
            split_meta_path = seed_dir / "split_metadata.json"
            if not pred_path.exists() or not split_meta_path.exists():
                raise FileNotFoundError(f"Missing final prediction or split metadata for {dataset} seed {seed}")

            pred = pd.read_csv(pred_path, sep="\t")
            split_meta = json.loads(split_meta_path.read_text(encoding="utf-8"))
            if int(split_meta.get("test_rows", -1)) != len(pred):
                raise ValueError(f"Prediction row count does not match split_metadata for {dataset} seed {seed}")
            if str(split_meta.get("dataset")) != dataset or str(split_meta.get("setting")) != "drug_cold":
                raise ValueError(f"Unexpected split metadata dataset/setting for {dataset} seed {seed}")

            test_drugs = set(pred["drug_index"].astype(int).unique())
            train_drugs = all_drugs - test_drugs
            train_fps = {d: fps_by_dataset[dataset][d] for d in sorted(train_drugs)}

            sim_records = []
            for test_drug in sorted(test_drugs):
                test_fp = fps_by_dataset[dataset][test_drug]
                best_sim = -1.0
                nearest_train_drug = None
                for train_drug, train_fp in train_fps.items():
                    s = float(DataStructs.TanimotoSimilarity(test_fp, train_fp))
                    if s > best_sim:
                        best_sim = s
                        nearest_train_drug = train_drug
                similarity = best_sim if best_sim >= 0.0 else math.nan
                bin_name = sim_bin(similarity)
                rec = {
                    "dataset": dataset,
                    "seed": seed,
                    "drug_index": test_drug,
                    "DrugBank_ID": drug_meta[test_drug]["DrugBank_ID"],
                    "SMILES": drug_meta[test_drug]["SMILES"],
                    "max_train_drug_tanimoto": similarity,
                    "similarity_bin": bin_name,
                    "nearest_train_drug_index": nearest_train_drug,
                    "nearest_train_DrugBank_ID": drug_meta[nearest_train_drug]["DrugBank_ID"] if nearest_train_drug is not None else "",
                    "n_train_drugs": len(train_drugs),
                    "n_test_drugs_seed": len(test_drugs),
                    "prediction_file": str(pred_path.relative_to(ROOT)),
                    "split_metadata_file": str(split_meta_path.relative_to(ROOT)),
                    "train_sha256": split_meta.get("train_sha256", ""),
                    "test_sha256": split_meta.get("test_sha256", ""),
                }
                sim_records.append(rec)
                drug_rows.append(rec)

            sim_df = pd.DataFrame(sim_records)
            merged = pred.merge(sim_df[["dataset", "seed", "drug_index", "max_train_drug_tanimoto", "similarity_bin"]], on=["dataset", "seed", "drug_index"], how="left")
            if merged["similarity_bin"].isna().any():
                raise ValueError(f"Missing similarity bin after merge for {dataset} seed {seed}")

            for bin_name in BINS:
                g = merged[merged["similarity_bin"] == bin_name]
                m = safe_metric_values(g["y_true"], g["y_prob"])
                m.update({
                    "dataset": dataset,
                    "setting": "drug_cold",
                    "seed": seed,
                    "similarity_bin": bin_name,
                    "n_test_drugs": int(g["drug_index"].nunique()),
                    "mean_max_train_drug_tanimoto": mean_or_nan(g["max_train_drug_tanimoto"]),
                    "valid_metric_seed": bool(not pd.isna(m["AUROC"]) and not pd.isna(m["AUPR_raw"])),
                })
                seed_rows.append(m)

    return pd.DataFrame(seed_rows), pd.DataFrame(drug_rows)


def summarize(seed_metrics: pd.DataFrame) -> pd.DataFrame:
    high_low_counts: dict[str, dict[str, int]] = {}
    for dataset, g in seed_metrics.groupby("dataset"):
        by_bin = g.pivot(index="seed", columns="similarity_bin", values=["AUROC", "AUPR_raw"])
        counts: dict[str, int] = {}
        for metric, out_name in [("AUROC", "AUROC"), ("AUPR_raw", "AUPR_raw")]:
            high = by_bin[(metric, "High")]
            low = by_bin[(metric, "Low")]
            valid = high.notna() & low.notna()
            counts[f"high_gt_low_count_{out_name}"] = int((high[valid] > low[valid]).sum())
            counts[f"high_low_valid_seed_count_{out_name}"] = int(valid.sum())
        high_low_counts[dataset] = counts

    rows: list[dict[str, object]] = []
    for dataset in DATASETS:
        for bin_name in BINS:
            g = seed_metrics[(seed_metrics["dataset"] == dataset) & (seed_metrics["similarity_bin"] == bin_name)].copy()
            valid = g[g["valid_metric_seed"]]
            row = {
                "dataset": dataset,
                "setting": "drug_cold",
                "similarity_bin": bin_name,
                "valid_seed_count": int(valid["seed"].nunique()),
                "seed_count_with_bin": int((g["n_test_pairs"] > 0).sum()),
                "mean_AUROC": mean_or_nan(g["AUROC"]),
                "sd_AUROC": sd_or_nan(g["AUROC"]),
                "mean_raw_AUPR": mean_or_nan(g["AUPR_raw"]),
                "sd_raw_AUPR": sd_or_nan(g["AUPR_raw"]),
                "mean_normalized_AUPR": mean_or_nan(g["AUPR_normalized"]),
                "sd_normalized_AUPR": sd_or_nan(g["AUPR_normalized"]),
                "prevalence_mean": mean_or_nan(g["prevalence"]),
                "prevalence_sd": sd_or_nan(g["prevalence"]),
                "n_test_drugs_mean": mean_or_nan(g["n_test_drugs"]),
                "n_test_drugs_sd": sd_or_nan(g["n_test_drugs"]),
                "n_test_pairs_mean": mean_or_nan(g["n_test_pairs"]),
                "n_test_pairs_sd": sd_or_nan(g["n_test_pairs"]),
                "mean_max_train_drug_tanimoto": mean_or_nan(g["mean_max_train_drug_tanimoto"]),
            }
            row.update(high_low_counts[dataset])
            rows.append(row)

    return pd.DataFrame(rows)


def write_summary_md(summary: pd.DataFrame, provenance: pd.DataFrame) -> None:
    md = OUT_DIR / "Fig4_similarity_stratified_final_summary.md"
    lines = [
        "# Fig.4b/c similarity-stratified final source data",
        "",
        "- Scope: Article1 / Paper1 only; ISG final PASS root `formal_runs/isg_clean_fixedfinal_20260706`.",
        "- Predictions: `04_formal_runs/{MDR,MDS}/drug_cold/seed_*/predictions.tsv`, seeds 0..24.",
        "- Similarity bins: High >= 0.70, Medium 0.40-<0.70, Low < 0.40 max train-drug Tanimoto.",
        "- Fingerprints: RDKit Morgan radius=2, nBits=2048 from provenance-verified drug SMILES Excel assets.",
        "- Normalized AUPR: `(raw AUPR - prevalence) / (1 - prevalence)`, computed per seed/bin then summarized.",
        "",
        "## Asset provenance",
        "",
        markdown_table(provenance),
        "",
        "## Visio-ready values, 4 decimals",
        "",
    ]

    visio_cols = [
        "dataset",
        "similarity_bin",
        "valid_seed_count",
        "mean_AUROC",
        "sd_AUROC",
        "mean_raw_AUPR",
        "sd_raw_AUPR",
        "mean_normalized_AUPR",
        "sd_normalized_AUPR",
        "prevalence_mean",
        "n_test_drugs_mean",
        "n_test_pairs_mean",
        "high_gt_low_count_AUROC",
        "high_gt_low_count_AUPR_raw",
    ]
    visio = summary[visio_cols].copy()
    for c in visio.columns:
        if c not in {"dataset", "similarity_bin", "valid_seed_count", "high_gt_low_count_AUROC", "high_gt_low_count_AUPR_raw"}:
            visio[c] = visio[c].map(fmt4)
    lines.append(markdown_table(visio))
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")


def write_excel_outputs(summary: pd.DataFrame, seed_metrics: pd.DataFrame, drug_bins: pd.DataFrame, provenance: pd.DataFrame) -> None:
    xlsx = OUT_DIR / "Fig4_similarity_stratified_source_data.xlsx"
    readme = pd.DataFrame([
        {"field": "scope", "value": "Article1/Paper1 Fig.4b/c similarity-stratified source data"},
        {"field": "final_root", "value": str(FINAL_ROOT.relative_to(ROOT))},
        {"field": "normalized_AUPR", "value": "(raw AUPR - prevalence) / (1 - prevalence), per seed/bin"},
        {"field": "bins", "value": "High >=0.70; Medium 0.40-<0.70; Low <0.40"},
    ])
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        readme.to_excel(writer, sheet_name="README", index=False)
        summary.to_excel(writer, sheet_name="Fig4_summary", index=False)
        seed_metrics.to_excel(writer, sheet_name="Fig4_seed_metrics", index=False)
        drug_bins.to_excel(writer, sheet_name="Fig4_drug_bins", index=False)
        provenance.to_excel(writer, sheet_name="asset_provenance", index=False)

    if SOURCE_XLSX.exists():
        with pd.ExcelFile(SOURCE_XLSX) as xl:
            sheets = {name: xl.parse(name) for name in xl.sheet_names}
        sheets["Fig4_external_or_similarity"] = summary
        sheets["Fig4_similarity_seed_metrics"] = seed_metrics
        sheets["Fig4_similarity_drug_bins"] = drug_bins
        sheets["Fig4_asset_provenance"] = provenance
        with pd.ExcelWriter(SOURCE_XLSX_WITH_FIG4, engine="openpyxl") as writer:
            for name, df in sheets.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
    else:
        shutil.copy2(xlsx, SOURCE_XLSX_WITH_FIG4)


def print_visio(summary: pd.DataFrame) -> None:
    cols = [
        "dataset",
        "similarity_bin",
        "valid_seed_count",
        "mean_AUROC",
        "sd_AUROC",
        "mean_raw_AUPR",
        "sd_raw_AUPR",
        "mean_normalized_AUPR",
        "sd_normalized_AUPR",
        "prevalence_mean",
        "n_test_drugs_mean",
        "n_test_pairs_mean",
        "high_gt_low_count_AUROC",
        "high_low_valid_seed_count_AUROC",
        "high_gt_low_count_AUPR_raw",
        "high_low_valid_seed_count_AUPR_raw",
    ]
    out = summary[cols].copy()
    for c in out.columns:
        if c not in {
            "dataset",
            "similarity_bin",
            "valid_seed_count",
            "high_gt_low_count_AUROC",
            "high_low_valid_seed_count_AUROC",
            "high_gt_low_count_AUPR_raw",
            "high_low_valid_seed_count_AUPR_raw",
        }:
            out[c] = out[c].map(fmt4)
    print("\nFig.4b/c Visio-ready final values (4 decimals)")
    print(out.to_string(index=False))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    drug_tables, fps_by_dataset, provenance = load_drug_assets()
    seed_metrics, drug_bins = compute_similarity_data(drug_tables, fps_by_dataset)
    summary = summarize(seed_metrics)

    summary_tsv = OUT_DIR / "Fig4_similarity_stratified_final.tsv"
    summary.to_csv(summary_tsv, sep="\t", index=False)
    seed_metrics.to_csv(OUT_DIR / "Fig4_similarity_stratified_seed_metrics.tsv", sep="\t", index=False)
    drug_bins.to_csv(OUT_DIR / "Fig4_similarity_stratified_drug_bins.tsv", sep="\t", index=False)
    provenance.to_csv(OUT_DIR / "Fig4_similarity_stratified_asset_provenance.tsv", sep="\t", index=False)
    write_summary_md(summary, provenance)
    write_excel_outputs(summary, seed_metrics, drug_bins, provenance)

    print_visio(summary)
    print("\nWrote:")
    for p in [
        summary_tsv,
        OUT_DIR / "Fig4_similarity_stratified_final_summary.md",
        OUT_DIR / "Fig4_similarity_stratified_source_data.xlsx",
        SOURCE_XLSX_WITH_FIG4,
    ]:
        print(p.relative_to(ROOT))


if __name__ == "__main__":
    main()
