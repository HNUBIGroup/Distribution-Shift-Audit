# Paper1 FINAL Data Export Report

## Generated files
- `results/source_data/Paper1_Source_Data_FINAL.xlsx`
- `results/source_data/Paper1_Supplementary_Data_FINAL.xlsx`
- `results/source_data/Paper1_data_manifest.tsv`
- `results/source_data/Paper1_data_export_report.md`
- `results/source_data/final_exports/` containing 33 TSV exports

## Source data workbook sheets
- `Fig2a_AUROC_across_shifts`: Fig2a_AUROC_across_shifts
- `Fig2b_AUPR_across_shifts`: Fig2b_AUPR_across_shifts
- `Fig2c_delta_AUROC_random_minus_`: Fig2c_delta_AUROC_random_minus_shifted
- `Fig3a_AUROC_vs_F1_all_MDA_combi`: Fig3a_AUROC_vs_F1_all_MDA_combinations
- `Fig3b_AUROC_vs_ECE_all_MDA_comb`: Fig3b_AUROC_vs_ECE_all_MDA_combinations
- `Fig3c_MPHGNN_calibration_curve_`: Fig3c_MPHGNN_calibration_curve_bins
- `Fig3d_MPHGNN_representative_met`: Fig3d_MPHGNN_representative_metrics
- `Fig4a_drugcold_vs_scaffoldcold`: Fig4a_drugcold_vs_scaffoldcold
- `Fig4b_MDR_similarity_stratified`: Fig4b_MDR_similarity_stratified
- `Fig4c_MDS_similarity_stratified`: Fig4c_MDS_similarity_stratified
- `Fig5a_CDA_AUROC_across_settings`: Fig5a_CDA_AUROC_across_settings
- `Fig5b_CDA_random_baseline_loss`: Fig5b_CDA_random_baseline_loss
- `Fig6a_masking_design_summary`: Fig6a_masking_design_summary
- `Fig6b_confirmatory_nonmetal_ana`: Fig6b_confirmatory_nonmetal_analysis
- `Fig6c_subgroup_high_low_paired_`: Fig6c_subgroup_high_low_paired_difference
- `Fig6d_platinum_blind_spot_examp`: Fig6d_platinum_blind_spot_examples
- `Fig6e_external_support_enrichme`: Fig6e_external_support_enrichment

## Supplementary data workbook sheets
- `STable1_dataset_summary`: STable1_dataset_summary
- `STable2_model_summary`: STable2_model_summary
- `STable3_split_protocol_summary`: STable3_split_protocol_summary
- `STable4_official_asset_registry`: STable4_official_asset_registry
- `STable5_MDA_complete_summary_me`: STable5_MDA_complete_summary_mean_sd
- `STable6_MDA_raw_seed_metrics`: STable6_MDA_raw_seed_metrics
- `STable7_CDA_complete_summary_me`: STable7_CDA_complete_summary_mean_sd
- `STable8_CDA_raw_seed_metrics_or`: STable8_CDA_raw_seed_metrics_or_summary
- `STable9_similarity_stratified_s`: STable9_similarity_stratified_seed_level
- `STable10_masking_summary`: STable10_masking_summary
- `STable11_external_support_summa`: STable11_external_support_summary
- `STable12_excluded_assets_and_au`: STable12_excluded_assets_and_audit_notes
- `STable13_official_audit_summary`: STable13_official_audit_summary
- `STable14_prediction_manifest`: STable14_prediction_manifest
- `STable15_GAT_masking_pairwise`: STable15_GAT_masking_pairwise
- `STable16_external_support_raw`: STable16_external_support_raw

## Primary upstream frozen/fixed-final sources
- `outputs/paper1_data_refresh_20260710/PAPER1_7MODEL_SUMMARY_MEAN_SD.tsv`
- `outputs/paper1_data_refresh_20260710/PAPER1_7MODEL_RAW_SEED_METRICS.tsv`
- `outputs/paper1_data_refresh_20260710/PAPER1_FROZEN_MODEL_REGISTRY.tsv`
- `outputs/paper1_data_refresh_20260710/PAPER1_FROZEN_MODEL_REGISTRY.tsv` is the authoritative updated registry for final PASS/fixed-final status.
- `formal_runs/paper1_github_packaging_registry_20260708/PAPER1_FROZEN_MODEL_ASSET_REGISTRY.tsv` was audited but not used as the authoritative result registry because it predates the final ISG PASS refresh.
- `outputs/paper1_data_refresh_20260710/Fig4_similarity_stratified_final.tsv` and `outputs/paper1_data_refresh_20260710/Fig4_similarity_stratified_seed_metrics.tsv`
- `outputs/paper1_data_refresh_20260710/Fig5_CDA_random_baseline_loss_final.tsv`
- `formal_runs/cda_msmcda_native_maskedcold_full100_fixedfinal_20260701/07_tables/FORMAL100_MASKING_RUN_AUDIT.tsv`
- `formal_runs/gat_only_masking_formal_20260625/table_exports/GAT_ONLY_MASKING_FORMAL_STRATEGY_SUMMARY_CONFIRMATORY.tsv`
- `formal_runs/gat_only_masking_formal_20260625/table_exports/GAT_ONLY_MASKING_FORMAL_PAIRWISE_CONFIRMATORY.tsv`
- `formal_runs/gat_only_masking_formal_20260625/table_exports/GAT_ONLY_MASKING_FORMAL_RAW_10000.tsv`
- `formal_runs/table_exports/external_enrichment_final_summary.tsv`

## Known schema exceptions
- None in generated sheets. MPHGNN loss remains unavailable as an official schema exception and is left blank where absent.

## Safety confirmations
- Article1 / Paper1 only.
- No formal experiments were rerun; all derived values use existing official tables or official prediction files.
- No model core code was modified.
- Bi-SGTAR uses only `formal_runs/bisgtar_masked_pairloss_fixedfinal_20260706` fixed-final E200 official root.
- Old recovered high-score Bi-SGTAR, smoke, pilot, failed, stale, partial, and non-Paper1 assets were not used as input.
- The older 20260710 source/supplementary Excel workbooks were not read.
