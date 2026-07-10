# Packaging Privacy Audit

This audit records privacy and packaging risks found during repository preparation. It does not delete or alter formal scientific outputs.

## Summary

The current local workspace contains many files that are not appropriate for public GitHub upload. The `.gitignore` excludes these by default, and curated release-facing assets are staged under `results/source_data/`.

## Risk Classes

| Risk type | Examples observed | Recommended handling |
| --- | --- | --- |
| Absolute local paths | `/home/...` paths in provenance, logs, and generated reports | Keep out of public source-data unless redacted; document official roots as relative paths |
| Username/path leakage | local username appears in absolute paths | Do not publish raw logs or unredacted provenance tables |
| Slurm/internal cluster details | `.out`, `.err`, job ids, node/job scripts | Exclude from git; keep only methodological descriptions |
| Checkpoints/model weights | `.pt`, `.pth`, `.ckpt` files | Archive externally only if needed; do not commit |
| Smoke/pilot/failed/partial/stale/recovered assets | numerous historical audit and run paths | Exclude from formal results and git packaging |
| Old Bi-SGTAR recovered/high-score assets | old/recovered/locked provenance records | Keep only as excluded provenance; never use as formal results |
| Large formal outputs | complete `formal_runs/`, `outputs_*`, raw predictions | Exclude from git; archive externally if needed |
| Private data mirrors | full raw data paths under local data/formal provenance | Provide data preparation instructions instead |

## Files/Directories To Exclude

- `formal_runs/`
- `release_audit/`
- `audit/`
- `outputs/` and `outputs_*/`
- `slurm/`
- `archive/`
- `DeepChem/`
- checkpoint and log files

## Follow-up Before Public Release

- Review `results/source_data/*.xlsx` for embedded absolute paths if journal policy requires fully redacted public files.
- Add public data/archive URLs or DOI to `docs/DATA_AVAILABILITY.md`.
- Confirm final license compatibility for third-party baseline code.
