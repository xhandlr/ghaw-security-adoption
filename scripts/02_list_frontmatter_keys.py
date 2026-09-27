"""List every frontmatter key across GHAW-H snapshots.

For each dotted key path (e.g. safe-outputs.threat-detection), reports how
many distinct workflows use it and a few example values. Snapshots whose
frontmatter fails to parse into a non-empty YAML dict are reported
separately, not silently skipped.

Runs the count twice: once over all snapshots, once over only the latest
version of each workflow (the unit of analysis for RQ1).
"""

import csv
from collections import defaultdict
from pathlib import Path

import pandas as pd
import yaml


class FrontmatterLoader(yaml.SafeLoader):
    """Like yaml.SafeLoader, but "on"/"off"/"yes"/"no" stay plain text.

    GH-AW frontmatter always uses "on" as the trigger field name, never as
    a literal boolean. The default YAML rules read bare on/off/yes/no as
    True/False, which silently turns the "on" key into the boolean True.
    """


for _first_letter in "OoYyNn":
    if _first_letter in FrontmatterLoader.yaml_implicit_resolvers:
        FrontmatterLoader.yaml_implicit_resolvers[_first_letter] = [
            (tag, regexp)
            for tag, regexp in FrontmatterLoader.yaml_implicit_resolvers[_first_letter]
            if tag != "tag:yaml.org,2002:bool"
        ]


def flatten_keys(doc):
    """Return a list of (dotted_path, value) pairs for a key and every sub-key.

    Example: {"safe-outputs": {"threat-detection": True}} becomes
    [("safe-outputs", {...}), ("safe-outputs.threat-detection", True)].
    """
    results = []
    pending = [("", doc)]

    while pending:
        # prefix is the path to the box we are about to open,
        # current is what is inside that box
        prefix, current = pending.pop()
        # skip if it is not a dict, nothing to flatten
        if not isinstance(current, dict):
            continue
        for key, value in current.items():
            if prefix == "":
                path = str(key)  # top level, keep the key as is
            else:
                path = prefix + "." + str(key)  # nested, prepend the current path
            results.append((path, value))
            pending.append((path, value))  # queued in case value is itself a dict

    return results


def count_keys(rows):
    key_workflows = defaultdict(set)
    key_examples = defaultdict(list)
    parse_failures = []

    for _, row in rows.iterrows():
        history_id = row["source_markdown_file_history_id"]
        try:
            doc = yaml.load(row["frontmatter"], Loader=FrontmatterLoader)
        except yaml.YAMLError as e:
            parse_failures.append((row["source_markdown_file_snapshot_id"], row["path"], str(e)))
            continue

        if not isinstance(doc, dict) or not doc:
            parse_failures.append((row["source_markdown_file_snapshot_id"], row["path"], "empty or not a dict"))
            continue

        for key_path, value in flatten_keys(doc):
            key_workflows[key_path].add(history_id)
            if len(key_examples[key_path]) < 3:
                example = "{...}" if isinstance(value, dict) else repr(value)
                if example not in key_examples[key_path]:
                    key_examples[key_path].append(example)

    return key_workflows, key_examples, parse_failures


def write_outputs(label, rows, key_workflows, key_examples, parse_failures):
    Path("results").mkdir(exist_ok=True)

    with open(f"results/frontmatter_keys_{label}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["key_path", "distinct_workflow_count", "example_values"])
        for key_path in sorted(key_workflows, key=lambda k: -len(key_workflows[k])):
            writer.writerow([
                key_path,
                len(key_workflows[key_path]),
                "; ".join(key_examples[key_path]),
            ])

    with open(f"results/frontmatter_parse_failures_{label}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["snapshot_id", "path", "reason"])
        writer.writerows(parse_failures)

    print(f"[{label}]")
    print(f"Snapshots processed: {len(rows)}")
    print(f"Parse failures (empty/invalid frontmatter): {len(parse_failures)}")
    print(f"Distinct key paths found: {len(key_workflows)}")
    print(f"Distinct workflows total: {rows['source_markdown_file_history_id'].nunique()}")
    print()


def main():
    snapshots = pd.read_parquet("data/raw/data/source_markdown_file_snapshot.parquet")
    versions = pd.read_parquet("data/raw/data/source_markdown_file_version.parquet")
    merged = snapshots.merge(
        versions[["source_markdown_file_snapshot_id", "source_markdown_file_history_id", "rank"]],
        on="source_markdown_file_snapshot_id",
    )

    latest = merged.loc[merged.groupby("source_markdown_file_history_id")["rank"].idxmax()]

    for label, rows in [("all_snapshots", merged), ("latest_version", latest)]:
        key_workflows, key_examples, parse_failures = count_keys(rows)
        write_outputs(label, rows, key_workflows, key_examples, parse_failures)


if __name__ == "__main__":
    main()
