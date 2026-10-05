"""Workflow families for RQ2. Read-only on the sample and the coding sheet.

Works on the RQ2-eligible workflows (recomputed with script 20's exclusion
criterion and checked against results/20_rq2_pilot_sample/eligibility.csv)
and, separately, on the 240 workflows of the pilot sample. Outputs with
counts have a population column: eligible or sample.

Families are looked at through:
- the workflow file name (without path, with extension, as written);
- the template the workflow was installed from: the frontmatter source
  field without the reference after @ (source_template; "none" if absent);
- the owner (the part of the repository name before "/");
- body copies: workflows whose normalized body (trailing spaces removed
  from each line, blank lines removed at the start and at the end) is
  identical. Copy groups are defined on the eligible workflows, so a
  sampled workflow belongs to a copy group if any eligible workflow has
  the same body, sampled or not.

Also writes the families of the rows already coded in
coding/rq2_coding_consensus.csv (tiene_defensa true or false) and a per-owner
summary of those rows. Category values written by the coder are kept as
they are.
"""

import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

DATA_DIR = Path("data/raw/data")
OUTPUT_DIR = Path("results/23_rq2_workflow_families")
ELIGIBILITY = Path("results/20_rq2_pilot_sample/eligibility.csv")
SAMPLE_INDEX = Path("coding/pilot_sample_index.csv")
CODING_SHEET = Path("coding/rq2_coding_consensus.csv")
TABLES = ["source_markdown_file_snapshot", "source_markdown_file_version", "repository"]
NO_TEMPLATE = "none"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_body(body):
    lines = [line.rstrip() for line in body.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def source_template(frontmatter, loader):
    try:
        doc = yaml.load(frontmatter, Loader=loader)
    except yaml.YAMLError:
        return NO_TEMPLATE
    if not isinstance(doc, dict) or doc.get("source") in (None, ""):
        return NO_TEMPLATE
    return str(doc["source"]).split("@", 1)[0]


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def counts_by(frame, column, populations):
    rows = []
    for population, members in populations.items():
        counts = Counter(frame.loc[members, column])
        rows += [[population, value, n]
                 for value, n in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]
    return rows


def main():
    with open("config/settings.yaml") as f:
        settings = yaml.safe_load(f)
    pilot = load_module("pilot20", "scripts/20_rq2_pilot_sample.py")
    loader = load_module("keys02", "scripts/02_list_frontmatter_keys.py").FrontmatterLoader

    snapshots = pd.read_parquet(DATA_DIR / "source_markdown_file_snapshot.parquet")
    versions = pd.read_parquet(DATA_DIR / "source_markdown_file_version.parquet")
    repositories = pd.read_parquet(DATA_DIR / "repository.parquet")
    merged = snapshots.merge(
        versions[["source_markdown_file_snapshot_id", "source_markdown_file_history_id", "rank"]],
        on="source_markdown_file_snapshot_id",
    ).merge(repositories[["repository_id", "repo_full_name"]], on="repository_id")
    latest = merged.loc[merged.groupby("source_markdown_file_history_id")["rank"].idxmax()]

    eligibility = settings["rq2"]["eligibility"]
    eligible = latest[latest["body"].map(lambda b: pilot.exclusion_reason(b, eligibility) == "")]
    expected = pd.read_csv(ELIGIBILITY).set_index("status")["workflows"]["eligible"]
    if len(eligible) != expected:
        raise SystemExit(f"Eligible workflows: {len(eligible)}, script 20 reports {expected}")

    eligible = eligible.set_index("source_markdown_file_snapshot_id").sort_index()
    index = pd.read_csv(SAMPLE_INDEX)
    outside = sorted(set(index["snapshot_id"]) - set(eligible.index))
    if outside:
        raise SystemExit(f"Sample snapshots not among eligible workflows: {outside}")
    populations = {"eligible": list(eligible.index), "sample": list(index["snapshot_id"])}
    in_sample = set(populations["sample"])

    frame = pd.DataFrame(index=eligible.index)
    frame["repository"] = eligible["repo_full_name"]
    frame["owner"] = eligible["repo_full_name"].map(lambda r: r.split("/", 1)[0])
    frame["filename"] = eligible["path"].map(lambda p: Path(p).name)
    frame["source_template"] = eligible["frontmatter"].map(lambda t: source_template(t, loader))
    frame["body_hash"] = eligible["body"].map(lambda b: sha256_text(normalize_body(b or "")))

    # Copy groups: bodies shared by 2+ eligible workflows. Ids C001, C002, ...
    # by group size (largest first), then by hash so the order is stable.
    sizes = Counter(frame["body_hash"])
    copied = sorted((h for h, n in sizes.items() if n >= 2), key=lambda h: (-sizes[h], h))
    group_ids = {h: f"C{i:03d}" for i, h in enumerate(copied, 1)}
    frame["copy_group"] = frame["body_hash"].map(lambda h: group_ids.get(h, ""))
    frame["copy_group_size"] = frame["body_hash"].map(sizes)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for population, members in populations.items():
        subset = frame.loc[members]
        summary_rows.append([
            population,
            len(subset),
            int((subset["copy_group"] == "").sum()),
            int((subset["copy_group"] != "").sum()),
            subset["owner"].nunique(),
            subset["repository"].nunique(),
            int((subset["source_template"] == NO_TEMPLATE).sum()),
        ])
    write_csv(OUTPUT_DIR / "summary.csv",
              ["population", "workflows", "unique_body", "in_copy_groups", "owners",
               "repositories", "no_source_template"], summary_rows)

    write_csv(OUTPUT_DIR / "by_filename.csv", ["population", "filename", "workflows"],
              counts_by(frame, "filename", populations))
    write_csv(OUTPUT_DIR / "by_source_template.csv", ["population", "source_template", "workflows"],
              counts_by(frame, "source_template", populations))

    owner_rows = []
    for population, members in populations.items():
        subset = frame.loc[members]
        workflows = subset.groupby("owner").size()
        repos = subset.groupby("owner")["repository"].nunique()
        for owner in sorted(workflows.index, key=lambda o: (-workflows[o], o)):
            owner_rows.append([population, owner, int(workflows[owner]), int(repos[owner])])
    write_csv(OUTPUT_DIR / "by_owner.csv", ["population", "owner", "workflows", "repositories"],
              owner_rows)

    copies = frame[frame["copy_group"] != ""].sort_values(["copy_group", "repository", "filename"])
    write_csv(OUTPUT_DIR / "body_copies.csv",
              ["copy_group", "owner", "repository", "filename", "source_template", "in_sample"],
              [[r["copy_group"], r["owner"], r["repository"], r["filename"], r["source_template"],
                snapshot_id in in_sample] for snapshot_id, r in copies.iterrows()])

    # Families of the rows already coded (same criterion as script 22).
    sheet = pd.read_csv(CODING_SHEET, dtype=str, keep_default_na=False)
    coded = sheet[sheet["tiene_defensa"].str.strip().isin(["true", "false"])]
    by_file = index.set_index("filename")["snapshot_id"]
    coded_rows = []
    for _, r in coded.iterrows():
        f = frame.loc[by_file[r["archivo"]]]
        coded_rows.append([
            r["orden"], r["archivo"], f["owner"], f["repository"], f["filename"],
            f["source_template"], f["copy_group"], f["copy_group_size"],
            r["tiene_defensa"].strip(), r.get("categoria", ""),
        ])
    write_csv(OUTPUT_DIR / "coded_rows.csv",
              ["order", "file", "owner", "repository", "filename", "source_template",
               "copy_group", "copy_group_size", "has_defense", "category"], coded_rows)

    coded_by_owner = Counter(row[2] for row in coded_rows)
    with_defense = Counter(row[2] for row in coded_rows if row[8] == "true")
    write_csv(OUTPUT_DIR / "coded_by_owner.csv", ["owner", "coded_rows", "with_defense"],
              [[o, coded_by_owner[o], with_defense[o]]
               for o in sorted(coded_by_owner, key=lambda o: (-coded_by_owner[o], o))])

    provenance = {
        "dataset_repo_id": settings["dataset"]["repo_id"],
        "dataset_revision": settings["dataset"]["revision"],
        "input_sha256": {
            **{t: sha256_of(DATA_DIR / f"{t}.parquet") for t in TABLES},
            "pilot_sample_index.csv": sha256_of(SAMPLE_INDEX),
            "rq2_coding_consensus.csv": sha256_of(CODING_SHEET),
        },
        "eligibility": eligibility,
        "body_normalization": "trailing spaces removed per line; leading and trailing blank lines removed",
        "eligible_workflows": len(frame),
        "sample_workflows": len(populations["sample"]),
        "coded_rows": len(coded_rows),
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Copy groups: {len(copied)}; coded rows: {len(coded_rows)}")


if __name__ == "__main__":
    main()
