# Data Availability

## Included in This Repository

The repository includes small release-facing source-data and supplementary-data files under:

```text
results/source_data/
```

These files are suitable for GitHub when size limits and journal policy allow.

## Not Included

The following are intentionally not committed:

- full raw MDA/CDA datasets;
- full `formal_runs/` output trees;
- model checkpoints and weights;
- raw prediction dumps beyond curated source data;
- slurm logs and cluster submission records;
- local cache mirrors;
- private path provenance tables that expose local usernames or filesystem layout.

## Preparing Data

For full reproduction, place input data under `data/` using the structure described in `data/README.md`. For example:

```text
data/
  MDR/
  MDS/
  CDA/
```

The exact files required depend on the model being reproduced. Use the official run provenance in the frozen roots to confirm filenames and hashes.

## Data Checks

Use SHA256 checksums where available:

```bash
sha256sum <file>
```

Release-facing source-data checksums are recorded in:

```text
docs/CHECKSUMS_SHA256.txt
```

## External Archival Recommendation

Large raw data, complete predictions, and frozen formal outputs should be archived outside git, for example in a GitHub Release, Zenodo, Figshare, OSF, or institutional storage. External archive information will be finalized by the repository owners.
