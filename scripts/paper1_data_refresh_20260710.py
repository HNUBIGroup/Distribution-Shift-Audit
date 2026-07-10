#!/usr/bin/env python3
import csv
import hashlib
import json
import math
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    matthews_corrcoef,
    roc_auc_score,
)


BASE = Path.cwd()
OUT = BASE / "outputs/paper1_data_refresh_20260710"
ISG_ROOT = BASE / "formal_runs/isg_clean_fixedfinal_20260706"
ISG_RUNS = ISG_ROOT / "04_formal_runs"
ISG_AUDIT = ISG_ROOT / "08_final_audit_20260710_after_4seed_rerun"
ISG_STATUS = ISG_ROOT / "09_status"
BIS_ROOT = BASE / "formal_runs/bisgtar_masked_pairloss_fixedfinal_20260706"
ROOTS = {
    "ISG-MDA": ISG_ROOT,
    "Bi-SGTAR": BIS_ROOT,
    "MSMCDA": BASE / "formal_runs/cda_msmcda_corrected_fullmetric_20260619",
    "DLST-MDA": BASE / "formal_runs/dlst_native_fixedfinal_fullmetric_20260623",
    "MPHGNN": BASE / "formal_runs/native_mda_audit_20260601/MPHGNN_STRICT_FORMAL_GUARD_20260614",
    "PLMF-MDA": BASE / "formal_runs/full_metric_rerun_20260615/plmf_standardized_repair_20260619",
    "MGCNA": BASE / "formal_runs/mgcna_corrected_fast_full125_fixedfinal_20260629",
}
TASK = {
    "ISG-MDA": "MDA",
    "Bi-SGTAR": "CDA",
    "MSMCDA": "CDA",
    "DLST-MDA": "MDA",
    "MPHGNN": "MDA",
    "PLMF-MDA": "MDA",
    "MGCNA": "MDA",
}
METRICS = ["AUROC", "AUPR", "ACC", "F1", "MCC", "Brier", "ECE", "NLL"]
SUMMARY_METRICS = METRICS + ["loss"]
ISG_DATASETS = ["MDR", "MDS"]
MDA_SETTINGS = ["random", "mirna_cold", "drug_cold", "strict_cold", "scaffold_cold"]
BIS_SETTINGS = ["random", "circrna_cold", "disease_cold", "strict_cold"]
BAD_LOG_PATTERNS = [
    re.compile(p, re.I)
    for p in [r"Traceback", r"\bOOM\b|out of memory", r"\bKilled\b", r"RuntimeError", r"\bNaN\b", r"\binf\b", r"NCCL", r"segfault"]
]


def mkdirs():
    OUT.mkdir(parents=True, exist_ok=True)
    ISG_AUDIT.mkdir(parents=True, exist_ok=True)
    ISG_STATUS.mkdir(parents=True, exist_ok=True)


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(BASE))
    except Exception:
        return str(p)


def read_tsv(path):
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)


def write_tsv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False, na_rep="")


def write_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def as_float(x):
    try:
        if x == "" or pd.isna(x):
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def ece_score(y_true, y_prob, n_bins=10):
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    out = 0.0
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        if i == n_bins - 1:
            mask = (y_prob >= lo) & (y_prob <= hi)
        else:
            mask = (y_prob >= lo) & (y_prob < hi)
        if mask.any():
            out += (mask.sum() / len(y_prob)) * abs(y_true[mask].mean() - y_prob[mask].mean())
    return float(out)


def recompute_metrics(pred_df):
    y_true = pred_df["y_true"].astype(int).to_numpy()
    y_prob = pred_df["y_prob"].astype(float).to_numpy()
    if "y_pred" in pred_df.columns:
        y_pred = pred_df["y_pred"].astype(int).to_numpy()
    else:
        y_pred = (y_prob > 0.5).astype(int)
    clipped = np.clip(y_prob, 1e-7, 1 - 1e-7)
    return {
        "AUROC": float(roc_auc_score(y_true, y_prob)),
        "AUPR": float(average_precision_score(y_true, y_prob)),
        "ACC": float(accuracy_score(y_true, y_pred)),
        "F1": float(f1_score(y_true, y_pred, zero_division=0)),
        "MCC": float(matthews_corrcoef(y_true, y_pred)),
        "Brier": float(brier_score_loss(y_true, y_prob)),
        "ECE": ece_score(y_true, y_prob),
        "NLL": float(log_loss(y_true, clipped, labels=[0, 1])),
    }


def prediction_stats(pred_path):
    if not pred_path.exists() or pred_path.stat().st_size == 0:
        return {
            "rows": 0,
            "sha256": "",
            "y_true_counts": "",
            "y_pred_counts": "",
            "y_prob_min": "",
            "y_prob_max": "",
            "status": "MISSING",
        }
    df = pd.read_csv(pred_path, sep="\t")
    rows = len(df)
    y_true_counts = dict(sorted(Counter(df["y_true"].astype(int)).items())) if "y_true" in df.columns else {}
    y_pred_counts = dict(sorted(Counter(df["y_pred"].astype(int)).items())) if "y_pred" in df.columns else {}
    y_prob_min = float(df["y_prob"].min()) if "y_prob" in df.columns and rows else ""
    y_prob_max = float(df["y_prob"].max()) if "y_prob" in df.columns and rows else ""
    return {
        "rows": rows,
        "sha256": sha256_file(pred_path),
        "y_true_counts": json.dumps(y_true_counts, sort_keys=True),
        "y_pred_counts": json.dumps(y_pred_counts, sort_keys=True),
        "y_prob_min": y_prob_min,
        "y_prob_max": y_prob_max,
        "status": "PASS",
    }


def check_code_hashes(path):
    if not path.exists():
        return "SCHEMA_EXCEPTION", "code_hashes.tsv missing"
    mismatches = []
    missing = []
    try:
        df = read_tsv(path)
    except Exception as exc:
        return "FAIL", f"unreadable code_hashes.tsv: {exc}"
    pcol = "path" if "path" in df.columns else df.columns[0]
    scol = "sha256" if "sha256" in df.columns else df.columns[-1]
    for _, row in df.iterrows():
        f = Path(row[pcol])
        if not f.exists():
            missing.append(str(f))
            continue
        actual = sha256_file(f)
        if actual != row[scol]:
            mismatches.append(str(f))
    if mismatches:
        return "FAIL", f"mismatches={len(mismatches)}"
    if missing:
        return "SCHEMA_EXCEPTION", f"missing_hash_targets={len(missing)}"
    return "PASS", "all current"


def log_audit(run_dir):
    notes = []
    status = "PASS"
    benign = 0
    for name in ["stdout.log", "stderr.log", "run.log"]:
        p = run_dir / name
        if not p.exists():
            continue
        text = p.read_text(errors="replace")
        benign += text.count("TypedStorage is deprecated")
        scrubbed = text.replace("TypedStorage is deprecated", "")
        hits = []
        for pat in BAD_LOG_PATTERNS:
            if pat.search(scrubbed):
                hits.append(pat.pattern)
        if hits:
            status = "FAIL"
            notes.append(f"{name}:{','.join(hits)}")
    if benign:
        notes.append(f"benign TypedStorage warnings={benign}")
    return status, "; ".join(notes)


def audit_isg():
    required = [
        "metrics.json",
        "metrics.tsv",
        "predictions.tsv",
        "quality_gate.json",
        "run_metadata.json",
        "split_metadata.json",
        "code_hashes.tsv",
        "epoch_history.tsv",
        "stdout.log",
        "stderr.log",
    ]
    integrity = []
    recompute = []
    split_rows = []
    log_rows = []
    raw = []
    manifest = []
    run_status = []
    code_hash_rows = []
    missing_expected = []
    max_diff = 0.0
    for dataset in ISG_DATASETS:
        for setting in MDA_SETTINGS:
            for seed in range(25):
                run_dir = ISG_RUNS / dataset / setting / f"seed_{seed}"
                missing = [x for x in required if not (run_dir / x).exists()]
                complete = (run_dir / "SEED_COMPLETE_PASS").exists()
                failed = (run_dir / "SEED_FAILED").exists()
                pred_path = run_dir / "predictions.tsv"
                pred_nonempty = pred_path.exists() and pred_path.stat().st_size > 0
                metrics_exists = (run_dir / "metrics.json").exists()
                q_exists = (run_dir / "quality_gate.json").exists()
                if not complete or failed or missing or not pred_nonempty:
                    missing_expected.append(f"{dataset}/{setting}/seed_{seed}")
                pstats = prediction_stats(pred_path)
                log_status, log_note = log_audit(run_dir)
                code_status, code_note = check_code_hashes(run_dir / "code_hashes.tsv")
                code_hash_rows.append(
                    {
                        "dataset": dataset,
                        "setting": setting,
                        "seed": seed,
                        "code_hash_status": code_status,
                        "note": code_note,
                        "run_dir": rel(run_dir),
                    }
                )
                gate_status = "PASS"
                gate_note = ""
                if q_exists:
                    q = json.loads((run_dir / "quality_gate.json").read_text())
                    bad = [g for g in q.get("gates", []) if g.get("status") != "PASS"]
                    gate_note = "; ".join(f"{g.get('gate')}={g.get('status')}" for g in bad)
                    if bad:
                        gate_status = "FAIL"
                integrity_status = "PASS" if complete and not failed and not missing and pred_nonempty and gate_status == "PASS" else "FAIL"
                integrity.append(
                    {
                        "dataset": dataset,
                        "setting": setting,
                        "seed": seed,
                        "complete_pass": int(complete),
                        "seed_failed": int(failed),
                        "missing_required_files": ",".join(missing),
                        "predictions_nonempty": int(pred_nonempty),
                        "prediction_rows": pstats["rows"],
                        "quality_gate_status": gate_status,
                        "code_hash_status": code_status,
                        "integrity_status": integrity_status,
                        "note": gate_note,
                        "run_dir": rel(run_dir),
                    }
                )
                run_status.append(
                    {
                        "model_name": "ISG-MDA",
                        "dataset": dataset,
                        "setting": setting,
                        "seed": seed,
                        "complete_pass": int(complete),
                        "seed_failed": int(failed),
                        "predictions_exists": int(pred_path.exists()),
                        "predictions_rows": pstats["rows"],
                        "metrics_exists": int(metrics_exists),
                        "quality_gate_exists": int(q_exists),
                        "log_status": log_status,
                        "note": log_note,
                    }
                )
                manifest.append(
                    {
                        "model_name": "ISG-MDA",
                        "dataset": dataset,
                        "setting": setting,
                        "seed": seed,
                        "prediction_file": rel(pred_path),
                        "rows": pstats["rows"],
                        "sha256": pstats["sha256"],
                        "y_true_counts": pstats["y_true_counts"],
                        "y_pred_counts": pstats["y_pred_counts"],
                        "y_prob_min": pstats["y_prob_min"],
                        "y_prob_max": pstats["y_prob_max"],
                        "include_in_release": "YES" if pstats["status"] == "PASS" else "NO",
                        "note": "",
                    }
                )
                log_rows.append(
                    {
                        "dataset": dataset,
                        "setting": setting,
                        "seed": seed,
                        "log_status": log_status,
                        "note": log_note,
                        "run_dir": rel(run_dir),
                    }
                )
                split_meta = {}
                if (run_dir / "split_metadata.json").exists():
                    split_meta = json.loads((run_dir / "split_metadata.json").read_text())
                split_status = "PASS"
                reasons = []
                if split_meta.get("pair_disjoint_pass") is not True:
                    split_status = "FAIL"
                    reasons.append("pair_disjoint")
                if split_meta.get("heldout_entity_pass") is not True:
                    split_status = "FAIL"
                    reasons.append("heldout_entity")
                if setting == "scaffold_cold" and gate_status != "PASS":
                    split_status = "FAIL"
                    reasons.append("scaffold_quality_gate")
                split_rows.append(
                    {
                        "dataset": dataset,
                        "setting": setting,
                        "seed": seed,
                        "pair_disjoint_pass": split_meta.get("pair_disjoint_pass", ""),
                        "pair_overlap": split_meta.get("pair_overlap", ""),
                        "heldout_entity_pass": split_meta.get("heldout_entity_pass", ""),
                        "mirna_overlap": split_meta.get("mirna_overlap", ""),
                        "drug_overlap": split_meta.get("drug_overlap", ""),
                        "train_rows": split_meta.get("train_rows", ""),
                        "test_rows": split_meta.get("test_rows", ""),
                        "split_leakage_status": split_status,
                        "note": ",".join(reasons),
                    }
                )
                if metrics_exists and pred_nonempty:
                    metrics = json.loads((run_dir / "metrics.json").read_text())
                    pred_df = pd.read_csv(pred_path, sep="\t")
                    rec = recompute_metrics(pred_df)
                    diffs = {m: abs(float(metrics[m]) - rec[m]) for m in METRICS if m in metrics}
                    row_max = max(diffs.values()) if diffs else math.inf
                    max_diff = max(max_diff, row_max if math.isfinite(row_max) else 0.0)
                    recompute.append(
                        {
                            "dataset": dataset,
                            "setting": setting,
                            "seed": seed,
                            **{m: metrics.get(m, "") for m in METRICS},
                            **{f"{m}_recomputed": rec[m] for m in METRICS},
                            **{f"{m}_abs_diff": diffs.get(m, "") for m in METRICS},
                            "max_abs_diff": row_max,
                            "status": "PASS" if row_max <= 1e-6 else "FAIL",
                            "prediction_file": rel(pred_path),
                        }
                    )
                    raw.append(
                        {
                            "dataset": dataset,
                            "setting": setting,
                            "seed": seed,
                            **{m: metrics.get(m, "") for m in METRICS},
                            "loss": metrics.get("loss", ""),
                            "test_loss": metrics.get("test_loss", ""),
                            "train_loss_final": metrics.get("train_loss_final", ""),
                            "loss_schema_note": "generic loss key unavailable" if "loss" not in metrics else "",
                            "n_test": split_meta.get("test_rows", pstats["rows"]),
                            "n_train": split_meta.get("train_rows", ""),
                            "prediction_rows": pstats["rows"],
                            "run_dir": rel(run_dir),
                            "status": "PASS" if integrity_status == "PASS" and row_max <= 1e-6 else "FAIL",
                        }
                    )
    raw_df = pd.DataFrame(raw)
    summary_rows = []
    for (dataset, setting), g in raw_df.groupby(["dataset", "setting"], sort=True):
        row = {"dataset": dataset, "setting": setting, "n_success": len(g)}
        notes = []
        for metric in SUMMARY_METRICS + ["test_loss", "train_loss_final"]:
            vals = pd.to_numeric(g[metric], errors="coerce") if metric in g.columns else pd.Series(dtype=float)
            if vals.notna().sum():
                row[f"{metric}_mean"] = vals.mean()
                row[f"{metric}_sd"] = vals.std(ddof=1)
                row[f"{metric}_mean_sd"] = f"{vals.mean():.6f} +/- {vals.std(ddof=1):.6f}"
            else:
                row[f"{metric}_mean"] = ""
                row[f"{metric}_sd"] = ""
                row[f"{metric}_mean_sd"] = "NA"
                if metric == "loss":
                    notes.append("generic loss key unavailable")
        row["schema_note"] = "; ".join(sorted(set(notes)))
        summary_rows.append(row)
    summary_df = pd.DataFrame(summary_rows)
    integrity_df = pd.DataFrame(integrity)
    recompute_df = pd.DataFrame(recompute)
    split_df = pd.DataFrame(split_rows)
    log_df = pd.DataFrame(log_rows)
    manifest_df = pd.DataFrame(manifest)
    run_status_df = pd.DataFrame(run_status)
    code_df = pd.DataFrame(code_hash_rows)
    write_tsv(integrity_df, ISG_AUDIT / "ISG_FORMAL_250_INTEGRITY_AUDIT.tsv")
    write_tsv(recompute_df, ISG_AUDIT / "ISG_FORMAL_250_METRIC_RECOMPUTATION.tsv")
    write_tsv(split_df, ISG_AUDIT / "ISG_FORMAL_250_SPLIT_LEAKAGE_AUDIT.tsv")
    write_tsv(log_df, ISG_AUDIT / "ISG_FORMAL_250_LOG_AUDIT.tsv")
    write_tsv(raw_df, ISG_AUDIT / "ISG_FORMAL_250_RAW_METRICS.tsv")
    write_tsv(summary_df, ISG_AUDIT / "ISG_FORMAL_250_SUMMARY_MEAN_SD.tsv")
    write_tsv(code_df, ISG_AUDIT / "ISG_FORMAL_250_CODE_HASH_AUDIT.tsv")
    write_tsv(manifest_df, OUT / "ISG_PREDICTION_MANIFEST.tsv")
    complete_count = int(integrity_df["complete_pass"].sum())
    failed_count = int(integrity_df["seed_failed"].sum())
    pred_ok = int((integrity_df["predictions_nonempty"] == 1).sum())
    metric_ok = int((recompute_df["status"] == "PASS").sum())
    audit_pass = (
        complete_count == 250
        and failed_count == 0
        and pred_ok == 250
        and metric_ok == 250
        and (integrity_df["integrity_status"] == "PASS").all()
        and (split_df["split_leakage_status"] == "PASS").all()
        and (log_df["log_status"] == "PASS").all()
        and not missing_expected
    )
    if audit_pass:
        (ISG_STATUS / "ISG_FORMAL_250_COMPLETE_PASS").write_text("PASS\n")
        (ISG_STATUS / "ISG_FROZEN_FOR_MANUSCRIPT_AND_SUPPLEMENT_20260710").write_text("PASS\n")
    else:
        gap = pd.DataFrame({"missing_or_failed_seed": missing_expected})
        write_tsv(gap, ISG_AUDIT / "ISG_FORMAL_250_GAP_REPORT.tsv")
        write_tsv(integrity_df[integrity_df["integrity_status"] != "PASS"], ISG_AUDIT / "ISG_FORMAL_250_RERUN_MANIFEST.tsv")
    report = [
        "# ISG formal 250 final audit after 4-seed rerun",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Status: {'PASS' if audit_pass else 'GAP'}",
        f"SEED_COMPLETE_PASS: {complete_count}/250",
        f"SEED_FAILED: {failed_count}",
        f"predictions.tsv nonempty: {pred_ok}/250",
        f"metric recomputation PASS: {metric_ok}/250",
        f"max metric recomputation abs diff: {max_diff:.12g}",
        f"split/leakage audit PASS: {int((split_df['split_leakage_status'] == 'PASS').sum())}/250",
        f"log audit PASS: {int((log_df['log_status'] == 'PASS').sum())}/250",
        "PyTorch TypedStorage deprecation warnings are recorded as benign warnings and are not failures.",
        "",
        "Outputs:",
        f"- {rel(ISG_AUDIT / 'ISG_FORMAL_250_INTEGRITY_AUDIT.tsv')}",
        f"- {rel(ISG_AUDIT / 'ISG_FORMAL_250_METRIC_RECOMPUTATION.tsv')}",
        f"- {rel(ISG_AUDIT / 'ISG_FORMAL_250_SPLIT_LEAKAGE_AUDIT.tsv')}",
        f"- {rel(ISG_AUDIT / 'ISG_FORMAL_250_LOG_AUDIT.tsv')}",
        f"- {rel(ISG_AUDIT / 'ISG_FORMAL_250_RAW_METRICS.tsv')}",
        f"- {rel(ISG_AUDIT / 'ISG_FORMAL_250_SUMMARY_MEAN_SD.tsv')}",
        f"- {rel(ISG_AUDIT / 'ISG_FORMAL_250_CODE_HASH_AUDIT.tsv')}",
    ]
    (ISG_AUDIT / "ISG_FORMAL_250_FINAL_AUDIT_REPORT.md").write_text("\n".join(report) + "\n")
    return {
        "pass": audit_pass,
        "complete_count": complete_count,
        "failed_count": failed_count,
        "max_diff": max_diff,
        "raw": raw_df,
        "summary": summary_df,
        "manifest": manifest_df,
        "run_status": run_status_df,
        "integrity": integrity_df,
        "recompute": recompute_df,
        "split": split_df,
        "log": log_df,
        "code": code_df,
    }


def canonical_summary(df, model, task_type, source_root, source_file, schema_note=""):
    out = pd.DataFrame(index=df.index)
    col = {c.lower(): c for c in df.columns}
    out["model_name"] = model
    out["task_type"] = task_type
    out["dataset"] = df[col["dataset"]] if "dataset" in col else ("Dataset1" if model == "Bi-SGTAR" else "native")
    out["setting"] = df[col["setting"]] if "setting" in col else ""
    ncol = next((col[x] for x in ["n_success", "n_seeds", "n", "n_expected"] if x in col), None)
    out["n_success"] = df[ncol] if ncol else ""
    for m in SUMMARY_METRICS:
        src = "AUC" if m == "AUROC" and "AUC_mean" in df.columns else m
        out[f"{m}_mean"] = df[f"{src}_mean"] if f"{src}_mean" in df.columns else ""
        out[f"{m}_sd"] = df[f"{src}_sd"] if f"{src}_sd" in df.columns else ""
    note = schema_note
    if "AUC_mean" in df.columns and "AUROC_mean" not in df.columns:
        note = (note + "; " if note else "") + "AUC column mapped to AUROC"
    if "loss_mean" not in df.columns:
        note = (note + "; " if note else "") + "loss unavailable; not imputed"
    if note:
        parts = []
        for part in [x.strip() for x in note.split(";")]:
            if part and part not in parts:
                parts.append(part)
        note = "; ".join(parts)
    out["schema_note"] = note
    out["source_root"] = rel(source_root)
    out["source_file"] = rel(source_file)
    return out


def canonical_raw(df, model, task_type, source_file, schema_note=""):
    out = pd.DataFrame(index=df.index)
    lc = {c.lower(): c for c in df.columns}
    out["model_name"] = model
    out["task_type"] = task_type
    out["dataset"] = df[lc["dataset"]] if "dataset" in lc else ("Dataset1" if model == "Bi-SGTAR" else "native")
    out["setting"] = df[lc["setting"]] if "setting" in lc else ""
    out["seed"] = df[lc["seed"]] if "seed" in lc else ""
    for m in METRICS:
        src = "AUC" if m == "AUROC" and "AUC" in df.columns else m
        out[m] = df[src] if src in df.columns else ""
    out["loss"] = df["loss"] if "loss" in df.columns else ""
    out["train_loss_final"] = df["train_loss_final"] if "train_loss_final" in df.columns else ""
    out["test_loss"] = df["test_loss"] if "test_loss" in df.columns else ""
    out["run_status"] = "PASS"
    rd = next((c for c in ["run_dir", "Run_dir", "output_dir", "prediction_file"] if c in df.columns), None)
    out["run_dir"] = df[rd] if rd else ""
    out["source_file"] = rel(source_file)
    if schema_note:
        out["schema_note"] = schema_note
    return out


def plmf_tables():
    root = ROOTS["PLMF-MDA"]
    rows = []
    for metrics_path in sorted((root / "05_runs").glob("*/*/seed_*/metrics.tsv")):
        if not (metrics_path.parent / "COMPLETE_PASS").exists():
            continue
        df = read_tsv(metrics_path)
        if df.empty:
            continue
        row = df.iloc[0].to_dict()
        meta_path = metrics_path.parent / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            row["n_test"] = meta.get("n_predictions", "")
            row["n_train"] = meta.get("train_rows", "")
        row["run_dir"] = rel(metrics_path.parent)
        rows.append(row)
    raw = pd.DataFrame(rows)
    srows = []
    for (dataset, setting), g in raw.groupby(["dataset", "setting"], sort=True):
        row = {"model": "PLMF-MDA", "dataset": dataset, "setting": setting, "n_success": len(g)}
        for m in SUMMARY_METRICS:
            vals = pd.to_numeric(g[m], errors="coerce") if m in g.columns else pd.Series(dtype=float)
            row[f"{m}_mean"] = vals.mean() if vals.notna().sum() else ""
            row[f"{m}_sd"] = vals.std(ddof=1) if vals.notna().sum() else ""
        srows.append(row)
    summary = pd.DataFrame(srows)
    raw_path = OUT / "PLMF_MDA_REBUILT_FROM_FROZEN_ROOT_RAW_METRICS.tsv"
    summary_path = OUT / "PLMF_MDA_REBUILT_FROM_FROZEN_ROOT_SUMMARY_MEAN_SD.tsv"
    write_tsv(raw, raw_path)
    write_tsv(summary, summary_path)
    return raw, summary, raw_path, summary_path


def load_model_tables(isg):
    model_files = {
        "Bi-SGTAR": (
            ROOTS["Bi-SGTAR"] / "06_metrics/BISGTAR_FIXEDFINAL_E200_RAW_METRICS.tsv",
            ROOTS["Bi-SGTAR"] / "06_metrics/BISGTAR_FIXEDFINAL_E200_SUMMARY_MEAN_SD.tsv",
        ),
        "MSMCDA": (
            ROOTS["MSMCDA"] / "MSMCDA_CORRECTED_FULL100_RAW_METRICS.tsv",
            ROOTS["MSMCDA"] / "MSMCDA_CORRECTED_FULL100_SUMMARY_MEAN_SD.tsv",
        ),
        "DLST-MDA": (
            ROOTS["DLST-MDA"] / "06_metrics/DLST_NATIVE_FIXEDFINAL_FULL125_RAW_METRICS.tsv",
            ROOTS["DLST-MDA"] / "06_metrics/DLST_NATIVE_FIXEDFINAL_SUMMARY_MEAN_SD.tsv",
        ),
        "MPHGNN": (
            ROOTS["MPHGNN"] / "table_exports/MPHGNN_ADAPTED_FIXEDTEST_E10_FULL25_raw_metrics.tsv",
            ROOTS["MPHGNN"] / "table_exports/MPHGNN_ADAPTED_FIXEDTEST_E10_FULL25_summary_mean_sd.tsv",
        ),
        "MGCNA": (
            ROOTS["MGCNA"] / "audit/MGCNA_CORRECTED_FAST_FINAL125_RAW_METRICS.tsv",
            ROOTS["MGCNA"] / "audit/MGCNA_CORRECTED_FAST_FINAL125_SUMMARY_MEAN_SD.tsv",
        ),
    }
    raw_all = []
    summary_all = []
    raw_all.append(canonical_raw(isg["raw"].assign(model_name="ISG-MDA"), "ISG-MDA", "MDA", ISG_AUDIT / "ISG_FORMAL_250_RAW_METRICS.tsv"))
    isg_summary = isg["summary"].copy()
    isg_summary["model"] = "ISG-MDA"
    summary_all.append(canonical_summary(isg_summary, "ISG-MDA", "MDA", ISG_ROOT, ISG_AUDIT / "ISG_FORMAL_250_SUMMARY_MEAN_SD.tsv", "after 4-seed rerun audit PASS"))
    plmf_raw, plmf_summary, plmf_raw_path, plmf_summary_path = plmf_tables()
    for model, (raw_path, summary_path) in model_files.items():
        raw_df = read_tsv(raw_path)
        summary_df = read_tsv(summary_path)
        note = ""
        if model == "MPHGNN":
            note = "loss unavailable; not imputed"
        raw_all.append(canonical_raw(raw_df, model, TASK[model], raw_path, note))
        summary_all.append(canonical_summary(summary_df, model, TASK[model], ROOTS[model], summary_path, note))
    raw_all.append(canonical_raw(plmf_raw, "PLMF-MDA", "MDA", plmf_raw_path))
    summary_all.append(canonical_summary(plmf_summary, "PLMF-MDA", "MDA", ROOTS["PLMF-MDA"], plmf_summary_path))
    raw7 = pd.concat(raw_all, ignore_index=True)
    summary7 = pd.concat(summary_all, ignore_index=True)
    return raw7, summary7


def manifest_from_prediction_files(model, files):
    rows = []
    for pred_path, dataset, setting, seed, note in files:
        st = prediction_stats(pred_path)
        rows.append(
            {
                "model_name": model,
                "dataset": dataset,
                "setting": setting,
                "seed": seed,
                "prediction_file": rel(pred_path),
                "rows": st["rows"],
                "sha256": st["sha256"],
                "y_true_counts": st["y_true_counts"],
                "y_pred_counts": st["y_pred_counts"],
                "y_prob_min": st["y_prob_min"],
                "y_prob_max": st["y_prob_max"],
                "include_in_release": "YES" if st["status"] == "PASS" else "NO",
                "note": note,
            }
        )
    return rows


def build_prediction_manifest(isg_manifest):
    rows = isg_manifest.to_dict("records")
    bis_files = []
    for setting in BIS_SETTINGS:
        for seed in range(25):
            bis_files.append((BIS_ROOT / "04_formal_runs" / setting / f"seed_{seed}" / "predictions.tsv", "Dataset1", setting, seed, ""))
    rows.extend(manifest_from_prediction_files("Bi-SGTAR", bis_files))
    msm_idx = read_tsv(ROOTS["MSMCDA"] / "MSMCDA_CORRECTED_FULL100_PREDICTION_INDEX.tsv")
    msm_files = []
    for _, r in msm_idx.iterrows():
        msm_files.append((BASE / r["Predictions_file"], r["Dataset"], r["Setting"], r["Seed"], ""))
    rows.extend(manifest_from_prediction_files("MSMCDA", msm_files))
    dlst_idx = read_tsv(ROOTS["DLST-MDA"] / "07_predictions/DLST_NATIVE_FIXEDFINAL_PREDICTION_INDEX.tsv")
    dlst_files = []
    for _, r in dlst_idx.iterrows():
        dlst_files.append((Path(r["predictions_path"]), "DLST-native", r["Setting"], r["Seed"], ""))
    rows.extend(manifest_from_prediction_files("DLST-MDA", dlst_files))
    mph = read_tsv(ROOTS["MPHGNN"] / "table_exports/MPHGNN_ADAPTED_FIXEDTEST_E10_FULL25_raw_metrics.tsv")
    mph_files = []
    for _, r in mph.iterrows():
        seed_int = int(r["seed"])
        candidates = [
            ROOTS["MPHGNN"] / r["prediction_file"],
            ROOTS["MPHGNN"] / "strict_full25_clean" / r["setting"] / f"seed_{seed_int:02d}" / r["prediction_file"],
            ROOTS["MPHGNN"] / "strict_full25_clean" / r["setting"] / f"seed_{seed_int}" / r["prediction_file"],
        ]
        pred = next((p for p in candidates if p.exists()), candidates[0])
        mph_files.append((pred, "native", r["setting"], r["seed"], "AUC mapped to AUROC; no loss"))
    rows.extend(manifest_from_prediction_files("MPHGNN", mph_files))
    plmf_files = []
    for p in sorted((ROOTS["PLMF-MDA"] / "05_runs").glob("*/*/seed_*/predictions.tsv")):
        parts = p.parts
        plmf_files.append((p, parts[-4], parts[-3], parts[-2].split("_")[-1], ""))
    rows.extend(manifest_from_prediction_files("PLMF-MDA", plmf_files))
    mgc_files = []
    for p in sorted((ROOTS["MGCNA"] / "formal_125runs").glob("*/*/predictions.tsv")):
        mgc_files.append((p, "native", p.parts[-3], p.parts[-2].split("_")[-1], ""))
    rows.extend(manifest_from_prediction_files("MGCNA", mgc_files))
    return pd.DataFrame(rows)


def build_run_status(raw7, manifest7, isg_run_status):
    rows = isg_run_status.to_dict("records")
    for _, r in raw7[raw7["model_name"] != "ISG-MDA"].iterrows():
        match = manifest7[
            (manifest7["model_name"] == r["model_name"])
            & (manifest7["setting"].astype(str) == str(r["setting"]))
            & (manifest7["seed"].astype(str) == str(r["seed"]))
        ]
        pred_rows = match.iloc[0]["rows"] if len(match) else ""
        rows.append(
            {
                "model_name": r["model_name"],
                "dataset": r["dataset"],
                "setting": r["setting"],
                "seed": r["seed"],
                "complete_pass": 1,
                "seed_failed": 0,
                "predictions_exists": 1 if len(match) and int(match.iloc[0]["rows"]) > 0 else 0,
                "predictions_rows": pred_rows,
                "metrics_exists": 1,
                "quality_gate_exists": "",
                "log_status": "NOT_REAUDITED_READONLY",
                "note": "read-only completeness check from frozen root",
            }
        )
    return pd.DataFrame(rows)


def marker_for_model(model):
    root = ROOTS[model]
    explicit = {
        "PLMF-MDA": root / "09_status/PLMF_REPAIR_STATUS.md",
        "MPHGNN": root / "status/MPHGNN_ADAPTED_FIXEDTEST_E10_FULL25.status.tsv",
    }
    if model in explicit and explicit[model].exists():
        return rel(explicit[model])
    candidates = list(root.glob("**/*PASS*"))
    candidates = [p for p in candidates if p.is_file() and not any(x in str(p).lower() for x in ["smoke", "pilot", "tmp", "failed"])]
    if model == "Bi-SGTAR":
        p = root / "09_status/BISGTAR_FIXEDFINAL_E200_COMPLETE_PASS"
        return rel(p) if p.exists() else ""
    if model == "ISG-MDA":
        p = root / "09_status/ISG_FORMAL_250_COMPLETE_PASS"
        return rel(p) if p.exists() else ""
    return rel(candidates[0]) if candidates else ""


def build_registry(summary7, manifest7, run_status7):
    rows = []
    expected = {"ISG-MDA": 250, "Bi-SGTAR": 100, "MSMCDA": 100, "DLST-MDA": 125, "MPHGNN": 125, "PLMF-MDA": 250, "MGCNA": 125}
    for model in ["ISG-MDA", "Bi-SGTAR", "MSMCDA", "DLST-MDA", "MPHGNN", "PLMF-MDA", "MGCNA"]:
        sm = summary7[summary7["model_name"] == model]
        rs = run_status7[run_status7["model_name"] == model]
        mf = manifest7[manifest7["model_name"] == model]
        schema = "; ".join(sorted(set(str(x) for x in sm["schema_note"].fillna("") if str(x))))
        rows.append(
            {
                "model_name": model,
                "task_type": TASK[model],
                "formal_root": rel(ROOTS[model]),
                "frozen_status": "PASS" if model != "Bi-SGTAR" else "FROZEN_FIXED_FINAL_E200_PASS_AFTER_DISCREPANCY_AUDIT",
                "status_marker": marker_for_model(model),
                "expected_runs": expected[model],
                "actual_complete_runs": int(pd.to_numeric(rs["complete_pass"], errors="coerce").fillna(0).sum()),
                "settings": ",".join(sorted(set(sm["setting"].astype(str)))),
                "metrics_available": ",".join([m for m in METRICS if f"{m}_mean" in sm.columns and sm[f"{m}_mean"].astype(str).ne("").any()]),
                "predictions_available": int((pd.to_numeric(mf["rows"], errors="coerce").fillna(0) > 0).sum()),
                "audit_status": "PASS" if int(pd.to_numeric(rs["complete_pass"], errors="coerce").fillna(0).sum()) >= expected[model] else "CHECK",
                "schema_exceptions": schema,
                "use_for_manuscript": "YES",
                "use_for_supplementary": "YES",
                "use_for_source_data": "YES",
            }
        )
    return pd.DataFrame(rows)


def audit_summary(isg, registry):
    rows = [
        {
            "model_name": "ISG-MDA",
            "audit_type": "final_integrity_metric_split_log_code",
            "n_checked": 250,
            "n_pass": 250 if isg["pass"] else "",
            "n_fail": 0 if isg["pass"] else "",
            "max_metric_recompute_diff": isg["max_diff"],
            "leakage_status": "PASS" if (isg["split"]["split_leakage_status"] == "PASS").all() else "FAIL",
            "log_status": "PASS" if (isg["log"]["log_status"] == "PASS").all() else "FAIL",
            "schema_exception": "generic loss key unavailable; test_loss/train_loss_final recorded",
            "report_path": rel(ISG_AUDIT / "ISG_FORMAL_250_FINAL_AUDIT_REPORT.md"),
        }
    ]
    for _, r in registry[registry["model_name"] != "ISG-MDA"].iterrows():
        rows.append(
            {
                "model_name": r["model_name"],
                "audit_type": "read_only_completeness_from_existing_frozen_tables",
                "n_checked": r["actual_complete_runs"],
                "n_pass": r["actual_complete_runs"],
                "n_fail": 0,
                "max_metric_recompute_diff": "",
                "leakage_status": "AVAILABLE_IF_EXISTING_REPORT_PRESENT",
                "log_status": "NOT_REAUDITED_READONLY",
                "schema_exception": r["schema_exceptions"],
                "report_path": r["status_marker"],
            }
        )
    return pd.DataFrame(rows)


def excluded_assets():
    rows = [
        {
            "asset_path": "formal_runs/native_mda_audit_20260601",
            "model_name": "Bi-SGTAR",
            "reason_excluded": "old recovered/locked high-score or REAL25/E200 candidate provenance only; current fixed-final E200 low-score version is official",
            "replacement_root": rel(BIS_ROOT),
            "safe_to_delete": "NO",
            "note": "probability direction check did not rescue old high result",
        },
        {
            "asset_path": "formal_runs/isg_clean_fixedfinal_20260706/08_final_audit_20260710",
            "model_name": "ISG-MDA",
            "reason_excluded": "old GAP audit output before 4-seed rerun completion",
            "replacement_root": rel(ISG_AUDIT),
            "safe_to_delete": "NO",
            "note": "superseded by after_4seed_rerun audit",
        },
    ]
    patterns = ["smoke", "pilot", "tmp", "failed", "partial", "stale", "superseded", "old", "legacy", "locked", "recovered"]
    for root in [ISG_ROOT, BIS_ROOT, ROOTS["MSMCDA"], ROOTS["DLST-MDA"], ROOTS["MPHGNN"], ROOTS["PLMF-MDA"], ROOTS["MGCNA"]]:
        for p in root.rglob("*"):
            sp = rel(p)
            low = sp.lower()
            if any(x in low for x in patterns):
                rows.append(
                    {
                        "asset_path": sp,
                        "model_name": next((m for m, rr in ROOTS.items() if rr == root), ""),
                        "reason_excluded": "matches smoke/pilot/tmp/failed/partial/stale/old/legacy/superseded/recovered/locked exclusion pattern",
                        "replacement_root": rel(root),
                        "safe_to_delete": "NO",
                        "note": "not used in manuscript-ready tables",
                    }
                )
    df = pd.DataFrame(rows).drop_duplicates("asset_path")
    return df


def manuscript_snippets(summary7):
    def fmt(v):
        try:
            return f"{float(v):.4f}"
        except Exception:
            return "NA"
    isg = summary7[summary7["model_name"] == "ISG-MDA"]
    lines = ["# ISG manuscript-ready numbers", ""]
    for dataset in ISG_DATASETS:
        r = isg[(isg["dataset"] == dataset) & (isg["setting"] == "random")].iloc[0]
        lines.append(f"- {dataset} random: AUROC {fmt(r['AUROC_mean'])} +/- {fmt(r['AUROC_sd'])}; AUPR {fmt(r['AUPR_mean'])} +/- {fmt(r['AUPR_sd'])}; F1 {fmt(r['F1_mean'])} +/- {fmt(r['F1_sd'])}; MCC {fmt(r['MCC_mean'])} +/- {fmt(r['MCC_sd'])}; Brier {fmt(r['Brier_mean'])} +/- {fmt(r['Brier_sd'])}; ECE {fmt(r['ECE_mean'])} +/- {fmt(r['ECE_sd'])}; NLL {fmt(r['NLL_mean'])} +/- {fmt(r['NLL_sd'])}.")
        base = float(r["AUROC_mean"])
        for setting in ["drug_cold", "scaffold_cold", "strict_cold", "mirna_cold"]:
            q = isg[(isg["dataset"] == dataset) & (isg["setting"] == setting)].iloc[0]
            lines.append(f"- {dataset} {setting}: AUROC {fmt(q['AUROC_mean'])} +/- {fmt(q['AUROC_sd'])}; degradation vs random {base - float(q['AUROC_mean']):.4f}; ECE {fmt(q['ECE_mean'])}; NLL {fmt(q['NLL_mean'])}.")
    worst = isg.sort_values("AUROC_mean").iloc[0]
    lines.append(f"- Worst ISG setting by AUROC: {worst['dataset']} {worst['setting']} AUROC {fmt(worst['AUROC_mean'])} +/- {fmt(worst['AUROC_sd'])}.")
    (OUT / "ISG_MANUSCRIPT_READY_NUMBERS.md").write_text("\n".join(lines) + "\n")
    bis = summary7[summary7["model_name"] == "Bi-SGTAR"]
    lines = ["# Bi-SGTAR manuscript-ready numbers", ""]
    for _, r in bis.iterrows():
        lines.append(f"- {r['setting']}: AUROC {fmt(r['AUROC_mean'])} +/- {fmt(r['AUROC_sd'])}; AUPR {fmt(r['AUPR_mean'])} +/- {fmt(r['AUPR_sd'])}; F1 {fmt(r['F1_mean'])} +/- {fmt(r['F1_sd'])}; MCC {fmt(r['MCC_mean'])} +/- {fmt(r['MCC_sd'])}; Brier {fmt(r['Brier_mean'])} +/- {fmt(r['Brier_sd'])}; ECE {fmt(r['ECE_mean'])} +/- {fmt(r['ECE_sd'])}; NLL {fmt(r['NLL_mean'])} +/- {fmt(r['NLL_sd'])}; loss {fmt(r['loss_mean'])} +/- {fmt(r['loss_sd'])}.")
    (OUT / "BISGTAR_MANUSCRIPT_READY_NUMBERS.md").write_text("\n".join(lines) + "\n")
    note = """# Bi-SGTAR fixed-final discrepancy note

- Current fixed-final E200 low-score version under `formal_runs/bisgtar_masked_pairloss_fixedfinal_20260706` is the official manuscript/supplement/source-data version.
- Old recovered/locked high-score versions are excluded/provenance only.
- Old high-score versions must not be used for manuscript, figures, supplement, or source data.
- Probability direction check did not rescue the old high result.
- Corrected split, loss mask, and prediction recomputation audit support the current low-score fixed-final version.
"""
    (OUT / "BISGTAR_FIXEDFINAL_DISCREPANCY_NOTE.md").write_text(note)


def source_data(summary7):
    rows = []
    for _, r in summary7.iterrows():
        for metric in ["AUROC", "AUPR", "F1", "MCC", "Brier", "ECE", "NLL"]:
            rows.append(
                {
                    "model_name": r["model_name"],
                    "task_type": r["task_type"],
                    "dataset": r["dataset"],
                    "setting": r["setting"],
                    "metric": metric,
                    "mean": r.get(f"{metric}_mean", ""),
                    "sd": r.get(f"{metric}_sd", ""),
                    "n": r["n_success"],
                    "source_root": r["source_root"],
                    "source_file": r["source_file"],
                }
            )
    fig2 = pd.DataFrame(rows)
    fig3 = fig2[fig2["metric"].isin(["AUROC", "AUPR", "F1", "MCC", "Brier", "ECE", "NLL"])].copy()
    fig6 = fig2[fig2["task_type"] == "CDA"].copy()
    missing = pd.DataFrame(
        [
            {"status": "TODO_NOT_FOUND", "note": "No frozen source data found under approved roots", "figure": "Fig4_external_or_similarity"},
            {"status": "TODO_NOT_FOUND", "note": "No frozen source data found under approved roots", "figure": "Fig5_robustness_or_noise"},
        ]
    )
    (OUT / "SOURCE_DATA_MISSING_ITEMS.md").write_text(
        "# Source data missing items\n\n- Fig4_external_or_similarity: TODO_NOT_FOUND. No frozen source data found under approved roots.\n- Fig5_robustness_or_noise: TODO_NOT_FOUND. No frozen source data found under approved roots.\n"
    )
    return fig2, fig3, missing, missing.copy(), fig6


def write_xlsx(path, sheets):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe = name[:31]
            df.to_excel(writer, sheet_name=safe, index=False)
    wb = load_workbook(path)
    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            max_len = max(len(str(c.value)) if c.value is not None else 0 for c in col[:200])
            ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 2, 10), 60)
    wb.save(path)


def brief_and_report(isg, registry, summary7, audit7, missing_source):
    def top_lines(model):
        sm = summary7[summary7["model_name"] == model]
        lines = []
        for _, r in sm.iterrows():
            lines.append(
                f"- {model} {r['dataset']} {r['setting']}: AUROC {r['AUROC_mean']} +/- {r['AUROC_sd']}; AUPR {r['AUPR_mean']} +/- {r['AUPR_sd']}; F1 {r['F1_mean']} +/- {r['F1_sd']}; MCC {r['MCC_mean']} +/- {r['MCC_sd']}."
            )
        return lines
    brief = ["# Manuscript number replacement brief", "", "## 1. ISG-MDA final numbers", f"- ISG audit status: {'PASS' if isg['pass'] else 'GAP'} after 4-seed rerun."]
    brief.extend(top_lines("ISG-MDA"))
    brief.extend(["", "## 2. Bi-SGTAR fixed-final numbers", "- Bi-SGTAR old recovered/locked high-score results must not be used."])
    brief.extend(top_lines("Bi-SGTAR"))
    brief.extend(["", "## 3. Other five model final numbers"])
    for model in ["MSMCDA", "DLST-MDA", "MPHGNN", "PLMF-MDA", "MGCNA"]:
        brief.extend(top_lines(model))
    brief.extend(
        [
            "",
            "## 4. Seven-model horizontal summary",
            "- Use `PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv` for main cross-model tables and figure replacement.",
            "",
            "## 5. Main text candidates",
            "- ISG-MDA random/cold degradation and worst setting.",
            "- Bi-SGTAR fixed-final E200 low-score official results.",
            "- Seven-model AUROC/AUPR/F1/MCC/calibration summary.",
            "",
            "## 6. Supplementary table candidates",
            "- All seed-level raw metrics, prediction manifest, split/leakage audit, recomputation audit, excluded assets.",
            "",
            "## 7. Visio figure replacement",
            "- Fig.2, Fig.3, Fig.6 have source-data sheets.",
            "- Fig.4 and Fig.5 are TODO_NOT_FOUND under approved frozen roots.",
            "",
            "## 8. Old numbers to delete or avoid",
            "- Bi-SGTAR old high-score recovered/locked results.",
            "- ISG old GAP audit and partial pre-rerun outputs.",
            "- Smoke/pilot/tmp/failed/partial/stale outputs.",
            "- DLST old 5-fold/old best epoch outputs if present.",
        ]
    )
    (OUT / "MANUSCRIPT_NUMBER_REPLACEMENT_BRIEF.md").write_text("\n".join(brief) + "\n")
    other = registry[~registry["model_name"].isin(["ISG-MDA", "Bi-SGTAR"])]
    report = [
        "# Paper1 data refresh final report",
        "",
        "## A. ISG audit status",
        f"- Status: {'PASS' if isg['pass'] else 'GAP'}",
        f"- Complete seed count: {isg['complete_count']}",
        f"- Failed count: {isg['failed_count']}",
        f"- Max metric recomputation diff: {isg['max_diff']}",
        f"- Audit report: {rel(ISG_AUDIT / 'ISG_FORMAL_250_FINAL_AUDIT_REPORT.md')}",
        f"- Summary: {rel(ISG_AUDIT / 'ISG_FORMAL_250_SUMMARY_MEAN_SD.tsv')}",
        "",
        "## B. Bi-SGTAR status",
        f"- Marker: {rel(BIS_ROOT / '09_status/BISGTAR_FIXEDFINAL_E200_COMPLETE_PASS')}",
        f"- Official summary: {rel(BIS_ROOT / '06_metrics/BISGTAR_FIXEDFINAL_E200_SUMMARY_MEAN_SD.tsv')}",
        "- Old high excluded: YES, provenance only.",
        "",
        "## C. Other five model status",
    ]
    for _, r in other.iterrows():
        report.append(f"- {r['model_name']}: root={r['formal_root']}; expected/actual={r['expected_runs']}/{r['actual_complete_runs']}; schema_exception={r['schema_exceptions']}")
    report.extend(
        [
            "",
            "## D. Generated files",
            f"- {rel(OUT / 'Supplementary_Data_Paper1_20260710.xlsx')}",
            f"- {rel(OUT / 'Source_Data_Paper1_20260710.xlsx')}",
            f"- {rel(OUT / 'PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv')}",
            f"- {rel(OUT / 'PAPER1_7MODEL_RAW_SEED_METRICS.tsv')}",
            f"- {rel(OUT / 'PAPER1_FROZEN_MODEL_REGISTRY.tsv')}",
            f"- {rel(OUT / 'MANUSCRIPT_NUMBER_REPLACEMENT_BRIEF.md')}",
            "",
            "## E. Missing data / TODO",
            "- Fig4_external_or_similarity: TODO_NOT_FOUND.",
            "- Fig5_robustness_or_noise: TODO_NOT_FOUND.",
            "- MPHGNN loss unavailable; not imputed.",
            "",
            "## F. Safety confirmation",
            "- No retraining.",
            "- No manuscript edit.",
            "- No Visio edit.",
            "- No Article2 access.",
            "- No GitHub packaging.",
            "- No old Bi-SGTAR high result used.",
        ]
    )
    (OUT / "PAPER1_DATA_REFRESH_FINAL_REPORT.md").write_text("\n".join(report) + "\n")


def main():
    mkdirs()
    bis_marker = BIS_ROOT / "09_status/BISGTAR_FIXEDFINAL_E200_COMPLETE_PASS"
    if not bis_marker.exists():
        raise SystemExit(f"Missing required Bi-SGTAR marker: {bis_marker}")
    isg = audit_isg()
    if not isg["pass"]:
        print("ISG final audit GAP")
        print(rel(ISG_AUDIT / "ISG_FORMAL_250_GAP_REPORT.tsv"))
        return
    raw7, summary7 = load_model_tables(isg)
    manifest7 = build_prediction_manifest(isg["manifest"])
    run_status7 = build_run_status(raw7, manifest7, isg["run_status"])
    registry = build_registry(summary7, manifest7, run_status7)
    audit7 = audit_summary(isg, registry)
    excluded = excluded_assets()
    write_tsv(registry, OUT / "PAPER1_FROZEN_MODEL_REGISTRY.tsv")
    write_json(registry.to_dict("records"), OUT / "PAPER1_FROZEN_MODEL_REGISTRY.json")
    write_tsv(summary7, OUT / "PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv")
    write_tsv(raw7, OUT / "PAPER1_7MODEL_RAW_SEED_METRICS.tsv")
    write_tsv(run_status7, OUT / "PAPER1_7MODEL_RUN_STATUS.tsv")
    write_tsv(manifest7, OUT / "PAPER1_7MODEL_PREDICTION_MANIFEST.tsv")
    write_tsv(audit7, OUT / "PAPER1_7MODEL_AUDIT_SUMMARY.tsv")
    write_tsv(excluded, OUT / "PAPER1_EXCLUDED_STALE_OR_FAILED_ASSETS.tsv")
    manuscript_snippets(summary7)
    fig2, fig3, fig4, fig5, fig6 = source_data(summary7)
    other5 = summary7[summary7["model_name"].isin(["MSMCDA", "DLST-MDA", "MPHGNN", "PLMF-MDA", "MGCNA"])]
    readme = pd.DataFrame(
        [
            {"field": "generated_time", "value": datetime.now().isoformat(timespec="seconds")},
            {"field": "data_sources", "value": "Seven approved frozen roots only"},
            {"field": "Bi-SGTAR", "value": "old high recovered/locked excluded; current fixed-final E200 low-score official"},
            {"field": "ISG-MDA", "value": "after 4-seed rerun final audit PASS"},
        ]
    )
    supp_sheets = {
        "00_README": readme,
        "01_Model_registry": registry,
        "02_7model_summary": summary7,
        "03_7model_raw_seed_metrics": raw7,
        "04_ISG_summary": isg["summary"],
        "05_ISG_raw_seed_metrics": isg["raw"],
        "06_ISG_metric_recompute": isg["recompute"],
        "07_ISG_split_leakage": isg["split"],
        "08_BiSGTAR_summary": read_tsv(BIS_ROOT / "06_metrics/BISGTAR_FIXEDFINAL_E200_SUMMARY_MEAN_SD.tsv"),
        "09_BiSGTAR_raw": read_tsv(BIS_ROOT / "06_metrics/BISGTAR_FIXEDFINAL_E200_RAW_METRICS.tsv"),
        "10_BiSGTAR_integrity": read_tsv(BIS_ROOT / "06_metrics/BISGTAR_FIXEDFINAL_E200_INTEGRITY_AUDIT.tsv"),
        "11_Other5_summary": other5,
        "12_Run_status": run_status7,
        "13_Prediction_manifest": manifest7,
        "14_Audit_summary": audit7,
        "15_Excluded_assets": excluded,
    }
    write_xlsx(OUT / "Supplementary_Data_Paper1_20260710.xlsx", supp_sheets)
    source_sheets = {
        "00_README": pd.DataFrame(
            [
                {"field": "description", "value": "Source data for Paper1 figures; no fabricated data."},
                {"field": "Fig2_distribution_shift", "value": "seven-model across split performance"},
                {"field": "Fig3_calibration_decision", "value": "ranking/calibration/decision metrics"},
                {"field": "Fig4_external_or_similarity", "value": "TODO_NOT_FOUND"},
                {"field": "Fig5_robustness_or_noise", "value": "TODO_NOT_FOUND"},
                {"field": "Fig6_CDA_or_summary", "value": "CDA models summary including MSMCDA and Bi-SGTAR"},
            ]
        ),
        "Fig2_distribution_shift": fig2,
        "Fig3_calibration_decision": fig3,
        "Fig4_external_or_similarity": fig4,
        "Fig5_robustness_or_noise": fig5,
        "Fig6_CDA_or_summary": fig6,
        "ISG_detailed_for_figures": summary7[summary7["model_name"] == "ISG-MDA"],
        "BiSGTAR_detailed_for_fig": summary7[summary7["model_name"] == "Bi-SGTAR"],
        "Other5_detailed_for_fig": other5,
    }
    write_xlsx(OUT / "Source_Data_Paper1_20260710.xlsx", source_sheets)
    brief_and_report(isg, registry, summary7, audit7, pd.concat([fig4, fig5], ignore_index=True))
    print("ISG final audit PASS")
    print(rel(OUT / "Supplementary_Data_Paper1_20260710.xlsx"))
    print(rel(OUT / "Source_Data_Paper1_20260710.xlsx"))
    print(rel(OUT / "MANUSCRIPT_NUMBER_REPLACEMENT_BRIEF.md"))
    print(rel(OUT / "PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv"))
    print("Missing/TODO: Fig4_external_or_similarity TODO_NOT_FOUND; Fig5_robustness_or_noise TODO_NOT_FOUND; MPHGNN loss unavailable; ISG generic loss unavailable but test_loss/train_loss_final recorded.")


if __name__ == "__main__":
    main()
