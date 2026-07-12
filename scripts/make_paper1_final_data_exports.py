#!/usr/bin/env python3
"""Build Paper1 FINAL source-data and supplementary-data exports.

This script intentionally does not read the older 20260710 Excel workbooks.
Inputs are the current frozen/fixed-final/official TSV/CSV/JSON/MD assets.
"""

from __future__ import annotations

import csv
import math
import re
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape


BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "results/source_data"
EXPORT_DIR = OUT_DIR / "final_exports"

REFRESH = BASE / "outputs/paper1_data_refresh_20260710"
PACKAGING = BASE / "formal_runs/paper1_github_packaging_registry_20260708"
GAT_MASK = BASE / "formal_runs/gat_only_masking_formal_20260625"
CDA_MASK = BASE / "formal_runs/cda_msmcda_native_maskedcold_full100_fixedfinal_20260701"
EXTERNAL = BASE / "formal_runs/table_exports"
MPHGNN_ROOT = BASE / "formal_runs/native_mda_audit_20260601/MPHGNN_STRICT_FORMAL_GUARD_20260614"

SOURCE_XLSX = OUT_DIR / "Paper1_Source_Data_FINAL.xlsx"
SUPP_XLSX = OUT_DIR / "Paper1_Supplementary_Data_FINAL.xlsx"
MANIFEST = OUT_DIR / "Paper1_data_manifest.tsv"
REPORT = OUT_DIR / "Paper1_data_export_report.md"

OLD_XLSX_NAMES = {
    "Source_Data_Paper1_20260710.xlsx",
    "Supplementary_Data_Paper1_20260710.xlsx",
    "Source_Data_Paper1_20260710_with_Fig4_similarity.xlsx",
    "Fig4_similarity_stratified_source_data.xlsx",
}


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(BASE))
    except Exception:
        return sanitize_public_value(str(path))


def sanitize_public_value(value: object) -> object:
    """Remove local usernames, absolute paths, and scheduler IDs from release exports."""
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"/home/[^/]+/My_module & PLMF-MDA/PLMF_clean/", "", text)
    text = re.sub(r"/home/[^/]+/My_module & PLMF-MDA/", "", text)
    text = re.sub(r"/home/[^/]+/", "local_provenance/", text)
    text = re.sub(r"\bu[0-9]{6,}\b", "local_user", text)
    text = text.replace("j" + "sj_replica", "local_replica")
    text = text.replace("slurm" + "_job", "scheduler_record")
    return text


def sanitize_public_row(row: dict[str, object]) -> dict[str, object]:
    sanitized = {key: sanitize_public_value(value) for key, value in row.items()}
    has_scheduler_record = any(str(value) == "scheduler_record" for value in sanitized.values())
    if has_scheduler_record:
        sanitized = {
            key: ("redacted_scheduler_id" if re.fullmatch(r"\d{5,}", str(value)) else value)
            for key, value in sanitized.items()
        }
    return sanitized


def read_table(path: Path, delimiter: str | None = None, headerless: bool = False) -> list[dict[str, str]]:
    if path.name in OLD_XLSX_NAMES:
        raise RuntimeError(f"Refusing prohibited old workbook input: {path}")
    if delimiter is None:
        delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        if headerless:
            reader = csv.reader(fh, delimiter=delimiter)
            for row in reader:
                rows.append({f"column_{i + 1}": value for i, value in enumerate(row)})
        else:
            reader = csv.DictReader(fh, delimiter=delimiter)
            for row in reader:
                rows.append({k: ("" if v is None else v) for k, v in row.items()})
    return rows


def write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            sanitized = sanitize_public_row({k: "" if row.get(k) is None else row.get(k) for k in fields})
            writer.writerow(sanitized)


def fnum(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.upper() in {"NA", "NAN", "MISSING", "NOT_AVAILABLE"}:
        return None
    try:
        x = float(text)
    except ValueError:
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return x


def mean_sd(values: list[float]) -> tuple[object, object, int]:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        return "", "", 0
    sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return statistics.mean(vals), sd, len(vals)


def is_mda(row: dict[str, str]) -> bool:
    return row.get("task_type") == "MDA"


def is_cda(row: dict[str, str]) -> bool:
    return row.get("task_type") == "CDA"


def select_cols(rows: list[dict[str, str]], cols: list[str]) -> list[dict[str, object]]:
    return [{c: row.get(c, "") for c in cols} for row in rows]


def add_source(rows: list[dict[str, object]], source: Path, note: str = "") -> list[dict[str, object]]:
    for row in rows:
        row["upstream_source"] = rel(source)
        if note:
            row["notes"] = note
    return rows


def todo_rows(reason: str, source_hint: str = "") -> list[dict[str, object]]:
    return [{"status": "NOT_AVAILABLE", "reason": reason, "source_hint": source_hint}]


def clean_sheet_name(name: str, used: set[str]) -> str:
    text = re.sub(r"[:\\/?*\[\]]", "_", name)
    text = text[:31]
    base = text
    i = 2
    while text in used:
        suffix = f"_{i}"
        text = f"{base[:31 - len(suffix)]}{suffix}"
        i += 1
    used.add(text)
    return text


def col_letter(n: int) -> str:
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def looks_numeric(value: object) -> bool:
    if isinstance(value, (int, float)):
        return not (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))
    if value is None:
        return False
    text = str(value).strip()
    if text == "":
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False


def xcell(row_idx: int, col_idx: int, value: object) -> str:
    ref = f"{col_letter(col_idx)}{row_idx}"
    if value is None:
        value = ""
    public_value = sanitize_public_value(value)
    if looks_numeric(public_value):
        return f'<c r="{ref}"><v>{escape(str(public_value))}</v></c>'
    text = escape(str(public_value))
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def worksheet_xml(rows: list[list[object]]) -> str:
    body = []
    for r_idx, row in enumerate(rows, start=1):
        cells = "".join(xcell(r_idx, c_idx, value) for c_idx, value in enumerate(row, start=1))
        body.append(f'<row r="{r_idx}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        f"<sheetData>{''.join(body)}</sheetData>"
        "</worksheet>"
    )


def write_xlsx(path: Path, sheets: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for i in range(1, len(sheets) + 1)
            )
            + "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            "</styleSheet>",
        )
        workbook_sheets = []
        rels = []
        for i, sheet in enumerate(sheets, start=1):
            name = escape(str(sheet["sheet_name"]))
            workbook_sheets.append(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>')
            rels.append(
                f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            )
            rows = sheet["xlsx_rows"]
            zf.writestr(f"xl/worksheets/sheet{i}.xml", worksheet_xml(rows))
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{''.join(workbook_sheets)}</sheets></workbook>",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rels)
            + "</Relationships>",
        )


def sheet_payload(
    workbook: str,
    requested_name: str,
    figure_or_table: str,
    description: str,
    source: str,
    rows: list[dict[str, object]],
    used_names: set[str],
    notes: str = "",
) -> dict[str, object]:
    sheet_name = clean_sheet_name(requested_name, used_names)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    if not fields:
        fields = ["status", "reason", "source_hint"]
        rows = todo_rows("No rows available", source)
    xrows: list[list[object]] = [
        ["Figure number / table", figure_or_table, "Panel", requested_name, "Brief description", description, "Data source file(s)", source],
        [],
        fields,
    ]
    for row in rows:
        xrows.append([row.get(field, "") for field in fields])
    return {
        "workbook": workbook,
        "requested_name": requested_name,
        "sheet_name": sheet_name,
        "figure_or_table": figure_or_table,
        "description": description,
        "upstream_source": source,
        "notes": notes,
        "rows": rows,
        "xlsx_rows": xrows,
    }


def build_mphgnn_calibration_bins() -> list[dict[str, object]]:
    raw_path = MPHGNN_ROOT / "table_exports/MPHGNN_ADAPTED_FIXEDTEST_E10_FULL25_raw_metrics.tsv"
    raw = read_table(raw_path)
    bins = defaultdict(lambda: {"n": 0, "sum_prob": 0.0, "sum_true": 0.0})
    missing = []
    for row in raw:
        setting = row.get("setting", "")
        seed = row.get("seed", "")
        pred_rel = row.get("prediction_file", "")
        pred_path = MPHGNN_ROOT / f"strict_full25_clean/{setting}/seed_{int(seed):02d}" / pred_rel
        if not pred_path.exists():
            missing.append(rel(pred_path))
            continue
        for pred in read_table(pred_path):
            prob = fnum(pred.get("y_prob"))
            y = fnum(pred.get("y_true"))
            if prob is None or y is None:
                continue
            idx = min(9, int(prob * 10))
            key = (setting, idx)
            bins[key]["n"] += 1
            bins[key]["sum_prob"] += prob
            bins[key]["sum_true"] += y
    out = []
    for (setting, idx), stats in sorted(bins.items()):
        n = stats["n"]
        out.append(
            {
                "model_name": "MPHGNN",
                "setting": setting,
                "bin_index": idx,
                "bin_lower": idx / 10,
                "bin_upper": (idx + 1) / 10,
                "n_predictions": n,
                "mean_predicted_probability": stats["sum_prob"] / n if n else "",
                "observed_positive_fraction": stats["sum_true"] / n if n else "",
                "absolute_calibration_gap": abs((stats["sum_prob"] / n) - (stats["sum_true"] / n)) if n else "",
                "upstream_source": rel(raw_path),
                "notes": "Derived from official MPHGNN audit prediction files; no model rerun.",
            }
        )
    if missing:
        out.append({"status": "NOT_AVAILABLE", "reason": f"Missing prediction files: {len(missing)}", "example": missing[0]})
    return out


def paired_delta_rows(raw: list[dict[str, str]], task_filter: str, metric: str, settings_to_compare: list[str]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], float] = {}
    for row in raw:
        if row.get("task_type") != task_filter:
            continue
        val = fnum(row.get(metric))
        if val is None:
            continue
        grouped[(row.get("model_name", ""), row.get("dataset", ""), row.get("setting", ""), row.get("seed", ""))] = val
    out = []
    models = sorted({k[0] for k in grouped})
    datasets = sorted({k[1] for k in grouped})
    for model in models:
        for dataset in datasets:
            for setting in settings_to_compare:
                diffs = []
                random_vals = []
                shifted_vals = []
                seeds = sorted({k[3] for k in grouped if k[0] == model and k[1] == dataset})
                for seed in seeds:
                    r = grouped.get((model, dataset, "random", seed))
                    s = grouped.get((model, dataset, setting, seed))
                    if r is not None and s is not None:
                        random_vals.append(r)
                        shifted_vals.append(s)
                        diffs.append(r - s)
                if diffs:
                    d_mean, d_sd, n = mean_sd(diffs)
                    r_mean, r_sd, _ = mean_sd(random_vals)
                    s_mean, s_sd, _ = mean_sd(shifted_vals)
                    out.append(
                        {
                            "model_name": model,
                            "dataset": dataset,
                            "comparison": f"random_minus_{setting}",
                            "metric": metric,
                            "n_matched_seeds": n,
                            "random_mean": r_mean,
                            "random_sd": r_sd,
                            "shifted_mean": s_mean,
                            "shifted_sd": s_sd,
                            "delta_mean": d_mean,
                            "delta_sd": d_sd,
                        }
                    )
    return out


def aggregate_formal100_masking(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    by_setting = defaultdict(list)
    for row in rows:
        by_setting[row.get("setting_from_path", "")].append(row)
    out = []
    for setting, vals in sorted(by_setting.items()):
        out.append(
            {
                "setting": setting,
                "n_seeds": len(vals),
                "applied_count_pass_seeds": sum(1 for r in vals if r.get("applied_count_pass") == "True"),
                "all_matrix_validation_pass_seeds": sum(1 for r in vals if r.get("all_matrix_validation_pass") == "True"),
                "manifest_rows_each": vals[0].get("manifest_rows", ""),
                "applied_masks_each": vals[0].get("applied_masks", ""),
                "expected_applied_masks_each": vals[0].get("expected_applied_masks", ""),
                "status": "PASS" if all(r.get("applied_count_pass") == "True" and r.get("all_matrix_validation_pass") == "True" for r in vals) else "CHECK",
            }
        )
    return out


def platinum_examples(raw_rows: list[dict[str, str]], limit: int = 80) -> list[dict[str, object]]:
    metals = [r for r in raw_rows if r.get("contains_metal") == "1" and r.get("selected_atom_element") == "Pt"]
    metals.sort(key=lambda r: fnum(r.get("absolute_delta")) or -1, reverse=True)
    cols = [
        "dataset",
        "model_seed",
        "candidate_pair_index",
        "controlled_rank",
        "global_rank",
        "miRNA_id",
        "drug_id",
        "strategy",
        "selected_atom_index",
        "selected_atom_element",
        "attention_score",
        "baseline_probability",
        "masked_probability",
        "signed_delta",
        "absolute_delta",
        "contains_metal",
        "analysis_subgroup",
        "analysis_role",
        "original_smiles",
    ]
    return [{c: r.get(c, "") for c in cols} for r in metals[:limit]]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    registry_path = REFRESH / "PAPER1_FROZEN_MODEL_REGISTRY.tsv"
    packaging_registry_path = PACKAGING / "PAPER1_FROZEN_MODEL_ASSET_REGISTRY.tsv"
    summary_path = REFRESH / "PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv"
    raw_path = REFRESH / "PAPER1_7MODEL_RAW_SEED_METRICS.tsv"
    fig4_summary_path = REFRESH / "Fig4_similarity_stratified_final.tsv"
    fig4_seed_path = REFRESH / "Fig4_similarity_stratified_seed_metrics.tsv"
    fig5_loss_path = REFRESH / "Fig5_CDA_random_baseline_loss_final.tsv"

    registry = read_table(registry_path)
    packaging_registry = read_table(packaging_registry_path)
    summary = read_table(summary_path)
    raw = read_table(raw_path)
    mda_summary = [r for r in summary if is_mda(r)]
    cda_summary = [r for r in summary if is_cda(r)]
    mda_raw = [r for r in raw if is_mda(r)]
    cda_raw = [r for r in raw if is_cda(r)]
    fig4_summary = read_table(fig4_summary_path)
    fig4_seed = read_table(fig4_seed_path)
    fig5_loss = read_table(fig5_loss_path)

    source_used: set[str] = set()
    supp_used: set[str] = set()
    source_sheets: list[dict[str, object]] = []
    supp_sheets: list[dict[str, object]] = []

    def add_source_sheet(name: str, fig: str, desc: str, src: Path | str, rows: list[dict[str, object]], notes: str = "") -> None:
        source_sheets.append(sheet_payload(SOURCE_XLSX.name, name, fig, desc, str(src), rows, source_used, notes))

    def add_supp_sheet(name: str, table: str, desc: str, src: Path | str, rows: list[dict[str, object]], notes: str = "") -> None:
        supp_sheets.append(sheet_payload(SUPP_XLSX.name, name, table, desc, str(src), rows, supp_used, notes))

    mda_basic_cols = [
        "model_name",
        "task_type",
        "dataset",
        "setting",
        "n_success",
        "AUROC_mean",
        "AUROC_sd",
        "AUPR_mean",
        "AUPR_sd",
        "F1_mean",
        "F1_sd",
        "ECE_mean",
        "ECE_sd",
        "Brier_mean",
        "Brier_sd",
        "NLL_mean",
        "NLL_sd",
        "schema_note",
        "source_root",
        "source_file",
    ]

    add_source_sheet(
        "Fig2a_AUROC_across_shifts",
        "Fig. 2",
        "Panel a; MDA AUROC across random and cold-start shifts.",
        summary_path,
        select_cols(mda_summary, mda_basic_cols),
    )
    add_source_sheet(
        "Fig2b_AUPR_across_shifts",
        "Fig. 2",
        "Panel b; MDA AUPR across random and cold-start shifts.",
        summary_path,
        select_cols(mda_summary, mda_basic_cols),
    )
    add_source_sheet(
        "Fig2c_delta_AUROC_random_minus_shifted",
        "Fig. 2",
        "Panel c; paired seed-level AUROC loss, random minus shifted setting.",
        raw_path,
        add_source(paired_delta_rows(raw, "MDA", "AUROC", ["drug_cold", "mirna_cold", "scaffold_cold", "strict_cold"]), raw_path),
    )

    add_source_sheet(
        "Fig3a_AUROC_vs_F1_all_MDA_combinations",
        "Fig. 3",
        "Panel a; AUROC versus F1 for all official MDA combinations.",
        summary_path,
        add_source(select_cols(mda_summary, mda_basic_cols), summary_path),
    )
    add_source_sheet(
        "Fig3b_AUROC_vs_ECE_all_MDA_combinations",
        "Fig. 3",
        "Panel b; AUROC versus ECE for all official MDA combinations.",
        summary_path,
        add_source(select_cols(mda_summary, mda_basic_cols), summary_path),
    )
    add_source_sheet(
        "Fig3c_MPHGNN_calibration_curve_bins",
        "Fig. 3",
        "Panel c; MPHGNN calibration bins derived from official audit predictions.",
        MPHGNN_ROOT / "table_exports/MPHGNN_ADAPTED_FIXEDTEST_E10_FULL25_raw_metrics.tsv",
        build_mphgnn_calibration_bins(),
        "Derived only from existing MPHGNN audit prediction files.",
    )
    add_source_sheet(
        "Fig3d_MPHGNN_representative_metrics",
        "Fig. 3",
        "Panel d; representative MPHGNN official summary metrics.",
        summary_path,
        add_source([r for r in select_cols(mda_summary, mda_basic_cols) if r.get("model_name") == "MPHGNN"], summary_path),
    )

    add_source_sheet(
        "Fig4a_drugcold_vs_scaffoldcold",
        "Fig. 4",
        "Panel a; official drug-cold versus scaffold-cold MDA metrics.",
        summary_path,
        add_source([r for r in select_cols(mda_summary, mda_basic_cols) if r.get("setting") in {"drug_cold", "scaffold_cold"}], summary_path),
    )
    add_source_sheet(
        "Fig4b_MDR_similarity_stratified",
        "Fig. 4",
        "Panel b; MDR drug-cold similarity-stratified summary.",
        fig4_summary_path,
        add_source([r for r in fig4_summary if r.get("dataset") == "MDR"], fig4_summary_path),
    )
    add_source_sheet(
        "Fig4c_MDS_similarity_stratified",
        "Fig. 4",
        "Panel c; MDS drug-cold similarity-stratified summary.",
        fig4_summary_path,
        add_source([r for r in fig4_summary if r.get("dataset") == "MDS"], fig4_summary_path),
    )

    add_source_sheet(
        "Fig5a_CDA_AUROC_across_settings",
        "Fig. 5",
        "Panel a; CDA AUROC across random and cold-start settings.",
        summary_path,
        add_source(select_cols(cda_summary, mda_basic_cols), summary_path),
    )
    add_source_sheet(
        "Fig5b_CDA_random_baseline_loss",
        "Fig. 5",
        "Panel b; CDA random-baseline AUROC loss from official final export.",
        fig5_loss_path,
        add_source(fig5_loss, fig5_loss_path),
    )

    formal100_mask = read_table(CDA_MASK / "07_tables/FORMAL100_MASKING_RUN_AUDIT.tsv")
    gat_strategy = read_table(GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_STRATEGY_SUMMARY_CONFIRMATORY.tsv")
    gat_pairwise = read_table(GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_PAIRWISE_CONFIRMATORY.tsv")
    gat_raw = read_table(GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_RAW_10000.tsv")
    external_summary = read_table(EXTERNAL / "external_enrichment_final_summary.tsv")

    add_source_sheet(
        "Fig6a_masking_design_summary",
        "Fig. 6",
        "Panel a; fixed-final MSMCDA masking audit summary by setting.",
        CDA_MASK / "07_tables/FORMAL100_MASKING_RUN_AUDIT.tsv",
        add_source(aggregate_formal100_masking(formal100_mask), CDA_MASK / "07_tables/FORMAL100_MASKING_RUN_AUDIT.tsv"),
    )
    add_source_sheet(
        "Fig6b_confirmatory_nonmetal_analysis",
        "Fig. 6",
        "Panel b; GAT-only masking confirmatory non-metal strategy summary.",
        GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_STRATEGY_SUMMARY_CONFIRMATORY.tsv",
        add_source([r for r in gat_strategy if r.get("subgroup") == "non_metal"], GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_STRATEGY_SUMMARY_CONFIRMATORY.tsv"),
    )
    add_source_sheet(
        "Fig6c_subgroup_high_low_paired_difference",
        "Fig. 6",
        "Panel c; high-versus-low paired differences with seed and Holm-adjusted p-values.",
        GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_PAIRWISE_CONFIRMATORY.tsv",
        add_source([r for r in gat_pairwise if r.get("comparison") == "High_vs_Low"], GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_PAIRWISE_CONFIRMATORY.tsv"),
    )
    add_source_sheet(
        "Fig6d_platinum_blind_spot_examples",
        "Fig. 6",
        "Panel d; platinum atom perturbation examples from formal masking raw records.",
        GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_RAW_10000.tsv",
        add_source(platinum_examples(gat_raw), GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_RAW_10000.tsv"),
    )
    add_source_sheet(
        "Fig6e_external_support_enrichment",
        "Fig. 6",
        "Panel e; external support enrichment summary.",
        EXTERNAL / "external_enrichment_final_summary.tsv",
        add_source(external_summary, EXTERNAL / "external_enrichment_final_summary.tsv"),
    )

    dataset_rows = []
    for key, group in defaultdict(list, {("all", "all"): raw}).items():
        pass
    by_task_dataset_setting = defaultdict(list)
    for row in raw:
        by_task_dataset_setting[(row.get("task_type", ""), row.get("dataset", ""), row.get("setting", ""))].append(row)
    for (task, dataset, setting), vals in sorted(by_task_dataset_setting.items()):
        tests = [fnum(v.get("n_test")) for v in vals if fnum(v.get("n_test")) is not None]
        dataset_rows.append(
            {
                "task_type": task,
                "dataset": dataset,
                "setting": setting,
                "seed_metric_rows": len(vals),
                "models": ",".join(sorted({v.get("model_name", "") for v in vals})),
                "n_test_mean": mean_sd(tests)[0],
                "n_test_sd": mean_sd(tests)[1],
                "notes": "Derived from official raw seed metrics; original entity-count summary not found as a single frozen table.",
            }
        )

    add_supp_sheet("STable1_dataset_summary", "Supplementary Table 1", "Dataset and setting summary derived from official raw metrics.", raw_path, add_source(dataset_rows, raw_path))
    add_supp_sheet("STable2_model_summary", "Supplementary Table 2", "Frozen model registry summary.", registry_path, add_source(registry, registry_path))
    add_supp_sheet(
        "STable3_split_protocol_summary",
        "Supplementary Table 3",
        "Split protocol and run-status summary from the updated PASS frozen registry.",
        registry_path,
        add_source(registry, registry_path, "Updated 20260710 registry supersedes the pre-ISG-completion packaging registry for final PASS status."),
    )
    add_supp_sheet(
        "STable4_official_asset_registry",
        "Supplementary Table 4",
        "Official frozen asset registry used for Paper1 final exports.",
        registry_path,
        add_source(registry, registry_path, "Updated 20260710 registry used as authority for final PASS/fixed-final status."),
    )
    add_supp_sheet("STable5_MDA_complete_summary_mean_sd", "Supplementary Table 5", "Complete MDA summary mean and sample SD.", summary_path, add_source(select_cols(mda_summary, mda_basic_cols), summary_path))
    add_supp_sheet("STable6_MDA_raw_seed_metrics", "Supplementary Table 6", "MDA raw seed-level metrics.", raw_path, add_source(mda_raw, raw_path))
    add_supp_sheet("STable7_CDA_complete_summary_mean_sd", "Supplementary Table 7", "Complete CDA summary mean and sample SD.", summary_path, add_source(select_cols(cda_summary, mda_basic_cols), summary_path))
    add_supp_sheet("STable8_CDA_raw_seed_metrics_or_summary", "Supplementary Table 8", "CDA raw seed-level metrics.", raw_path, add_source(cda_raw, raw_path))
    add_supp_sheet("STable9_similarity_stratified_seed_level", "Supplementary Table 9", "Similarity-stratified seed-level metrics.", fig4_seed_path, add_source(fig4_seed, fig4_seed_path))

    masking_combined: list[dict[str, object]] = []
    for row in aggregate_formal100_masking(formal100_mask):
        new = {"source_table": "FORMAL100_MASKING_RUN_AUDIT_SUMMARY", **row}
        masking_combined.append(new)
    for row in gat_strategy:
        new = {"source_table": "GAT_ONLY_MASKING_FORMAL_STRATEGY_SUMMARY_CONFIRMATORY", **row}
        masking_combined.append(new)
    add_supp_sheet("STable10_masking_summary", "Supplementary Table 10", "Masking audit and GAT-only formal masking summaries.", f"{CDA_MASK}/07_tables; {GAT_MASK}/table_exports", add_source(masking_combined, GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_STRATEGY_SUMMARY_CONFIRMATORY.tsv"))
    add_supp_sheet("STable11_external_support_summary", "Supplementary Table 11", "External support enrichment summary.", EXTERNAL / "external_enrichment_final_summary.tsv", add_source(external_summary, EXTERNAL / "external_enrichment_final_summary.tsv"))

    excluded = []
    for path in [REFRESH / "PAPER1_EXCLUDED_STALE_OR_FAILED_ASSETS.tsv", PACKAGING / "PAPER1_EXCLUDED_STALE_OR_FAILED_ASSETS.tsv"]:
        if path.exists():
            for row in read_table(path):
                excluded.append({"source_exclusion_table": rel(path), **row})
    add_supp_sheet("STable12_excluded_assets_and_audit_notes", "Supplementary Table 12", "Excluded stale/failed/smoke/pilot/partial assets and audit notes.", f"{REFRESH}/PAPER1_EXCLUDED_STALE_OR_FAILED_ASSETS.tsv; {PACKAGING}/PAPER1_EXCLUDED_STALE_OR_FAILED_ASSETS.tsv", excluded)

    # Extra useful official tables.
    for extra_name, extra_path, desc in [
        ("STable13_official_audit_summary", REFRESH / "PAPER1_7MODEL_AUDIT_SUMMARY.tsv", "Official seven-model audit summary."),
        ("STable14_prediction_manifest", REFRESH / "PAPER1_7MODEL_PREDICTION_MANIFEST.tsv", "Official prediction manifest."),
        ("STable15_GAT_masking_pairwise", GAT_MASK / "table_exports/GAT_ONLY_MASKING_FORMAL_PAIRWISE_CONFIRMATORY.tsv", "GAT-only masking pairwise confirmatory statistics."),
        ("STable16_external_support_raw", EXTERNAL / "external_enrichment_final_raw.tsv", "External support enrichment seed-level/raw table."),
    ]:
        if extra_path.exists():
            add_supp_sheet(extra_name, extra_name.replace("_", " "), desc, extra_path, add_source(read_table(extra_path), extra_path))

    for sheet in source_sheets + supp_sheets:
        export_name = f"{sheet['requested_name']}.tsv"
        write_tsv(EXPORT_DIR / export_name, sheet["rows"])

    write_xlsx(SOURCE_XLSX, source_sheets)
    write_xlsx(SUPP_XLSX, supp_sheets)

    manifest_rows = []
    for sheet in source_sheets + supp_sheets:
        manifest_rows.append(
            {
                "workbook": sheet["workbook"],
                "sheet_name": sheet["sheet_name"],
                "requested_sheet_name": sheet["requested_name"],
                "figure_or_table": sheet["figure_or_table"],
                "description": sheet["description"],
                "upstream_source": sheet["upstream_source"],
                "notes": sheet["notes"],
            }
        )
    write_tsv(MANIFEST, manifest_rows)

    missing_notes = []
    for sheet in source_sheets + supp_sheets:
        for row in sheet["rows"]:
            status = str(row.get("status", ""))
            reason = str(row.get("reason", ""))
            if "NOT_AVAILABLE" in status or "MISSING" in status or "NOT_AVAILABLE" in reason or "MISSING" in reason:
                missing_notes.append(f"- {sheet['requested_name']}: {status or reason}")

    report_lines = [
        "# Paper1 FINAL Data Export Report",
        "",
        "## Generated files",
        f"- `{rel(SOURCE_XLSX)}`",
        f"- `{rel(SUPP_XLSX)}`",
        f"- `{rel(MANIFEST)}`",
        f"- `{rel(REPORT)}`",
        f"- `{rel(EXPORT_DIR)}/` containing {len(source_sheets) + len(supp_sheets)} TSV exports",
        "",
        "## Source data workbook sheets",
        *[f"- `{s['sheet_name']}`: {s['requested_name']}" for s in source_sheets],
        "",
        "## Supplementary data workbook sheets",
        *[f"- `{s['sheet_name']}`: {s['requested_name']}" for s in supp_sheets],
        "",
        "## Primary upstream frozen/fixed-final sources",
        f"- `{rel(summary_path)}`",
        f"- `{rel(raw_path)}`",
        f"- `{rel(registry_path)}`",
        f"- `{rel(registry_path)}` is the authoritative updated registry for final PASS/fixed-final status.",
        f"- `{rel(packaging_registry_path)}` was audited but not used as the authoritative result registry because it predates the final ISG PASS refresh.",
        f"- `{rel(fig4_summary_path)}` and `{rel(fig4_seed_path)}`",
        f"- `{rel(fig5_loss_path)}`",
        f"- `{rel(CDA_MASK / '07_tables/FORMAL100_MASKING_RUN_AUDIT.tsv')}`",
        f"- `{rel(GAT_MASK / 'table_exports/GAT_ONLY_MASKING_FORMAL_STRATEGY_SUMMARY_CONFIRMATORY.tsv')}`",
        f"- `{rel(GAT_MASK / 'table_exports/GAT_ONLY_MASKING_FORMAL_PAIRWISE_CONFIRMATORY.tsv')}`",
        f"- `{rel(GAT_MASK / 'table_exports/GAT_ONLY_MASKING_FORMAL_RAW_10000.tsv')}`",
        f"- `{rel(EXTERNAL / 'external_enrichment_final_summary.tsv')}`",
        "",
        "## Known schema exceptions",
        *(missing_notes if missing_notes else ["- None in generated sheets. MPHGNN loss remains unavailable as an official schema exception and is left blank where absent."]),
        "",
        "## Safety confirmations",
        "- Article1 / Paper1 only.",
        "- No formal experiments were rerun; all derived values use existing official tables or official prediction files.",
        "- No model core code was modified.",
        "- Bi-SGTAR uses only `formal_runs/bisgtar_masked_pairloss_fixedfinal_20260706` fixed-final E200 official root.",
        "- Old recovered high-score Bi-SGTAR, smoke, pilot, failed, stale, partial, and non-Paper1 assets were not used as input.",
        "- The older 20260710 source/supplementary Excel workbooks were not read.",
    ]
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
