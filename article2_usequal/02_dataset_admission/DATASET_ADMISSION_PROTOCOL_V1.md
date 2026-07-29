# UseQual Dataset Admission Protocol V1

## Status and scope

- Protocol ID: `USEQUAL_DATASET_ADMISSION_V1`
- Created: `2026-07-29`
- Project: *Use-aware Model Qualification under Distribution Shift* (UseQual)
- Scope: admission of frozen-prediction evaluation tasks for general binary classification and binary relation prediction.
- This protocol is pre-performance and outcome-blind. It neither trains models nor changes an admission decision in response to observed model performance.

The unit of assessment is one **dataset task and its frozen split version**, not a seed, a model run, or a source family. A task enters the method only through frozen records containing `y_true`, continuous `y_prob`/`y_score`, appropriate group or entity identifiers, split/shift metadata, intended use, and qualification requirements. Existing MDR/MDS/CircRNA relation evidence is an application block only; it cannot supply the non-biological main evidence.

## Evidence standard

Every factual cell must cite an official paper, official benchmark site, official repository, or original data documentation. Evidence records use a source URL/path, access date, evidence type, quoted locator, and verification state. A URL placed in a registry before source inspection is a **source locator**, not verification. Unknown fields are `UNRESOLVED`; they must never be inferred from a model paper, a third-party loader, or a favorable result.

Permitted metadata/loader inspection is read-only and may not trigger large downloads. Camelyon17, MIMIC, ogbl-citation2, tgbl-comment, and tgbl-flight are explicitly download-prohibited in this stage. MIMIC access must record credentialing, DUA, and non-redistribution requirements. Yearbook must record the gender/sensitive-attribute and ethical-risk assessment. TGB records must separately pin data, package, and negative-sample versions.

## Hard gates

| Gate | Requirement | Failure handling |
|---|---|---|
| G1 | Native binary classification or native binary relation prediction | Exclude; no arbitrary multiclass binarization. |
| G2 | Real, interpretable distribution shift | Exclude random-split-only tasks and artificial corruption as primary evidence. |
| G3 | Auditable group/domain/time/entity metadata | Exclude or hold pending an official metadata audit. |
| G4 | Official or preregistrably frozen split | Exclude if only a mutable/random split is available. |
| G5 | Target-domain statistical support | Hold/exclude if prespecified support thresholds fail. |
| G6 | Continuous score or probability can be retained | Exclude label-only interfaces. |
| G7 | Main task supports at least three model families | Hold pending a documented feasibility plan. |
| G8 | Duplicate, entity, temporal, label, and negative-sampling audits are possible | Exclude if key leakage controls cannot be audited. |
| G9 | Source, version, licence, and access requirements are clear | Hold pending official confirmation. |
| G10 | Source-family dependence is disclosed | Collapse correlated tasks into a redundancy family; do not count as independent evidence. |

`UNASSESSED`, `PENDING_OFFICIAL_VERIFICATION`, and `UNRESOLVED` are not passes. A hard-gate pass must be supported by evidence records.

## Prespecified screen

For ordinary binary classification, screen target data using: `target_n >= 1000`, `target_positive_n >= 100`, `target_negative_n >= 100`, and `effective_group_n >= 20`. For binary relation prediction, use: `target_positive_edges >= 500`, `target_left_entities >= 50`, `target_right_entities >= 50`, and an explicit negative-sampling protocol. These are preliminary data screens, not final qualification-evidence thresholds, and cannot be revised from model results.

## Scoring and role allocation

Score only after G1--G10 evidence is completed: shift/deployment semantics (20), group metadata (15), target support (15), split/version/source (10), model-family support (10), modality/domain value (10), ranking/decision/probability coverage (10), and access/licence/compute feasibility (10). Roles are: Primary confirmatory `>=80` plus all hard gates; Secondary replication `65--79`; Diagnostic/stress `50--64` or primarily artificial shift; Excluded `<50` or a critical gate failure. Scores are `UNSCORED` until the underlying cells are verified.

## Independence, leakage, and use controls

- Multiple seeds, reweightings, or splits of one source are not independent datasets.
- TableShift, MIMIC, TGB, and biological relation tasks remain linked within their redundancy families.
- Random splits are sanity checks only, never distribution-shift evidence.
- Duplicate rows, train/test entity intersection, timestamp ordering, target/feature leakage, and the provenance of every negative edge must be checked before admission.
- `ogbl-citation` is deprecated and excluded; only `ogbl-citation2` is a candidate.
- No task may be admitted by expected AUROC, calibration, ranking, or decision performance.

## Required artifacts and decision states

The TSV files in this directory are the authoritative machine-readable ledger. Each datasheet must preserve raw counts separately from derived screening decisions. `dataset_exclusion_log.tsv` records any gate failure without deleting the candidate. `dataset_redundancy_graph.tsv` names shared source/collection/labeling dependencies. The audit report may recommend a 15--20 task set, but it cannot freeze one; freeze requires a dated protocol amendment and complete official evidence.

## Environment boundary

This admission stage creates Markdown/TSV only and uses no data loader, training, or large asset download. The existing `plmf` environment is documented for legacy Article2 sidecar parsing only. There is currently no independent UseQual environment specification; any future environment proposal must be based on pinned loader/import requirements and must not use `scvc_gears` or `scvc_gpu`.
