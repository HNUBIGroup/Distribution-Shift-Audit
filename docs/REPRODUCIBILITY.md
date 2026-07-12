# Reproducibility

This document describes the Article1/Paper1 reproducibility contract for the sparse RNA association prediction reliability audit.

## Scope

Use only frozen/fixed-final/PASS results listed in `docs/OFFICIAL_ASSETS.md`. Do not use smoke, pilot, temporary, failed, partial, stale, recovered, or old high-score Bi-SGTAR outputs as formal results.

## Evaluation Settings

MDA settings:

- `random`
- `miRNA_cold` / `mirna_cold`
- `drug_cold`
- `strict_cold`
- `scaffold_cold`

CDA settings:

- `random`
- `circRNA_cold` / `circrna_cold`
- `disease_cold`
- `strict_cold`

The fixed-final registry in `results/source_data/PAPER1_FROZEN_MODEL_REGISTRY.tsv` records the expected and completed run counts for each model.

## Seeds

Formal summaries use seed-level metrics from the official frozen roots. Most formal tables use 25 seeds per dataset/setting combination. Registry fields `expected_runs` and `actual_complete_runs` define the official run count for each model.

## Metrics

Reported metrics include:

- AUROC
- AUPR
- ACC
- F1
- MCC
- Brier
- ECE
- NLL
- loss, when available

Missing loss values are not imputed. MPHGNN uses an AUC-to-AUROC schema mapping noted in the registry.

## Mean +/- SD

Mean and standard deviation are computed from raw seed-level metrics:

```bash
python scripts/make_summary_tables.py \
  --raw-metrics results/source_data/PAPER1_7MODEL_RAW_SEED_METRICS.tsv \
  --output-dir results/source_data
```

The output should be compared against:

```text
results/source_data/PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv
```

## Fig.2-Fig.6 Source Data

Curated source-data files are staged in `results/source_data/`.

- Fig.2 distribution shift: `PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv`
- Fig.3 calibration/decision metrics: `Paper1_Source_Data_FINAL.xlsx`
- Fig.4 similarity/cold-start source data: `Fig4_similarity_stratified_final.tsv`, `Fig4_similarity_stratified_seed_metrics.tsv`
- Fig.5 CDA random-baseline loss: `Fig5_CDA_random_baseline_loss_final.tsv`
- Fig.6 summary/supplementary assets: `Paper1_Supplementary_Data_FINAL.xlsx`

To refresh staged source data from local frozen outputs:

```bash
python scripts/make_source_data.py --project-root . --output-dir results/source_data
```

## Official Frozen Results

The frozen roots are listed in `docs/OFFICIAL_ASSETS.md` and in:

```text
results/source_data/PAPER1_FROZEN_MODEL_REGISTRY.tsv
```

Use `scripts/verify_official_assets.py` before rebuilding summaries from a full local workspace.

## Excluded Results

Do not use:

- smoke or pilot outputs;
- failed, partial, or stale runs;
- temporary debug outputs;
- backup or recovered outputs;
- old recovered/locked high-score Bi-SGTAR assets;
- full `formal_runs/` trees copied into git.

Excluded/provenance records can be kept locally for audit purposes, but they are not formal results.
