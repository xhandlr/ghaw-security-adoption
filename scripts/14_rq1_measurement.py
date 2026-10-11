"""RQ1 measurement: classify the demo fields of each workflow.

Applies coding/rq1_codebook.yaml to the latest snapshot of each workflow
(highest rank, same criterion as scripts 02 and 12). All values, decisions
and reasons come from the codebook; this script only knows how to compare
a value against each rule type listed in the codebook's rule_types.

Per workflow and field:
- not declared -> implicit
- declared -> rules are tried in the codebook's order (equal_to_default,
  then forms, then rest). The first match decides. Other rules that also
  match are listed in other_rules; if they lead to a different decision,
  the state is conflict. A value no rule matches is no_rule.

For modified values, the field's direction section is applied as a second
layer: the first category that matches gives direction and broadens; if none
matches, the direction rest rule does.

Workflows whose frontmatter cannot be read as a dict are excluded and
listed in excluded.csv.
"""

import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

CODEBOOK = Path("coding/rq1_codebook.yaml")
DATA_DIR = Path("data/raw/data")
OUTPUT_DIR = Path("results/14_rq1_measurement")
TABLES = ["source_markdown_file_snapshot", "source_markdown_file_version", "repository"]
EQUAL_STATE = "explicit_equal_default"
ADDED_COMMANDS_RULE = "bash_dir_adds_and_removes"  # direction rule whose added commands are listed


def canonical(value):
    return json.dumps(value, sort_keys=True)


def as_set(items):
    return {canonical(item) for item in items}


def matches(rule, value):
    kind = rule["type"]
    if kind == "exact_value":
        return canonical(value) == canonical(rule["value"])
    if kind == "list_same_set":
        return isinstance(value, list) and as_set(value) == as_set(rule["value"])
    if kind == "list_other_set":
        return isinstance(value, list) and as_set(value) != as_set(rule["value"])
    if kind == "dict_key_set":
        return (isinstance(value, dict) and set(value) == {rule["key"]}
                and isinstance(value[rule["key"]], list)
                and as_set(value[rule["key"]]) == as_set(rule["value"]))
    if kind == "list_contains_any":
        return isinstance(value, list) and bool(as_set(value) & as_set(rule["value"]))
    if kind == "list_vs_set":
        if not isinstance(value, list):
            return False
        items, reference = as_set(value), as_set(rule["value"])
        if items & as_set(rule.get("excludes", [])):
            return False
        relation = rule["relation"]
        if relation == "subset":
            return items < reference
        if relation == "superset":
            return items > reference
        if relation == "adds_and_removes":
            return bool(items - reference) and bool(reference - items)
        raise ValueError(f"unknown relation: {relation}")
    if kind == "dict_conditions":
        return isinstance(value, dict) and all(condition_holds(c, value) for c in rule["conditions"])
    if kind == "rest":
        return True
    raise ValueError(f"unknown rule type: {kind}")


def condition_holds(condition, value):
    """One condition of a dict_conditions rule, as listed in rule_types."""
    (name, args), = condition.items()
    if name in ("any_key_with_value", "no_key_with_value"):
        found = any(k not in args["except"] and canonical(v) == canonical(args["value"])
                    for k, v in value.items())
        return found if name == "any_key_with_value" else not found
    if name in ("key_with_value", "key_not_equal"):
        equal = args["key"] in value and canonical(value[args["key"]]) == canonical(args["value"])
        return equal if name == "key_with_value" else not equal
    if name == "key_present":
        return args["key"] in value
    if name in ("list_in_key_contains", "list_in_key_not_contains"):
        items = value.get(args["key"])
        if not isinstance(items, list):
            return False
        present = canonical(args["value"]) in as_set(items)
        return present if name == "list_in_key_contains" else not present
    if name == "list_in_key_not_empty":
        items = value.get(args["key"])
        return isinstance(items, list) and len(items) > 0
    if name == "other_keys":
        return set(value) <= set(args["allowed"])
    raise ValueError(f"unknown condition: {name}")


def load_codebook():
    codebook = yaml.safe_load(CODEBOOK.read_text())
    known = set(codebook["rule_types"])
    fields = {}
    for name, spec in codebook["fields"].items():
        rules = [(r, EQUAL_STATE) for r in spec["equal_to_default"]["values"]]
        rules += [(r, r["decision"]) for r in spec.get("forms", [])]
        rest = spec.get("rest")
        direction = spec.get("direction", {})
        categories = direction.get("categories", [])
        direction_rest = direction.get("rest")
        checked = [r for r, _ in rules] + categories
        checked += [r for r in (rest, direction_rest) if r]
        for rule in checked:
            if rule["type"] not in known:
                raise ValueError(f"{name}: rule {rule['id']} has a type not in rule_types")
        fields[name] = (rules, rest, categories, direction_rest)
    return fields


def direction_of(value, categories, direction_rest):
    """(direction, broadens, rule_id, other_rule_ids) for a modified value.

    The first category that matches decides; other matching categories are
    listed, and if any of them has a different direction the result is
    conflict. With no match, the direction rest rule applies.
    """
    hits = [rule for rule in categories if matches(rule, value)]
    if not hits:
        if direction_rest:
            return (direction_rest["direction"], direction_rest.get("broadens", ""),
                    direction_rest["id"], [])
        return "", "", "", []
    first, others = hits[0], hits[1:]
    other_ids = [rule["id"] for rule in others]
    if any(rule["direction"] != first["direction"] for rule in others):
        return "conflict", "", first["id"], other_ids
    return first["direction"], first.get("broadens", ""), first["id"], other_ids


def classify(value, rules, rest):
    """(state, rule_id, other_rule_ids) for a declared value."""
    hits = [(rule, decision) for rule, decision in rules if matches(rule, value)]
    if not hits:
        if rest and matches(rest, value):
            return rest["decision"], rest["id"], []
        return "no_rule", "", []
    (first, decision), others = hits[0], hits[1:]
    other_ids = [rule["id"] for rule, _ in others]
    if any(d != decision for _, d in others):
        return "conflict", first["id"], other_ids
    return decision, first["id"], other_ids


def field_value(doc, name):
    current = doc
    for key in name.split("."):
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current


def frontmatter_loader():
    spec = importlib.util.spec_from_file_location("keys02", "scripts/02_list_frontmatter_keys.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FrontmatterLoader


def latest_snapshots():
    snapshots = pd.read_parquet(DATA_DIR / "source_markdown_file_snapshot.parquet")
    versions = pd.read_parquet(DATA_DIR / "source_markdown_file_version.parquet")
    repos = pd.read_parquet(DATA_DIR / "repository.parquet")
    latest = versions.loc[versions.groupby("source_markdown_file_history_id")["rank"].idxmax()]
    return (latest[["source_markdown_file_history_id", "source_markdown_file_snapshot_id"]]
            .merge(snapshots, on="source_markdown_file_snapshot_id")
            .merge(repos[["repository_id", "repo_full_name"]], on="repository_id", how="left")
            .sort_values("source_markdown_file_history_id"))


def parse(text, loader):
    try:
        doc = yaml.load(text, Loader=loader)
    except yaml.YAMLError as error:
        return None, f"yaml error: {str(error).splitlines()[0]}"
    if doc is None:
        return None, "empty frontmatter"
    if not isinstance(doc, dict):
        return None, f"not a dict: {type(doc).__name__}"
    return doc, ""


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    fields = load_codebook()
    loader = frontmatter_loader()

    measurement, excluded = [], []
    for _, row in latest_snapshots().iterrows():
        ids = [row["source_markdown_file_history_id"], row["source_markdown_file_snapshot_id"],
               row["repo_full_name"], row["path"]]
        doc, reason = parse(row["frontmatter"], loader)
        if doc is None:
            excluded.append(ids + [reason])
            continue
        for name, (rules, rest, categories, direction_rest) in fields.items():
            declared, value = field_value(doc, name)
            if declared:
                state, rule_id, others = classify(value, rules, rest)
                written = canonical(value)
            else:
                state, rule_id, others, written = "implicit", "", [], ""
            if state == "modified":
                d_dir, d_broadens, d_rule, d_others = direction_of(value, categories, direction_rest)
                d_others = json.dumps(d_others)
            else:
                d_dir, d_broadens, d_rule, d_others = "", "", "", ""
            measurement.append(ids + [name, declared, written, state, rule_id, json.dumps(others),
                                      d_dir, d_broadens, d_rule, d_others])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    header = ["history_id", "snapshot_id", "repo_full_name", "path"]
    write_csv(OUTPUT_DIR / "measurement.csv",
              header + ["field", "declared", "value", "state", "rule_id", "other_rules",
                        "direction", "broadens", "direction_rule_id", "direction_other_rules"],
              measurement)
    write_csv(OUTPUT_DIR / "excluded.csv", header + ["reason"], excluded)

    states = Counter((m[4], m[7]) for m in measurement)
    write_csv(OUTPUT_DIR / "summary.csv", ["field", "state", "workflows"],
              [[f, s, n] for (f, s), n in sorted(states.items())])

    for state_or_rule, filename in [("no_rule", "no_rule.csv"), ("rest", "rest.csv")]:
        if state_or_rule == "no_rule":
            selected = [m for m in measurement if m[7] == "no_rule"]
        else:
            rest_ids = {rest["id"] for _, rest, _, _ in fields.values() if rest}
            selected = [m for m in measurement if m[8] in rest_ids]
        counts = Counter((m[4], m[6]) for m in selected)
        write_csv(OUTPUT_DIR / filename, ["field", "value", "workflows"],
                  [[f, v, n] for (f, v), n in sorted(counts.items(), key=lambda x: (x[0][0], -x[1]))])

    modified = [m for m in measurement if m[7] == "modified"]
    directions = Counter((m[4], m[10], m[11]) for m in modified)
    write_csv(OUTPUT_DIR / "direction_summary.csv", ["field", "direction", "broadens", "workflows"],
              [[f, d, a, n] for (f, d, a), n in sorted(directions.items())])

    checks = []
    for name in fields:
        rows = [m for m in modified if m[4] == name]
        checks.append([name, len(rows),
                       sum(m[13] not in ("", "[]") for m in rows),
                       sum(m[10] == "conflict" for m in rows)])
    write_csv(OUTPUT_DIR / "direction_overlaps.csv",
              ["field", "modified", "overlaps", "conflicts"], checks)

    direction_rest_ids ={r["id"] for _, _, _, r in fields.values() if r}
    write_csv(OUTPUT_DIR / "direction_rest.csv",
              header + ["field", "value", "direction_rule_id"],
              [m[:4] + [m[4], m[6], m[12]] for m in modified if m[12] in direction_rest_ids])

    # Commands added by lists in ADDED_COMMANDS_RULE, outside the codebook's default list.
    default_commands = set(yaml.safe_load(CODEBOOK.read_text())["fields"]["tools.bash"]["default"])
    added = Counter(command for m in modified if m[12] == ADDED_COMMANDS_RULE
                    for command in set(json.loads(m[6])) - default_commands)
    write_csv(OUTPUT_DIR / "bash_added_commands.csv", ["command", "workflows"],
              sorted(added.items(), key=lambda x: (-x[1], x[0])))

    with open("config/settings.yaml") as f:
        dataset = yaml.safe_load(f)["dataset"]
    provenance = {
        "codebook": str(CODEBOOK),
        "codebook_sha256": sha256_of(CODEBOOK),
        "dataset_repo_id": dataset["repo_id"],
        "dataset_revision": dataset["revision"],
        "input_sha256": {t: sha256_of(DATA_DIR / f"{t}.parquet") for t in TABLES},
        "workflows_measured": len({m[0] for m in measurement}),
        "workflows_excluded": len(excluded),
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Measured: {provenance['workflows_measured']}, excluded: {len(excluded)}")
    for (field, state), n in sorted(states.items()):
        print(f"{field} {state}: {n}")


if __name__ == "__main__":
    main()
