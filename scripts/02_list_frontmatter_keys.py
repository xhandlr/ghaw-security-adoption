"""List every frontmatter key across GHAW-H snapshots.

For each dotted key path (e.g. safe-outputs.threat-detection), reports how
many distinct workflows use it and a few example values. Snapshots are
never silently skipped: those whose frontmatter fails to parse, or parses
to something that is not a dict, are reported as parse failures; those
whose frontmatter parses to a valid but empty dict ({}) are reported
separately, since that is not a failure, just a workflow with no declared
keys.

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

    Lists of objects are walked with the same [] notation as
    results/03_schema_fields/fields.csv: {"steps": [{"name": "x"}]} also
    yields ("steps[].name", "x"). Lists of plain values (text, numbers)
    yield no sub-keys; they are counted only at the field's own path.
    Free-form keys keep their concrete name (mcp-servers.github).
    """
    results = []
    pending = [("", doc)]

    while pending:
        # prefix is the path to the box we are about to open,
        # current is what is inside that box
        prefix, current = pending.pop()
        # a list: open each item that is itself a dict or a list, under prefix[]
        if isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)):
                    pending.append((prefix + "[]", item))
            continue
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
    empty_dicts = []

    for _, row in rows.iterrows():
        history_id = row["source_markdown_file_history_id"]
        snapshot_id = row["source_markdown_file_snapshot_id"]
        path = row["path"]

        try:
            doc = yaml.load(row["frontmatter"], Loader=FrontmatterLoader)
        except yaml.YAMLError as e:
            parse_failures.append((snapshot_id, path, str(e)))
            continue

        if doc is None:
            parse_failures.append((snapshot_id, path, "empty frontmatter"))
            continue

        if not isinstance(doc, dict):
            parse_failures.append((snapshot_id, path, f"not a dict: {type(doc).__name__}"))
            continue

        if not doc:
            empty_dicts.append((snapshot_id, path))
            # not a failure: it parsed fine, it just declares no keys.
            # still counts as a valid workflow, just contributes no keys below.
            continue

        for key_path, value in flatten_keys(doc):
            key_workflows[key_path].add(history_id)
            if len(key_examples[key_path]) < 3:
                example = "{...}" if isinstance(value, dict) else repr(value)
                if example not in key_examples[key_path]:
                    key_examples[key_path].append(example)

    return key_workflows, key_examples, parse_failures, empty_dicts


OUTPUT_DIR = Path("results/02_frontmatter_keys")


def write_outputs(label, rows, key_workflows, key_examples, parse_failures, empty_dicts):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / f"keys_{label}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["key_path", "distinct_workflow_count", "example_values"])
        for key_path in sorted(key_workflows, key=lambda k: -len(key_workflows[k])):
            writer.writerow([
                key_path,
                len(key_workflows[key_path]),
                "; ".join(key_examples[key_path]),
            ])

    with open(OUTPUT_DIR / f"parse_failures_{label}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["snapshot_id", "path", "reason"])
        writer.writerows(parse_failures)

    with open(OUTPUT_DIR / f"empty_dicts_{label}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["snapshot_id", "path"])
        writer.writerows(empty_dicts)

    print(f"[{label}]")
    print(f"Snapshots processed: {len(rows)}")
    print(f"Parse failures (empty or invalid frontmatter): {len(parse_failures)}")
    print(f"Valid but empty frontmatter (parses to {{}}): {len(empty_dicts)}")
    print(f"Distinct key paths found: {len(key_workflows)}")
    print(f"Distinct workflows total: {rows['source_markdown_file_history_id'].nunique()}")
    print()

    return [
        label,
        len(rows),
        rows["source_markdown_file_history_id"].nunique(),
        len(parse_failures),
        len(key_workflows),
        len([k for k in key_workflows if "." not in k and "[]" not in k]),
    ]


def main():
    snapshots = pd.read_parquet("data/raw/data/source_markdown_file_snapshot.parquet")
    versions = pd.read_parquet("data/raw/data/source_markdown_file_version.parquet")
    merged = snapshots.merge(
        versions[["source_markdown_file_snapshot_id", "source_markdown_file_history_id", "rank"]],
        on="source_markdown_file_snapshot_id",
    )

    latest = merged.loc[merged.groupby("source_markdown_file_history_id")["rank"].idxmax()]

    summary = []
    for label, rows in [("all_snapshots", merged), ("latest_version", latest)]:
        key_workflows, key_examples, parse_failures, empty_dicts = count_keys(rows)
        summary.append(write_outputs(label, rows, key_workflows, key_examples, parse_failures, empty_dicts))

    with open(OUTPUT_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["scope", "snapshots_processed", "workflows_processed",
                         "parse_failures", "distinct_key_paths", "distinct_roots"])
        writer.writerows(summary)


if __name__ == "__main__":
    main()
