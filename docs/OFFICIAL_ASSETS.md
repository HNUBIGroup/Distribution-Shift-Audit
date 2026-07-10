# Official Assets

This file defines the only formal Paper1 result roots that may be used for README tables, figures, supplementary data, source data, and GitHub packaging.

The machine-readable registry is:

```text
results/source_data/PAPER1_FROZEN_MODEL_REGISTRY.tsv
```

## Official Frozen Roots

| Model | Task | Official root | Status |
| --- | --- | --- | --- |
| ISG-MDA | MDA | `formal_runs/isg_clean_fixedfinal_20260706` | fixed-final PASS |
| PLMF-MDA | MDA | `formal_runs/full_metric_rerun_20260615/plmf_standardized_repair_20260619` | fixed-final PASS |
| MGCNA | MDA | `formal_runs/mgcna_corrected_fast_full125_fixedfinal_20260629` | fixed-final PASS |
| DLST-MDA | MDA | `formal_runs/dlst_native_fixedfinal_fullmetric_20260623` | fixed-final PASS |
| MPHGNN | MDA | `formal_runs/native_mda_audit_20260601/MPHGNN_STRICT_FORMAL_GUARD_20260614` | fixed-test official PASS |
| MSMCDA | CDA | `formal_runs/cda_msmcda_corrected_fullmetric_20260619` | official PASS |
| Bi-SGTAR | CDA | `formal_runs/bisgtar_masked_pairloss_fixedfinal_20260706` | fixed-final E200 official PASS |

## Bi-SGTAR Rule

Bi-SGTAR must use the fixed-final E200 low-score official version:

```text
formal_runs/bisgtar_masked_pairloss_fixedfinal_20260706
```

Old recovered/locked high-score Bi-SGTAR outputs may be retained only as excluded/provenance records. They must not enter README, figure, supplementary, source-data, or GitHub formal result packaging.

## Excluded Classes

Exclude all paths or assets marked or named as:

- smoke
- pilot
- tmp or temp
- failed
- partial
- stale
- recovered
- old
- backup or `.bak`
- slurm-only logs
- checkpoint-only outputs

## Verification

Run:

```bash
python scripts/verify_official_assets.py --project-root .
```

Use `--allow-missing` when checking a GitHub clone that intentionally does not include full formal run trees.

