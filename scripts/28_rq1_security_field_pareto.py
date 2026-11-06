"""RQ1: Pareto of the security fields with the measurement granularity rules.
Read-only on the inputs.

Takes the fields coded is_security_field = "true" in SHEET and the
frontmatter of the latest snapshot of each workflow (highest rank, same
criterion as scripts 02, 14 and 19, with script 02's loader and
flatten_keys). Workflows whose frontmatter cannot be read as a dict are
excluded. Then applies section 5 of coding/rq1_security_coding_guide.md
("Granularidad de medición") to decide in which path each declaration is
counted, so that one value is not counted twice:

- Dependent block (permissions, network): the block is measured as a
  whole. A workflow counts once for the block when it declares the block in
  any form, and the block's children are not measured separately.
- Same setting (sandbox.type and sandbox.agent): when both paths are
  security fields, they are one unit, counted once per workflow that
  declares either of them, under sandbox.agent.
- Parent of any other block (a top-level security field that is not a
  dependent block): the parent is not counted as a declaration of its own
  when it only contains children that the sheet measures. In a workflow,
  the parent counts as a declaration of its own when its value is not a
  non-empty mapping (true, false, a string, a list, null or an empty
  mapping), or when none of the child paths it declares is a row of the
  sheet, whether coded true or false. Paths are compared exactly, as in
  script 19, so a wildcard row such as mcp-scripts.* never matches a
  concrete name: mcp-servers (free-form names, no rows) and mcp-scripts
  (only the mcp-scripts.* row) then count as declarations of the parent.
  The rule applies only to top-level fields, the parents of the blocks:
  every deeper field is measured as a child, whatever its value.
- Every other security field counts once per workflow that writes its path
  (the same presence as script 19).

The specific-dependency rule (safe-outputs.create-issue) changes the
default of a child, not where it is counted, so it does not change this
count.

Declarations are summed over all units. Units are sorted by number of
workflows (then by path), and the Pareto set is the smallest prefix whose
cumulative share of declarations reaches 80%. As a check, the count of
every unit measured by plain presence must equal
results/19_rq1_security_field_usage/presence.csv.

Writes to results/28_rq1_security_field_pareto/:
- units.csv: every measured unit with the rule applied, the workflows that
  declare it, its share of workflows and of declarations, the cumulative
  share and whether it is in the Pareto set;
- excluded_paths.csv: security fields that are not measured as units of
  their own, and why;
- summary.csv: workflows, security fields, units, units used,
  declarations, size of the Pareto set and its cumulative share;
- provenance.json: SHA-256 of the script, the inputs and the outputs.
"""

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import yaml

SHEET = Path("coding/rq1_security_coding_consensus.csv")
GUIDE = Path("coding/rq1_security_coding_guide.md")
PRESENCE_19 = Path("results/19_rq1_security_field_usage/presence.csv")
SNAPSHOTS = Path("data/raw/data/source_markdown_file_snapshot.parquet")
VERSIONS = Path("data/raw/data/source_markdown_file_version.parquet")
OUTPUT_DIR = Path("results/28_rq1_security_field_pareto")

DEPENDENT_BLOCKS = ("permissions", "network")
SAME_SETTING = {"sandbox.type": "sandbox.agent"}  # alias -> unit it is counted under
THRESHOLD = 0.80


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_script(number_name):
    spec = importlib.util.spec_from_file_location(number_name, f"scripts/{number_name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_sheet():
    """Security fields in sheet order, and every path in the sheet."""
    sheet = pd.read_csv(SHEET, dtype=str, keep_default_na=False)
    values = set(sheet["is_security_field"].str.strip())
    if not values <= {"true", "false"}:
        raise SystemExit(f"{SHEET}: rows not coded true/false: {sorted(values - {'true', 'false'})}")
    return list(sheet.loc[sheet["is_security_field"].str.strip() == "true", "path"]), set(sheet["path"])


def latest_frontmatters(keys02):
    """{workflow id: {path: value}} for the latest snapshot, and excluded count."""
    snapshots = pd.read_parquet(SNAPSHOTS)
    versions = pd.read_parquet(VERSIONS)
    merged = snapshots.merge(
        versions[["source_markdown_file_snapshot_id", "source_markdown_file_history_id", "rank"]],
        on="source_markdown_file_snapshot_id",
    )
    latest = merged.loc[merged.groupby("source_markdown_file_history_id")["rank"].idxmax()]
    declared, excluded = {}, 0
    for _, row in latest.iterrows():
        try:
            doc = yaml.load(row["frontmatter"], Loader=keys02.FrontmatterLoader)
        except yaml.YAMLError:
            doc = None
        if not isinstance(doc, dict):
            excluded += 1
            continue
        declared[row["source_markdown_file_history_id"]] = dict(keys02.flatten_keys(doc))
    return declared, excluded


def child_of_block(path):
    return any(path.startswith(block + ".") for block in DEPENDENT_BLOCKS)


def main():
    fields, sheet_paths = read_sheet()
    field_set = set(fields)
    declared, excluded = latest_frontmatters(load_script("02_list_frontmatter_keys"))
    total = len(declared)

    units, rules, skipped = {}, {}, []
    for path in fields:
        if child_of_block(path):
            skipped.append((path, "child of a dependent block, measured within its block"))
            continue
        if path in SAME_SETTING and SAME_SETTING[path] in field_set:
            skipped.append((path, f"same setting as {SAME_SETTING[path]}, counted under it"))
            continue
        aliases = [a for a, unit in SAME_SETTING.items() if unit == path and a in field_set]
        names = [path, *aliases]
        if path in DEPENDENT_BLOCKS:
            rule = "dependent block"
            users = {w for w, keys in declared.items() if path in keys}
        elif "." not in path:
            rule = "parent: counted unless it only contains children in the sheet"
            users = {w for w, keys in declared.items()
                     if path in keys and not (isinstance(keys[path], dict) and keys[path]
                                              and any(k.startswith(path + ".") and k in sheet_paths
                                                      for k in keys))}
        else:
            rule = "same setting" if aliases else "presence"
            users = {w for w, keys in declared.items() if any(n in keys for n in names)}
        units[path], rules[path] = users, rule

    presence = {r["path"]: int(r["workflows"]) for r in csv.DictReader(open(PRESENCE_19))}
    mismatched = [p for p in units if rules[p] in ("presence", "dependent block")
                  and len(units[p]) != presence.get(p)]
    if mismatched:
        raise SystemExit(f"Counts differ from {PRESENCE_19} for: {mismatched}")

    order = sorted(units, key=lambda p: (-len(units[p]), p))
    declarations = sum(len(units[p]) for p in order)
    rows, cumulative, pareto_size = [], 0, None
    for rank, path in enumerate(order, 1):
        n = len(units[path])
        cumulative += n
        share = cumulative / declarations
        in_pareto = pareto_size is None
        if in_pareto and share >= THRESHOLD:
            pareto_size = rank
        rows.append([rank, path, rules[path], n, n / total, n / declarations, share, in_pareto])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "units.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["rank", "path", "rule", "workflows", "share_of_workflows",
                         "share_of_declarations", "cumulative_share", "in_pareto"])
        writer.writerows(rows)
    with open(OUTPUT_DIR / "excluded_paths.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["path", "reason"])
        writer.writerows(skipped)
    with open(OUTPUT_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["measure", "value"])
        writer.writerows([
            ["workflows_analysed", total],
            ["workflows_excluded_unreadable_frontmatter", excluded],
            ["security_fields", len(fields)],
            ["measured_units", len(units)],
            ["measured_units_used", sum(bool(units[p]) for p in units)],
            ["declarations", declarations],
            ["pareto_threshold", THRESHOLD],
            ["pareto_units", pareto_size],
            ["pareto_cumulative_share", rows[pareto_size - 1][6]],
        ])

    provenance = {
        "script_sha256": sha256_of(__file__),
        "sheet": str(SHEET),
        "sheet_sha256": sha256_of(SHEET),
        "guide_sha256": sha256_of(GUIDE),
        "presence_19_sha256": sha256_of(PRESENCE_19),
        "snapshots_sha256": sha256_of(SNAPSHOTS),
        "versions_sha256": sha256_of(VERSIONS),
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Workflows: {total} (excluded {excluded}); security fields: {len(fields)}; "
          f"units: {len(units)} ({sum(bool(units[p]) for p in units)} used); "
          f"declarations: {declarations}; Pareto: {pareto_size} units, "
          f"{rows[pareto_size - 1][6]:.1%}")


if __name__ == "__main__":
    main()
