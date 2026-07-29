# Dataset Admission Audit Report

## Status

Phase 0 (protocol and registry framework) is complete. No candidate has yet passed a hard gate, received a numeric admission score, or been frozen. The candidate registry contains source locators only; they require official-source inspection before any factual task-level fields can be populated.

## Scope controls observed

- No model training or evaluation was run.
- No external benchmark data were downloaded.
- No Article1 path or Article3 path was entered or modified.
- No `scvc_gears` or `scvc_gpu` environment was used.
- Existing Article2 frozen prediction assets were not changed.

## Baseline project evidence

Stage 0 is recorded PASS. Stage 1 is recorded PASS with 825 prediction records: 700 `COMPLETE` and 125 `PROVENANCE_UNRESOLVED`. Scaffold sidecars are recorded for all 125 scaffold-cold prediction records; PLMF pair IDs are recorded as reconstructed and metric-verified. MPHGNN remains diagnostic-only because original cold-split train/test pair overlap is unresolved. These facts define the biological application boundary and do not establish admission for any new benchmark.

## Pending audit work

1. Inspect official metadata/papers/loaders for each listed candidate and create evidence records.
2. Populate task rows, source/version/access records, shift/group semantics, and target support without downloading prohibited assets.
3. Audit TGB package/data/negative-sample versions and MIMIC credentialing/DUA/non-redistribution constraints.
4. Score only verified rows, build redundancy links, then propose (not freeze) a 15--20 task shortlist and a pilot.

## Counts at this checkpoint

Candidate tasks enumerated: 34. Hard-gate passes: 0 (not yet assessed). Candidate Primary/Secondary/Diagnostic/Excluded: 0/0/0/0. Deprecated `ogbl-citation` is a separate policy exclusion recorded in `dataset_exclusion_log.tsv`; it is not included in the candidate pool. Modality, shift, dependency, access, leakage, cost, redundancy, and replication counts are intentionally not reported until official evidence is entered.

The provisional pilot list is not frozen. It may be assessed later against TableShift-Income, CivilComments, Camelyon17, and either tgbl-wiki-v2 or ogbl-collab, but only after the same hard-gate audit.
