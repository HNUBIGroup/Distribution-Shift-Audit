# Results Directory

`results/source_data/` contains small, release-facing Paper1 source-data tables copied from the frozen/fixed-final/PASS refresh outputs.

It intentionally does not contain:

- full `formal_runs/` directories;
- checkpoints or model weights;
- slurm logs;
- smoke, pilot, failed, partial, stale, temporary, or recovered high-score assets;
- large raw prediction dumps beyond curated source-data tables.

The authoritative local frozen roots are listed in `docs/OFFICIAL_ASSETS.md`. Use `scripts/verify_official_assets.py` to check that those roots exist in a full local reproduction workspace.

