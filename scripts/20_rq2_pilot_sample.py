"""Draw a random pilot sample of workflow bodies for manual reading.

Used to derive the keyword vocabulary for config/keywords_body.yaml before
any automatic filtering happens (RQ2). Each sampled workflow's body is
written to its own readable .md file under coding/pilot_sample/, instead
of a CSV cell, so it can be opened and read like a normal document.

Only eligible workflows are sampled (criteria in config/settings.yaml,
rq2.eligibility): a body with no instructions (nothing left after removing
HTML comments, blank lines and heading lines) or a body that is only a
${{ ... }} expression is excluded. Counts per exclusion reason are written
to results/20_rq2_pilot_sample/.
"""

import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import yaml


def load_settings():
    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)


def safe_filename(repo_full_name, path):
    stem = Path(path).stem
    return f"{repo_full_name.replace('/', '__')}__{stem}.md"


def exclusion_reason(body, eligibility):
    """Why a body is excluded from RQ2, or "" if it is eligible."""
    body = body or ""
    if eligibility.get("no_instructions"):
        without_comments = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
        lines = [line for line in without_comments.splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
        if not lines:
            return "no_instructions"
    pattern = eligibility.get("only_expression_pattern")
    if pattern and re.fullmatch(pattern, body):
        return "only_expression"
    return ""


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
    latest = latest.assign(exclusion=latest["body"].map(
        lambda b: exclusion_reason(b, settings["rq2"]["eligibility"])))
    eligible = latest[latest["exclusion"] == ""]
    sample = eligible.sample(n=sample_size, random_state=seed)

    results_dir = Path(settings["paths"]["results_dir"]) / "20_rq2_pilot_sample"
    results_dir.mkdir(parents=True, exist_ok=True)
    counts = latest["exclusion"].replace("", "eligible").value_counts()
    counts.rename_axis("status").reset_index(name="workflows").to_csv(
        results_dir / "eligibility.csv", index=False)
    latest[latest["exclusion"] != ""][
        ["source_markdown_file_snapshot_id", "repo_full_name", "path", "exclusion"]
    ].to_csv(results_dir / "excluded_workflows.csv", index=False)

    output_dir = coding_dir / "pilot_sample"
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_file in output_dir.glob("*.md"):
        old_file.unlink()  # bodies from a previous sample must not remain

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

    index_path = coding_dir / "pilot_sample_index.csv"
    pd.DataFrame(index_rows).to_csv(index_path, index=False)

    def sha256_of(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    tables = ["source_markdown_file_snapshot", "source_markdown_file_version", "repository"]
    provenance = {
        "dataset_repo_id": settings["dataset"]["repo_id"],
        "dataset_revision": settings["dataset"]["revision"],
        "input_sha256": {t: sha256_of(raw_dir / "data" / f"{t}.parquet") for t in tables},
        "eligibility": settings["rq2"]["eligibility"],
        "sample_size": sample_size,
        "random_seed": seed,
        "workflows": len(latest),
        "eligible": len(eligible),
        "outputs_sha256": {
            **{p.name: sha256_of(p) for p in sorted(results_dir.glob("*.csv"))},
            "pilot_sample_index.csv": sha256_of(index_path),
        },
    }
    (results_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Eligible: {len(eligible)} of {len(latest)}; excluded: {dict(counts.drop('eligible'))}")
    print(f"Sampled {len(sample)} workflows (seed={seed}).")
    print(f"Bodies written to {output_dir}/")
    print(f"Index written to {coding_dir / 'pilot_sample_index.csv'}")


if __name__ == "__main__":
    main()
