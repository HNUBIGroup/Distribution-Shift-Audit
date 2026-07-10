# Model Card

## Task

Sparse RNA association prediction reliability audit across MDA and CDA models.

## Inputs

Inputs depend on the model and task, and may include:

- miRNA identifiers or sequence-derived features;
- drug identifiers, SMILES, molecular graph features, or chemical fingerprints;
- circRNA and disease identifiers or associated feature matrices;
- train/test split metadata for random, cold-start, strict-cold, and scaffold-cold settings.

## Outputs

Models output association scores or probabilities for RNA-related entity pairs. Evaluation scripts convert these predictions into AUROC, AUPR, calibration, decision, and error metrics.

## Intended Use

This code is intended for research reproducibility, auditing model reliability under distribution shift, and generating source data for the associated Paper1 figures and supplementary tables.

## Not Intended For

The models and outputs are not intended for clinical diagnosis, treatment selection, direct patient management, or unsupervised deployment in biomedical decision systems.

## Known Limitations

- Performance can degrade strongly under cold-start and strict-cold settings.
- Calibration may be poor even when ranking metrics appear acceptable.
- Sparse labels and negative sampling assumptions can affect AUPR and decision metrics.
- Some baseline implementations have model-specific schema exceptions; see the official registry.
- Full reproduction depends on external data and local frozen formal outputs that are not committed to git.

## Distribution Shift Risks

Random splits can overstate reliability for deployment settings where drugs, RNAs, circRNAs, or diseases are unseen during training. Always inspect cold-start, strict-cold, and scaffold-cold results before interpreting model utility.

## Calibration and Decision Failure Risks

High AUROC or AUPR does not guarantee calibrated probabilities or useful decision thresholds. Decision-failure and prediction-level audit outputs should be reviewed before using scores to prioritize experiments.

