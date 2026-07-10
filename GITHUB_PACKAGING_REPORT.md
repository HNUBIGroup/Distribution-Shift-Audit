# GitHub Packaging Report

Date: 2026-07-11

Local project root used during packaging:

```text
<LOCAL_PROJECT_ROOT>/PLMF_clean
```

## 1. Files Added or Modified

Repository metadata:

- `README.md`
- `.gitignore`
- `environment.yml`
- `requirements.txt`
- `pyproject.toml`
- `CITATION.cff`
- `LICENSE_TODO.md`

Documentation:

- `docs/REPRODUCIBILITY.md`
- `docs/DATA_AVAILABILITY.md`
- `docs/OFFICIAL_ASSETS.md`
- `docs/MODEL_CARD.md`
- `docs/PACKAGING_PRIVACY_AUDIT.md`
- `docs/CHECKSUMS_SHA256.txt`

Script entry points:

- `scripts/check_environment.py`
- `scripts/run_smoke_test.sh`
- `scripts/collect_seed_metrics.py`
- `scripts/make_summary_tables.py`
- `scripts/make_source_data.py`
- `scripts/verify_official_assets.py`

Packaging directories:

- `data/README.md`
- `data/example/.gitkeep`
- `results/README.md`
- `results/source_data/`
- `src/README.md`
- `examples/README.md`
- `tests/README.md`

Curated source-data assets staged:

- `results/source_data/PAPER1_FROZEN_MODEL_REGISTRY.tsv`
- `results/source_data/PAPER1_7MODEL_AUDIT_SUMMARY.tsv`
- `results/source_data/PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv`
- `results/source_data/PAPER1_7MODEL_RAW_SEED_METRICS.tsv`
- `results/source_data/Fig4_similarity_stratified_final.tsv`
- `results/source_data/Fig4_similarity_stratified_seed_metrics.tsv`
- `results/source_data/Fig5_CDA_random_baseline_loss_final.tsv`
- `results/source_data/Source_Data_Paper1_20260710.xlsx`
- `results/source_data/Supplementary_Data_Paper1_20260710.xlsx`

The staged source-data copies were redacted for local absolute paths and then checksummed.

## 2. Recommended Files To Include in GitHub

Include:

- top-level model and preprocessing code needed for Article1/Paper1, after final review;
- `README.md`;
- `.gitignore`;
- `environment.yml`;
- `requirements.txt`;
- `pyproject.toml`;
- `CITATION.cff`;
- `LICENSE_TODO.md`;
- `configs/`;
- curated scripts listed above;
- `docs/`;
- `data/README.md`;
- `data/example/`;
- `results/README.md`;
- `results/source_data/`;
- `examples/`;
- `tests/`.

Core existing script-oriented code candidates:

- `train.py`, `train_v2_*.py`;
- `layers.py`, `layers_v2_*.py`, `layers_gat.py`;
- `data_preprocess.py`, `data_preprocess_scaffold.py`;
- `split_utils.py`, `split_utils_scaffold.py`;
- `build_drug_graph.py`, `build_mirna_graph.py`;
- selected figure/source-data generation scripts: `scripts/paper1_data_refresh_20260710.py` and `scripts/recompute_fig4_similarity_stratified_final.py`.

Review these existing top-level files before `git add` to exclude backups, submit scripts, and historical debug artifacts.

## 3. Recommended Files Not To Include in GitHub

Exclude:

- `formal_runs/`;
- `release_audit/`;
- `audit/`;
- `audit_reports/`;
- `archive/`;
- `outputs/` and `outputs_*/`;
- `DeepChem/`;
- `slurm/`;
- `status/`;
- `candidate_manifests/`;
- raw full `data/` contents except README/example files;
- checkpoint/model weight files: `*.pt`, `*.pth`, `*.ckpt`;
- logs and cluster output: `*.log`, `*.out`, `*.err`, `slurm-*`;
- zip/tar archives;
- smoke, pilot, tmp, failed, partial, stale, recovered, old, backup, and `.bak` outputs;
- old recovered/locked high-score Bi-SGTAR assets.

## 4. Manual Confirmation Still Needed

- Confirm final author list, repository URL, DOI, journal, and year in `CITATION.cff`.
- Choose a final license after reviewing third-party baseline code and data licensing.
- Decide whether to publish source-data workbooks directly in git or move them to GitHub Release/Zenodo.
- Add final public data/archive URL to `docs/DATA_AVAILABILITY.md`.
- Review top-level historical scripts before adding them to git; many submit/debug scripts should remain excluded.
- Resolve the local `torch` import issue before running training or strict environment CI.

## 5. License Status

No final license was selected. `LICENSE_TODO.md` was created. MIT may be reasonable for code if third-party and data constraints permit, but this needs human confirmation.

## 6. Data Release Recommendation

Small curated source-data files are staged under `results/source_data/` and checksummed in `docs/CHECKSUMS_SHA256.txt`.

Full raw datasets, complete formal run outputs, checkpoints, and raw prediction archives should not be committed. Use GitHub Release, Zenodo, Figshare, OSF, or institutional storage and cite the final URL/DOI in `docs/DATA_AVAILABILITY.md`.

## 7. Privacy and Path Leakage

Privacy risks were found in the full local workspace:

- absolute `/home/...` paths;
- local username in paths;
- slurm job ids and cluster logs;
- local data mirrors;
- old/recovered/stale provenance records.

These risks are documented in `docs/PACKAGING_PRIVACY_AUDIT.md`. Curated files under `results/source_data/` were checked after redaction and no `/home/` or local username hits remained.

## 8. Validation Performed

Completed:

- verified required packaging files exist;
- ran `scripts/run_smoke_test.sh` successfully;
- verified official asset registry and status markers in the local full workspace;
- checked script `--help` for new Python entry points under the `plmf` environment;
- checked curated source-data files for obvious local absolute path leakage;
- generated `docs/CHECKSUMS_SHA256.txt`.

Known environment issue:

```text
torch import failed in the current plmf environment:
libtorch_cuda.so: failed to map segment from shared object
```

`run_smoke_test.sh` uses `check_environment.py --warn-only` so packaging/source-data checks still run. Fix PyTorch/CUDA before training or GPU reproducibility work.

## 9. Suggested Git Initialization Commands

Do not push until manual license/data review is complete.

```bash
git init
git status
git add README.md .gitignore environment.yml requirements.txt pyproject.toml CITATION.cff LICENSE_TODO.md
git add docs/ data/ results/ examples/ tests/ src/
git add scripts/check_environment.py scripts/run_smoke_test.sh scripts/collect_seed_metrics.py scripts/make_summary_tables.py scripts/make_source_data.py scripts/verify_official_assets.py scripts/paper1_data_refresh_20260710.py scripts/recompute_fig4_similarity_stratified_final.py
git add configs/
git add train.py train_v2_*.py layers.py layers_v2_*.py layers_gat.py data_preprocess.py data_preprocess_scaffold.py split_utils.py split_utils_scaffold.py build_drug_graph.py build_mirna_graph.py
git status
git commit -m "Package reproducible code and source data for release"
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```

Before committing, inspect `git status` carefully and ensure no full formal outputs, checkpoints, logs, raw data, or excluded Bi-SGTAR assets are staged.
