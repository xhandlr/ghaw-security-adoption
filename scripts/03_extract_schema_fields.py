"""Extract every field from the GH-AW frontmatter JSON Schema.

Downloads the schema at a pinned commit from github/gh-aw, then walks it
to list every field path with its type, description, and default. Records
the schema's origin (repo, path, commit, SHA-256) in provenance.json.

The schema is large and uses $ref, oneOf/anyOf, patternProperties, and
additionalProperties. Free-form keys from patternProperties and from
additionalProperties (when it is a schema, not true/false) are both written
as * (e.g. jobs.*.permissions); the key_source column says which one.
fields.csv has one row per (field path, oneOf/anyOf branch trace): each row
keeps its own description and default, and no default is ever copied from
one branch to another. fields_by_path.csv summarizes, per path, how many
branches it has and whether they differ, without picking a main branch.

Array "items" are walked; fields inside a list element are marked with []
(e.g. tools.github.allowed[].name). Nesting is capped at MAX_PATH_DEPTH
levels (each "." and each "[]" counts as one) as a safety net against
circular references. Whatever the walk still does not cover is measured
in extraction_limits.csv.
"""

import csv
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

MAX_PATH_DEPTH = 6


def load_settings():
    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)


def download_schema(repo, path, commit, raw_dir):
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    request = urllib.request.Request(url, headers={"User-Agent": "ghaw-security-adoption"})
    with urllib.request.urlopen(request) as response:
        content = response.read()

    raw_dir.mkdir(parents=True, exist_ok=True)
    local_path = raw_dir / "gh_aw_schema.json"
    local_path.write_bytes(content)
    return local_path, url


def resolve_ref(schema, definitions):
    if isinstance(schema, dict) and "$ref" in schema:
        ref_name = schema["$ref"].rsplit("/", 1)[-1]
        return definitions.get(ref_name, {})
    return schema


def child_property_names(schema, definitions, seen_ids=None):
    """Names of properties directly under schema, including through oneOf/anyOf."""
    schema = resolve_ref(schema, definitions)
    if not isinstance(schema, dict):
        return set()
    seen_ids = seen_ids if seen_ids is not None else set()
    if id(schema) in seen_ids:
        return set()
    seen_ids.add(id(schema))

    names = set(schema.get("properties", {}))
    if schema.get("patternProperties"):
        names.add("*")
    for branch in schema.get("oneOf", []) + schema.get("anyOf", []):
        names |= child_property_names(branch, definitions, seen_ids)
    if isinstance(schema.get("items"), dict):
        names |= {"[]." + n for n in child_property_names(schema["items"], definitions, seen_ids)}
    return names


def path_depth(path):
    return path.count(".") + path.count("[]")


def flatten_schema(root_schema, definitions):
    """Walk the schema.

    Returns (fields, limits) where fields is a list of
    (path, branch_trace, key_source, type, description, has_default, default) and limits
    maps a limit type to {path: set of names not walked}.
    """
    fields = []
    limits = {
        "max_depth_cut": {},
        "tuple_items_not_walked": {},
        "allof_not_walked": {},
        "pattern_and_additional_properties": {},
    }
    pending = [("", root_schema, "")]

    def record(path, subschema, trace, key_source):
        resolved = resolve_ref(subschema, definitions)
        fields.append((
            path,
            trace,
            key_source,
            resolved.get("type", ""),
            resolved.get("description", ""),
            "default" in resolved,
            resolved.get("default"),
        ))

    def note(limit_type, path, names):
        if names:
            limits[limit_type].setdefault(path or "<root>", set()).update(names)

    while pending:
        prefix, schema, trace = pending.pop()
        schema = resolve_ref(schema, definitions)
        if not isinstance(schema, dict):
            continue

        if path_depth(prefix) >= MAX_PATH_DEPTH:
            note("max_depth_cut", prefix, child_property_names(schema, definitions))
            continue

        for branch in schema.get("allOf", []):
            note("allof_not_walked", prefix, child_property_names(branch, definitions))
        if schema.get("patternProperties") and isinstance(schema.get("additionalProperties"), dict):
            note("pattern_and_additional_properties", prefix, {"*"})

        items = schema.get("items")
        if isinstance(items, dict):
            pending.append((prefix + "[]", items, trace))
        elif isinstance(items, list):
            for item in items:
                note("tuple_items_not_walked", prefix, child_property_names(item, definitions))

        for kind in ("oneOf", "anyOf"):
            for i, branch in enumerate(schema.get(kind, [])):
                pending.append((prefix, branch, f"{trace}/{prefix or '<root>'}:{kind}[{i}]"))

        for key, subschema in schema.get("properties", {}).items():
            path = key if prefix == "" else prefix + "." + key
            record(path, subschema, trace, "properties")
            pending.append((path, subschema, trace))

        for _pattern, subschema in schema.get("patternProperties", {}).items():
            path = "*" if prefix == "" else prefix + ".*"
            record(path, subschema, trace, "patternProperties")
            pending.append((path, subschema, trace))

        if isinstance(schema.get("additionalProperties"), dict):
            path = "*" if prefix == "" else prefix + ".*"
            record(path, schema["additionalProperties"], trace, "additionalProperties")
            pending.append((path, schema["additionalProperties"], trace))

    return fields, limits


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_fields(fields, fields_path):
    """One row per distinct (path, trace, key_source, type, description, default).

    Returns (row_count, same_path_and_trace_conflicts), the latter being
    (path, trace) pairs that still carry more than one distinct row.
    """
    rows = []
    seen = set()
    for path, trace, key_source, field_type, description, has_default, default in fields:
        default_json = json.dumps(default) if has_default else ""
        row = (path, trace or "<none>", key_source, str(field_type), description, has_default, default_json)
        if row in seen:
            continue
        seen.add(row)
        rows.append(row)

    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    with open(fields_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["field_path", "branch_trace", "key_source", "type", "description", "has_default", "default"])
        writer.writerows(rows)

    per_pair = {}
    for row in rows:
        per_pair.setdefault((row[0], row[1]), []).append(row)
    conflicts = {pair: n for pair, n in per_pair.items() if len(n) > 1}
    return len(rows), conflicts


def write_fields_by_path(fields_path, by_path_path):
    """Derived from fields.csv: one row per path, no branch chosen as main."""
    with open(fields_path) as f:
        rows = list(csv.DictReader(f))
    groups = {}
    for row in rows:
        groups.setdefault(row["field_path"], []).append(row)

    with open(by_path_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["field_path", "n_branches", "n_branches_with_default",
                         "descriptions_differ", "defaults_differ"])
        for path in sorted(groups):
            group = groups[path]
            defaults = {(r["has_default"], r["default"]) for r in group}
            writer.writerow([
                path,
                len(group),
                sum(r["has_default"] == "True" for r in group),
                len({r["description"] for r in group}) > 1,
                len(defaults) > 1,
            ])
    return len(groups)


def main():
    settings = load_settings()
    schema_cfg = settings["gh_aw_schema"]
    raw_dir = Path(settings["paths"]["raw_dir"])

    local_path, url = download_schema(schema_cfg["repo"], schema_cfg["path"], schema_cfg["commit"], raw_dir)
    schema_doc = json.loads(local_path.read_text())
    definitions = schema_doc.get("definitions", schema_doc.get("$defs", {}))

    fields, limits = flatten_schema(schema_doc, definitions)

    output_dir = Path("results/03_schema_fields")
    output_dir.mkdir(parents=True, exist_ok=True)
    fields_path = output_dir / "fields.csv"
    row_count, pair_conflicts = write_fields(fields, fields_path)
    distinct_paths = write_fields_by_path(fields_path, output_dir / "fields_by_path.csv")

    with open(output_dir / "extraction_limits.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["limit_type", "field_path", "detail"])
        for limit_type, affected in limits.items():
            for path in sorted(affected):
                writer.writerow([limit_type, path, json.dumps(sorted(affected[path]))])
        for (path, trace), group in sorted(pair_conflicts.items()):
            detail = {"branch_trace": trace, "distinct_rows": len(group)}
            writer.writerow(["same_path_and_trace_differ", path, json.dumps(detail)])

    summary = {limit_type: len(affected) for limit_type, affected in limits.items()}
    summary["same_path_and_trace_differ"] = len(pair_conflicts)
    with open(output_dir / "extraction_limits_summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["limit_type", "affected_paths"])
        writer.writerows(summary.items())

    provenance = {
        "repo": schema_cfg["repo"],
        "path": schema_cfg["path"],
        "commit": schema_cfg["commit"],
        "url": url,
        "schema_sha256": sha256_of(local_path),
        "fields_csv_sha256": sha256_of(fields_path),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "max_path_depth": MAX_PATH_DEPTH,
        "fields_csv_rows": row_count,
        "distinct_field_paths": distinct_paths,
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Schema commit: {schema_cfg['commit']}")
    print(f"fields.csv rows: {row_count}")
    print(f"Distinct field paths: {distinct_paths}")
    for limit_type, count in summary.items():
        print(f"{limit_type}: {count}")


if __name__ == "__main__":
    main()
