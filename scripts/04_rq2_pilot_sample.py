"""Draw a random pilot sample of workflow bodies for manual reading.

Used to derive the keyword vocabulary for config/keywords_body.yaml before
any automatic filtering happens (RQ2). Each sampled workflow's body is
written to its own readable .md file under coding/pilot_sample/, instead
of a CSV cell, so it can be opened and read like a normal document.
"""

from pathlib import Path

import pandas as pd
import yaml


def load_settings():
    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)


def safe_filename(repo_full_name, path):
    stem = Path(path).stem
    return f"{repo_full_name.replace('/', '__')}__{stem}.md"


def main():
    settings = load_settings()
    raw_dir = Path(settings["paths"]["raw_dir"])
    coding_dir = Path(settings["paths"]["coding_dir"])
    sample_size = settings["rq2"]["pilot_sample_size"]
    seed = settings["rq2"]["random_seed"]

    snapshots = pd.read_parquet(raw_dir / "data" / "source_markdown_file_snapshot.parquet")
    versions = pd.read_parquet(raw_dir / "data" / "source_markdown_file_version.parquet")
    repositories = pd.read_parquet(raw_dir / "data" / "repository.parquet")

    merged = snapshots.merge(
        versions[["source_markdown_file_snapshot_id", "source_markdown_file_history_id", "rank"]],
        on="source_markdown_file_snapshot_id",
    ).merge(
        repositories[["repository_id", "repo_full_name"]],
        on="repository_id",
    )

    latest = merged.loc[merged.groupby("source_markdown_file_history_id")["rank"].idxmax()]
    sample = latest.sample(n=sample_size, random_state=seed)

    output_dir = coding_dir / "pilot_sample"
    output_dir.mkdir(parents=True, exist_ok=True)

    index_rows = []
    for _, row in sample.iterrows():
        filename = safe_filename(row["repo_full_name"], row["path"])
        (output_dir / filename).write_text(row["body"] or "")
        index_rows.append({
            "snapshot_id": row["source_markdown_file_snapshot_id"],
            "repo_full_name": row["repo_full_name"],
            "path": row["path"],
            "filename": filename,
        })

    pd.DataFrame(index_rows).to_csv(coding_dir / "pilot_sample_index.csv", index=False)

    print(f"Sampled {len(sample)} workflows (seed={seed}).")
    print(f"Bodies written to {output_dir}/")
    print(f"Index written to {coding_dir / 'pilot_sample_index.csv'}")


if __name__ == "__main__":
    main()
