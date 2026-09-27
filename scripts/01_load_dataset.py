"""Download the GHAW-H tables and report basic columns and counts.

Does not choose a snapshot or pin a dataset revision. That decision is
recorded manually in config/settings.yaml after reviewing this script's
output.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml
from huggingface_hub import HfApi, hf_hub_download

TABLES = [
    "repository",
    "source_markdown_file_history",
    "source_markdown_file_snapshot",
    "source_markdown_file_version",
    "lock_file_snapshot",
]

def load_settings():
    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)

def main():
    settings = load_settings()
    repo_id = settings["dataset"]["repo_id"]
    revision = settings["dataset"]["revision"]
    raw_dir = Path(settings["paths"]["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    api = HfApi()
    resolved_sha = api.dataset_info(repo_id, revision=revision).sha

    tables = {}
    for name in TABLES:
        local_path = hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            filename=f"data/{name}.parquet",
            revision=resolved_sha,
            local_dir=raw_dir,
        )
        tables[name] = pd.read_parquet(local_path)

    log = {
        "download_date": datetime.now(timezone.utc).isoformat(),
        "repo_id": repo_id,
        "resolved_revision": resolved_sha,
        "tables": {name: f"data/{name}.parquet" for name in TABLES},
    }
    with open(raw_dir / "download_log.json", "w") as f:
        json.dump(log, f, indent=2)

    print(f"Resolved revision: {resolved_sha}")
    print("(not yet pinned in config/settings.yaml, that is a manual decision)\n")

    for name in TABLES:
        df = tables[name]
        print(f"{name}: {len(df)} rows")
        print(f"columns: {list(df.columns)}")
        print("--------------------------------------")

    print("\nSummary:")
    print(f"distinct repositories: {len(tables['repository'])}")
    print(f"distinct workflows (histories): {len(tables['source_markdown_file_history'])}")
    print(f"total markdown snapshots: {len(tables['source_markdown_file_snapshot'])}")
    print(f"total lock file snapshots: {len(tables['lock_file_snapshot'])}")


if __name__ == "__main__":
    main()
