"""Describe the GHAW-H dataset: size, period and versions per workflow.

Reads the downloaded tables (data/raw/data/) and writes to
results/04_dataset_overview/:
- summary.csv: one row per measure (repositories, workflows, snapshots,
  first and last commit date over all versions and over the latest
  version of each workflow, and versions per workflow: mean, median,
  maximum, workflows with a single version);
- versions_per_workflow.csv: how many workflows have each number of
  versions;
- provenance.json: dataset revision and SHA-256 of inputs and outputs.

The latest version of a workflow is its highest rank, the same criterion
as config/settings.yaml (snapshot_selection).
"""

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

DATA_DIR = Path("data/raw/data")
OUTPUT_DIR = Path("results/04_dataset_overview")
TABLES = ["repository", "source_markdown_file_history", "source_markdown_file_version"]


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    with open("config/settings.yaml") as f:
        settings = yaml.safe_load(f)

    repositories = pd.read_parquet(DATA_DIR / "repository.parquet")
    histories = pd.read_parquet(DATA_DIR / "source_markdown_file_history.parquet")
    versions = pd.read_parquet(DATA_DIR / "source_markdown_file_version.parquet")

    committed = pd.to_datetime(versions["committed_at"], utc=True)
    latest = versions.loc[versions.groupby("source_markdown_file_history_id")["rank"].idxmax()]
    latest_committed = pd.to_datetime(latest["committed_at"], utc=True)
    per_workflow = versions.groupby("source_markdown_file_history_id").size()

    summary = [
        ["repositories", len(repositories)],
        ["workflows", len(histories)],
        ["snapshots", len(versions)],
        ["first_commit_all_versions", committed.min().date().isoformat()],
        ["last_commit_all_versions", committed.max().date().isoformat()],
        ["first_commit_latest_versions", latest_committed.min().date().isoformat()],
        ["last_commit_latest_versions", latest_committed.max().date().isoformat()],
        ["median_commit_latest_versions", latest_committed.median().date().isoformat()],
        ["versions_per_workflow_mean", round(per_workflow.mean(), 2)],
        ["versions_per_workflow_median", per_workflow.median()],
        ["versions_per_workflow_max", int(per_workflow.max())],
        ["workflows_with_one_version", int((per_workflow == 1).sum())],
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["measure", "value"])
        writer.writerows(summary)

    distribution = per_workflow.value_counts().sort_index()
    with open(OUTPUT_DIR / "versions_per_workflow.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["versions", "workflows"])
        writer.writerows([int(v), int(n)] for v, n in distribution.items())

    provenance = {
        "dataset_repo_id": settings["dataset"]["repo_id"],
        "dataset_revision": settings["dataset"]["revision"],
        "snapshot_selection": settings["snapshot_selection"]["criterion"],
        "input_sha256": {t: sha256_of(DATA_DIR / f"{t}.parquet") for t in TABLES},
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    for measure, value in summary:
        print(f"{measure}: {value}")


if __name__ == "__main__":
    main()
