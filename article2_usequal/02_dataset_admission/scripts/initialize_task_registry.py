"""Create a deliberately unresolved task-level admission ledger from candidates.

This is metadata scaffolding only: it reads no benchmark asset, downloads
nothing, trains nothing, and treats a source locator as unverified evidence.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dataset_candidate_registry.tsv"
DESTINATION = ROOT / "dataset_task_registry.tsv"


def main() -> None:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        candidates = list(csv.DictReader(handle, delimiter="\t"))
    with DESTINATION.open(newline="", encoding="utf-8") as handle:
        fields = csv.DictReader(handle, delimiter="\t").fieldnames
    assert fields is not None

    rows = []
    for item in candidates:
        row = {field: "UNRESOLVED" for field in fields}
        for field in ("dataset_id", "dataset_family", "benchmark_suite", "domain", "modality"):
            row[field] = item[field]
        row.update(
            task_definition="PENDING_OFFICIAL_TASK_DEFINITION",
            native_binary="UNASSESSED",
            classification_or_relation="UNASSESSED",
            hard_gate_status="UNASSESSED_G1_G10",
            admission_score="UNSCORED",
            recommended_role="UNASSESSED",
            exclusion_reason="",
            evidence_source=item["official_source_locator"],
            verification_status="PENDING_OFFICIAL_VERIFICATION",
        )
        rows.append(row)

    with DESTINATION.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
