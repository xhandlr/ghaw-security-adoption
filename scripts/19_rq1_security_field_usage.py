"""RQ1: how often workflows declare the security fields. Read-only on the inputs.

Takes the fields coded is_security_field = "true" in SHEET and looks for
them in the frontmatter of the latest snapshot of each workflow (highest
rank, same criterion as scripts 02 and 14). A field counts as present in a
workflow only when its path is written explicitly in the frontmatter, with
the same dotted and [] notation as script 02 (its loader and flatten_keys
are reused). A parent being present does not make its children present.

Workflows whose frontmatter cannot be read as a dict are excluded and
counted in summary.csv. Workflows with an empty frontmatter ({}) stay in
the denominator, declaring no fields. As a check, the per-field counts
must equal results/02_frontmatter_keys/keys_latest_version.csv.

Eligibility: a field could only be declared after it was added to the
GH-AW schema. For each security field, the script finds the first commit
of the schema file (up to the commit pinned in config/settings.yaml) whose
fields, extracted with script 03's flatten_schema, include the path. A
workflow is eligible for a field when its latest version was committed at
or after that commit's date. Usage is reported over all workflows and over
the eligible ones. Limits:
- the first commit is found by binary search over the schema history, so
  only some versions are read; it assumes a field is never removed and
  added again;
- a field that was renamed counts as missing in versions with the old name;
- dates are commit dates of the schema and of the workflow file, not the
  dates a GH-AW release shipped the field or a workflow was compiled.

The schema history is read from a blobless clone of github/gh-aw in
data/raw/gh-aw, made by this script if it is missing.

SHEET is the first coder's sheet until the consensus sheet exists
(scripts/18_rq1_consensus_sheet.py); then it should point to
coding/rq1_security_coding_consensus.csv.

Writes to results/19_rq1_security_field_usage/:
- presence.csv: every security field with its root, the date it entered
  the schema, the number and share of all workflows that declare it, the
  eligible workflows and the share of them that declare it, and whether
  any workflow does;
- top_used.csv: the security fields declared by at least one workflow,
  sorted by number of workflows;
- by_root.csv: per root, the security fields it has, how many of them are
  used, and how many workflows declare at least one of them;
- summary.csv: workflows analysed, security fields used and never used,
  never used fields split by whether any workflow was eligible, and
  workflows that declare at least one security field;
- provenance.json: SHA-256 of the inputs and outputs, and the schema
  commits read.
"""

import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pandas as pd
import yaml

SHEET = Path("coding/rq1_security_coding_coder1.csv")
KEYS_02 = Path("results/02_frontmatter_keys/keys_latest_version.csv")
SNAPSHOTS = Path("data/raw/data/source_markdown_file_snapshot.parquet")
VERSIONS = Path("data/raw/data/source_markdown_file_version.parquet")
SETTINGS = Path("config/settings.yaml")
CLONE = Path("data/raw/gh-aw")
OUTPUT_DIR = Path("results/19_rq1_security_field_usage")


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_script(number_name):
    spec = importlib.util.spec_from_file_location(number_name, f"scripts/{number_name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def security_fields():
    """(path, root) of every field coded true, in sheet order."""
    sheet = pd.read_csv(SHEET, dtype=str, keep_default_na=False)
    values = set(sheet["is_security_field"].str.strip())
    if not values <= {"true", "false"}:
        raise SystemExit(f"{SHEET}: rows not coded true/false: {sorted(values - {'true', 'false'})}")
    chosen = sheet[sheet["is_security_field"].str.strip() == "true"]
    return list(zip(chosen["path"], chosen["root"]))


def workflow_keys(keys02):
    """{workflow id: set of key paths}, {workflow id: commit date} for the latest snapshot, and excluded count."""
    snapshots = pd.read_parquet(SNAPSHOTS)
    versions = pd.read_parquet(VERSIONS)
    merged = snapshots.merge(
        versions[["source_markdown_file_snapshot_id", "source_markdown_file_history_id", "rank", "committed_at"]],
        on="source_markdown_file_snapshot_id",
    )
    latest = merged.loc[merged.groupby("source_markdown_file_history_id")["rank"].idxmax()]

    keys, dates, excluded = {}, {}, 0
    for _, row in latest.iterrows():
        try:
            doc = yaml.load(row["frontmatter"], Loader=keys02.FrontmatterLoader)
        except yaml.YAMLError:
            doc = None
        if not isinstance(doc, dict):
            excluded += 1
            continue
        workflow = row["source_markdown_file_history_id"]
        keys[workflow] = {path for path, _ in keys02.flatten_keys(doc)}
        dates[workflow] = pd.Timestamp(row["committed_at"])
    return keys, dates, excluded


def git(*args):
    return subprocess.run(["git", "-C", str(CLONE), *args], check=True,
                          capture_output=True, text=True).stdout


class SchemaHistory:
    """Field paths of each version of the schema file, read on demand."""

    def __init__(self, repo, path, commit, schema03):
        if not CLONE.exists():
            subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                            f"https://github.com/{repo}.git", str(CLONE)], check=True)
        self.path, self.schema03, self.cache = path, schema03, {}
        self.commits = git("rev-list", "--reverse", commit, "--", path).split()
        if not self.commits or self.commits[-1] != commit:
            raise SystemExit(f"Pinned commit {commit} does not touch {path}")

    def fields(self, commit):
        if commit not in self.cache:
            doc = json.loads(git("show", f"{commit}:{self.path}"))
            definitions = doc.get("definitions", doc.get("$defs", {}))
            self.cache[commit] = {f[0] for f in self.schema03.flatten_schema(doc, definitions)[0]}
        return self.cache[commit]

    def first_commit_with(self, field):
        """Oldest commit whose schema has field, assuming it stays once added."""
        if field not in self.fields(self.commits[-1]):
            raise SystemExit(f"{field} is not in the pinned schema")
        low, high = 0, len(self.commits) - 1
        while low < high:
            middle = (low + high) // 2
            if field in self.fields(self.commits[middle]):
                high = middle
            else:
                low = middle + 1
        return self.commits[low]

    def date(self, commit):
        return pd.Timestamp(git("log", "-1", "--format=%cI", commit).strip())


def main():
    settings = yaml.safe_load(open(SETTINGS))["gh_aw_schema"]
    fields = security_fields()
    keys, dates, excluded = workflow_keys(load_script("02_list_frontmatter_keys"))
    total = len(keys)

    users = {path: {w for w, declared in keys.items() if path in declared} for path, _ in fields}

    expected = {r["key_path"]: int(r["distinct_workflow_count"]) for r in csv.DictReader(open(KEYS_02))}
    mismatched = [p for p, ws in users.items() if len(ws) != expected.get(p, 0)]
    if mismatched:
        raise SystemExit(f"Counts differ from {KEYS_02} for: {mismatched}")

    history = SchemaHistory(settings["repo"], settings["path"], settings["commit"],
                            load_script("03_extract_schema_fields"))
    since, eligible = {}, {}
    for path, _ in fields:
        commit = history.first_commit_with(path)
        since[path] = (commit, history.date(commit))
        eligible[path] = {w for w, d in dates.items() if d >= since[path][1]}
        if not users[path] <= eligible[path]:
            raise SystemExit(f"{path} is declared by workflows written before it entered the schema")

    def share(n, d):
        return n / d if d else ""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "presence.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "root", "in_schema_since", "schema_commit", "workflows",
                         "share_of_workflows", "eligible_workflows", "share_of_eligible", "present"])
        for path, root in fields:
            n, e = len(users[path]), len(eligible[path])
            writer.writerow([path, root, since[path][1].isoformat(), since[path][0],
                             n, n / total, e, share(n, e), bool(n)])

    used = sorted((p for p, _ in fields if users[p]), key=lambda p: (-len(users[p]), p))
    root_of = dict(fields)
    with open(OUTPUT_DIR / "top_used.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "path", "root", "workflows", "share_of_workflows",
                         "eligible_workflows", "share_of_eligible"])
        for rank, path in enumerate(used, 1):
            n, e = len(users[path]), len(eligible[path])
            writer.writerow([rank, path, root_of[path], n, n / total, e, share(n, e)])

    roots = list(dict.fromkeys(root for _, root in fields))
    with open(OUTPUT_DIR / "by_root.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["root", "security_fields", "fields_used", "fields_never_used",
                         "workflows_declaring_any", "share_of_workflows"])
        rows = []
        for root in roots:
            paths = [p for p, r in fields if r == root]
            declaring = set().union(*(users[p] for p in paths))
            n_used = sum(bool(users[p]) for p in paths)
            rows.append([root, len(paths), n_used, len(paths) - n_used, len(declaring), len(declaring) / total])
        writer.writerows(sorted(rows, key=lambda r: (-r[4], r[0])))

    never = [p for p, _ in fields if not users[p]]
    any_security = set().union(*users.values())
    with open(OUTPUT_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["measure", "value"])
        writer.writerows([
            ["workflows_analysed", total],
            ["workflows_excluded_unreadable_frontmatter", excluded],
            ["security_fields", len(fields)],
            ["security_fields_used", len(used)],
            ["security_fields_never_used", len(never)],
            ["never_used_with_eligible_workflows", sum(bool(eligible[p]) for p in never)],
            ["never_used_without_eligible_workflows", sum(not eligible[p] for p in never)],
            ["workflows_declaring_any_security_field", len(any_security)],
            ["share_of_workflows_declaring_any", len(any_security) / total],
        ])

    provenance = {
        "sheet": str(SHEET),
        "sheet_sha256": sha256_of(SHEET),
        "keys_02": str(KEYS_02),
        "keys_02_sha256": sha256_of(KEYS_02),
        "snapshots_sha256": sha256_of(SNAPSHOTS),
        "versions_sha256": sha256_of(VERSIONS),
        "schema_repo": settings["repo"],
        "schema_path": settings["path"],
        "schema_pinned_commit": settings["commit"],
        "schema_commits_in_history": len(history.commits),
        "schema_commits_read": sorted(history.cache),
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Workflows: {total} (excluded {excluded}); security fields used "
          f"{len(used)}/{len(fields)}; workflows declaring any: {len(any_security)}; "
          f"schema versions read: {len(history.cache)}/{len(history.commits)}")


if __name__ == "__main__":
    main()
