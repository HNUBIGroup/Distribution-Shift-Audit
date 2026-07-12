# Sparse RNA Association Prediction Reliability Audit

This repository packages the Article1/Paper1 code, source data, and reproducibility notes for a reliability audit of sparse RNA association prediction models. The study evaluates MDA and CDA models under distribution shift, cold-start, strict-cold, scaffold-cold, calibration, decision-failure, and prediction-level audit settings.

The repository is organized for transparent reuse of frozen/fixed-final/PASS results. It does not include full raw datasets, full formal run trees, checkpoints, slurm logs, or historical failed/smoke/pilot/recovered outputs.

## Main Features

- MDA model code and preprocessing utilities for miRNA-drug association experiments.
- Evaluation utilities for AUROC, AUPR, ACC, F1, MCC, Brier, ECE, and NLL.
- Source-data generation scripts for Paper1 figures and supplementary tables.
- Official asset manifest that distinguishes fixed-final/PASS results from excluded historical runs.
- Packaging checks for environment, official assets, and source-data tables.

## Repository Structure

```text
.
├── README.md
├── CITATION.cff
├── environment.yml
├── requirements.txt
├── configs/
├── scripts/
├── data/
│   ├── README.md
│   └── example/
├── results/
│   ├── README.md
│   └── source_data/
├── docs/
│   ├── REPRODUCIBILITY.md
│   ├── DATA_AVAILABILITY.md
│   ├── MODEL_CARD.md
│   └── OFFICIAL_ASSETS.md
└── tests/
```

The current research code is script-oriented. Core historical entry points remain at the repository top level to avoid changing validated experiment behavior.

Repository URL: <https://github.com/HNUBIGroup/Distribution-Shift-Audit>

## Installation

Conda is recommended:

```bash
conda env create -f environment.yml
conda activate sparse-rna-reliability
python scripts/check_environment.py
```

If you already have the original local environment:

```bash
conda activate plmf
python scripts/check_environment.py
```

A pip fallback is provided:

```bash
python -m pip install -r requirements.txt
```

Some baseline models may require CUDA-specific packages such as PyTorch Geometric or DGL. Install those according to your CUDA/PyTorch version.

## Quick Start

Run packaging-level checks without launching formal experiments:

```bash
bash scripts/run_smoke_test.sh
```

Verify local official result roots if you have the full reproduction workspace:

```bash
python scripts/verify_official_assets.py --project-root . --allow-missing
```

Inspect curated source data:

```bash
python scripts/make_summary_tables.py \
  --raw-metrics results/source_data/PAPER1_7MODEL_RAW_SEED_METRICS.tsv \
  --output-dir results/source_data
```

## Minimal Smoke Test

The smoke test checks the Python environment, confirms that curated source-data files are readable, and validates official asset metadata when available. It does not train a model and does not run formal experiments.

```bash
bash scripts/run_smoke_test.sh
```

## Reproducing Metrics

Formal metrics are summarized as mean +/- standard deviation across seeds from raw seed-level metrics. Curated Paper1 source-data tables are in `results/source_data/`.

To regenerate a summary table from raw seed metrics:

```bash
python scripts/make_summary_tables.py \
  --raw-metrics results/source_data/PAPER1_7MODEL_RAW_SEED_METRICS.tsv \
  --output-dir results/source_data
```

To collect seed metrics from a local formal run root:

```bash
python scripts/collect_seed_metrics.py \
  --project-root . \
  --registry results/source_data/PAPER1_FROZEN_MODEL_REGISTRY.tsv \
  --output-dir results/source_data
```

See `docs/REPRODUCIBILITY.md` for the evaluated settings, seed counts, metrics, and official/excluded result rules.

## Generating Source Data and Supplementary Data

Curated release-facing assets are already staged under `results/source_data/`.

To copy the current frozen refresh outputs into a target source-data directory:

```bash
python scripts/make_source_data.py \
  --project-root . \
  --output-dir results/source_data
```

For Fig.4 similarity-stratified source data, use:

```bash
python scripts/recompute_fig4_similarity_stratified_final.py
```

This script uses final ISG drug-cold predictions and provenance-verified drug SMILES assets. It writes to `outputs/paper1_data_refresh_20260710/` and does not modify seed outputs.

## Data Availability

Full raw datasets and full formal run outputs are not committed to git. See `docs/DATA_AVAILABILITY.md` for data preparation, expected paths, and checksum guidance.

Small source-data and supplementary-data files are provided under `results/source_data/`. Larger raw data, checkpoints, and full prediction archives should be distributed through an external archive such as a GitHub Release, Zenodo, Figshare, OSF, or institutional storage.

## Official Results

Only frozen/fixed-final/PASS roots listed in `docs/OFFICIAL_ASSETS.md` are valid for README, figure, supplementary, source-data, and GitHub packaging. In particular, Bi-SGTAR must use the fixed-final E200 low-score official version:

```text
formal_runs/bisgtar_masked_pairloss_fixedfinal_20260706
```

Old recovered/locked high-score Bi-SGTAR outputs are excluded and must not be used as formal results.

## Citation

Use `CITATION.cff` for citation metadata. Manuscript bibliographic details that are not yet public will be finalized by the repository owners.

## License

License information will be finalized by the repository owners. Review third-party baseline code and data provenance before public release.

## Contact

Use the GitHub repository issue tracker for public release questions.
