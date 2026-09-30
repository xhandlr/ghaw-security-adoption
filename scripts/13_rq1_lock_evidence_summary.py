"""Cross each workflow's frontmatter with its lock evidence (script 12).

Builds base.csv (one row per workflow: the four demo fields as written in
the frontmatter, plus the lock columns from 12) and, from it, the evidence
for the pending points of coding/rq1_codebook.yaml. It does not classify
workflows as implicit / equal / modified; that is the measurement script.

Groups are (compiler_version, agent_id); locks without metadata form their
own group, labelled no_metadata. The reference firewall set of a group is
the most frequent firewall_domains among the workflows of that group that
do NOT declare network. On a tie the group is marked "tie" and no set is
chosen; with no such workflows it is marked "no_reference".
"""

import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import yaml

EVIDENCE_DIR = Path("results/12_rq1_lock_evidence")
OUTPUT_DIR = Path("results/13_rq1_lock_evidence_summary")
SNAPSHOT_TABLE = Path("data/raw/data/source_markdown_file_snapshot.parquet")
NO_METADATA = "no_metadata"
FIELDS = {"strict": ("strict",), "tools.bash": ("tools", "bash"),
          "network": ("network",), "permissions": ("permissions",)}


def load_frontmatter_loader():
    """Reuse the loader from script 02, so YAML is read the same way."""
    spec = importlib.util.spec_from_file_location("keys02", "scripts/02_list_frontmatter_keys.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FrontmatterLoader


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_evidence():
    evidence_path = EVIDENCE_DIR / "lock_evidence.csv"
    expected = json.loads((EVIDENCE_DIR / "provenance.json").read_text())["lock_evidence_csv_sha256"]
    actual = sha256_of(evidence_path)
    if actual != expected:
        raise SystemExit(f"lock_evidence.csv SHA-256 {actual} does not match 12 provenance {expected}")
    return pd.read_csv(evidence_path, keep_default_na=False, dtype=str), actual


def field_value(doc, keys):
    """(declared, value) for a dotted field in a parsed frontmatter."""
    current = doc
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current


def build_base(evidence, loader):
    frontmatter = pd.read_parquet(SNAPSHOT_TABLE).set_index("source_markdown_file_snapshot_id")["frontmatter"]
    rows = []
    for _, ev in evidence.iterrows():
        row = ev.to_dict()
        row["group_compiler_version"] = ev["compiler_version"] or NO_METADATA
        row["group_agent_id"] = ev["agent_id"] or NO_METADATA
        try:
            doc = yaml.load(frontmatter[int(ev["snapshot_id"])], Loader=loader)
        except yaml.YAMLError:
            doc = None
        row["frontmatter_status"] = "ok" if isinstance(doc, dict) else "parse_failure"
        for name, keys in FIELDS.items():
            declared, value = field_value(doc, keys) if isinstance(doc, dict) else (False, None)
            row[f"{name}_declared"] = declared
            row[f"{name}_value"] = json.dumps(value, sort_keys=True) if declared else ""
        rows.append(row)
    return pd.DataFrame(rows)


def network_form(row):
    """undeclared / defaults / allowed_defaults / other, from the written value."""
    if not row["network_declared"]:
        return "undeclared"
    value = json.loads(row["network_value"])
    if value == "defaults":
        return "defaults"
    if (isinstance(value, dict) and set(value) == {"allowed"}
            and isinstance(value["allowed"], list) and set(value["allowed"]) == {"defaults"}):
        return "allowed_defaults"
    return "other"


def group_references(base):
    """(compiler_version, agent_id) -> (status, reference set or None, n)."""
    references = {}
    usable = base[(base["frontmatter_status"] == "ok") & (base["firewall_status"] == "ok")]
    for group, rows in usable.groupby(["group_compiler_version", "group_agent_id"]):
        undeclared = rows[~rows["network_declared"]]["firewall_domains"]
        if undeclared.empty:
            references[group] = ("no_reference", None, 0)
            continue
        counts = Counter(undeclared).most_common()
        if len(counts) > 1 and counts[0][1] == counts[1][1]:
            references[group] = ("tie", None, counts[0][1])
        else:
            references[group] = ("ok", counts[0][0], counts[0][1])
    return references


def set_difference(domains_json, reference_json):
    domains, reference = set(json.loads(domains_json)), set(json.loads(reference_json))
    return json.dumps(sorted(domains - reference)), json.dumps(sorted(reference - domains))


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    evidence, evidence_sha = load_evidence()
    base = build_base(evidence, load_frontmatter_loader())
    base["network_form"] = base.apply(network_form, axis=1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base.to_csv(OUTPUT_DIR / "base.csv", index=False)

    valid = base[base["frontmatter_status"] == "ok"]
    summary = [["frontmatter_parse_failure", "", int((base["frontmatter_status"] != "ok").sum())]]
    group = ["group_compiler_version", "group_agent_id"]

    # 1. permissions not declared -> agent permissions in the lock
    rows = valid[~valid["permissions_declared"]]
    write_csv(OUTPUT_DIR / "permissions_undeclared.csv",
              ["repo_full_name", "path", "group_compiler_version", "group_agent_id",
               "agent_permissions", "agent_permissions_status"],
              rows[["repo_full_name", "path", *group, "agent_permissions",
                    "agent_permissions_status"]].values.tolist())
    summary.append(["permissions_undeclared", "rows", len(rows)])

    # 2. network forms equal to the default, against each group's reference
    references = group_references(base)
    forms = valid[valid["network_form"].isin(["undeclared", "defaults", "allowed_defaults"])]
    summary.append(["network_default_forms", "excluded_firewall_status_not_ok",
                    int((forms["firewall_status"] != "ok").sum())])
    forms = forms[forms["firewall_status"] == "ok"]

    by_form, by_group, outliers = [], [], []
    for key, rows in forms.groupby(group):
        status, reference, reference_n = references.get(key, ("no_reference", None, 0))
        forms_present = sorted(rows["network_form"].unique())
        matches_by_form = {}
        for form, form_rows in rows.groupby("network_form"):
            counts = Counter(form_rows["firewall_domains"])
            matching = int((form_rows["firewall_domains"] == reference).sum()) if reference else ""
            matches_by_form[form] = (matching, len(form_rows))
            by_form.append([*key, form, len(form_rows), len(counts), status,
                            reference or "", reference_n, matching])
            if reference:
                for _, r in form_rows[form_rows["firewall_domains"] != reference].iterrows():
                    extra, missing = set_difference(r["firewall_domains"], reference)
                    outliers.append([*key, form, r["repo_full_name"], r["path"],
                                     r["firewall_domains_n"], extra, missing])
        all_match = (all(m == n for m, n in matches_by_form.values()) if reference else "")
        by_group.append([*key, "+".join(forms_present), status,
                         json.dumps({f: f"{m}/{n}" for f, (m, n) in matches_by_form.items()}),
                         all_match])
    write_csv(OUTPUT_DIR / "network_default_forms.csv",
              [*group, "network_form", "rows", "distinct_firewall_sets", "reference_status",
               "reference_set", "reference_n", "rows_matching_reference"], by_form)
    write_csv(OUTPUT_DIR / "network_default_forms_by_group.csv",
              [*group, "forms_present", "reference_status", "matching_by_form", "all_rows_match"],
              by_group)
    write_csv(OUTPUT_DIR / "network_default_forms_outliers.csv",
              [*group, "network_form", "repo_full_name", "path", "firewall_domains_n",
               "extra_vs_reference", "missing_vs_reference"], outliers)
    summary.append(["network_default_forms", "rows", len(forms)])
    summary.append(["network_default_forms", "outlier_rows", len(outliers)])

    # 3. tools.bash written as true -> bash_mode
    rows = valid[valid["tools.bash_value"] == "true"]
    mode = rows["bash_mode"].where(rows["bash_mode"] != "", rows["bash_status"])
    table = pd.crosstab(rows["group_agent_id"], mode)
    table.to_csv(OUTPUT_DIR / "bash_true.csv")
    summary.append(["bash_true", "rows", len(rows)])

    # 4. network written exactly as {firewall: true}
    rows = valid[valid["network_value"] == json.dumps({"firewall": True})]
    firewall_only = []
    for _, r in rows.iterrows():
        status, reference, reference_n = references.get(
            (r["group_compiler_version"], r["group_agent_id"]), ("no_reference", None, 0))
        extra, missing = set_difference(r["firewall_domains"], reference) if reference and r["firewall_domains"] else ("", "")
        firewall_only.append([r["repo_full_name"], r["path"], r["group_compiler_version"],
                              r["group_agent_id"], r["firewall_status"], r["firewall_domains"],
                              r["firewall_domains_n"], status, reference or "", reference_n,
                              len(json.loads(reference)) if reference else "", extra, missing])
    write_csv(OUTPUT_DIR / "network_firewall_only.csv",
              ["repo_full_name", "path", *group, "firewall_status", "firewall_domains",
               "firewall_domains_n", "reference_status", "reference_set", "reference_n",
               "reference_domains_n", "extra_vs_reference", "missing_vs_reference"], firewall_only)
    summary.append(["network_firewall_only", "rows", len(rows)])

    # 5. tools.bash not declared -> bash_mode by agent and compiler version
    rows = valid[~valid["tools.bash_declared"]]
    mode = rows["bash_mode"].where(rows["bash_mode"] != "", rows["bash_status"])
    counts = rows.assign(bash_mode_or_status=mode).groupby(
        ["group_agent_id", "group_compiler_version", "bash_mode_or_status"]).size()
    counts.reset_index(name="rows").to_csv(OUTPUT_DIR / "bash_undeclared.csv", index=False)
    summary.append(["bash_undeclared", "rows", len(rows)])

    write_csv(OUTPUT_DIR / "summary.csv", ["output", "measure", "value"], summary)

    with open("config/settings.yaml") as f:
        dataset = yaml.safe_load(f)["dataset"]
    provenance = {
        "dataset_repo_id": dataset["repo_id"],
        "dataset_revision": dataset["revision"],
        "lock_evidence_csv":str(EVIDENCE_DIR / "lock_evidence.csv"),
        "lock_evidence_csv_sha256": evidence_sha,
        "snapshot_table_sha256": sha256_of(SNAPSHOT_TABLE),
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    for output, measure, value in summary:
        print(f"{output} {measure}: {value}")


if __name__ == "__main__":
    main()
