"""Extract every field from the GH-AW frontmatter JSON Schema.

Downloads the schema at a pinned commit from github/gh-aw, then walks it
to list every field path with its type, description, and default. Marks
(for prioritization only, not for deciding inclusion) whether the
description contains a keyword from config/keywords_docs.yaml.

The schema is large and uses $ref, oneOf/anyOf, and patternProperties.
This script resolves those, but caps how deep it follows nested fields
(MAX_PATH_DEPTH) as a safety net against runaway or circular references.
It does not look inside array "items" schemas.
"""

import csv
import json
import urllib.request
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
    return local_path


def resolve_ref(schema, definitions):
    if isinstance(schema, dict) and "$ref" in schema:
        ref_name = schema["$ref"].rsplit("/", 1)[-1]
        return definitions.get(ref_name, {})
    return schema


def flatten_schema(root_schema, definitions):
    """Return a list of (path, type, description, default) for every named field."""
    results = []
    pending = [("", root_schema)]

    while pending:
        prefix, schema = pending.pop()
        schema = resolve_ref(schema, definitions)
        if not isinstance(schema, dict):
            continue
        if prefix.count(".") >= MAX_PATH_DEPTH:
            continue

        for branch in schema.get("oneOf", []) + schema.get("anyOf", []):
            pending.append((prefix, branch))

        for key, subschema in schema.get("properties", {}).items():
            path = key if prefix == "" else prefix + "." + key
            resolved = resolve_ref(subschema, definitions)
            results.append((
                path,
                resolved.get("type", ""),
                resolved.get("description", ""),
                resolved.get("default", ""),
            ))
            pending.append((path, subschema))

        for _pattern, subschema in schema.get("patternProperties", {}).items():
            path = "*" if prefix == "" else prefix + ".*"
            resolved = resolve_ref(subschema, definitions)
            results.append((
                path,
                resolved.get("type", ""),
                resolved.get("description", ""),
                resolved.get("default", ""),
            ))
            pending.append((path, subschema))

    return results


def load_keywords():
    with open("config/keywords_docs.yaml") as f:
        doc = yaml.safe_load(f)
    return [kw.lower() for kw in (doc or {}).get("keywords", [])]


def main():
    settings = load_settings()
    schema_cfg = settings["gh_aw_schema"]
    raw_dir = Path(settings["paths"]["raw_dir"])

    local_path = download_schema(schema_cfg["repo"], schema_cfg["path"], schema_cfg["commit"], raw_dir)
    schema_doc = json.loads(local_path.read_text())
    definitions = schema_doc.get("definitions", schema_doc.get("$defs", {}))

    fields = flatten_schema(schema_doc, definitions)
    keywords = load_keywords()

    output_dir = Path("results/03_schema_fields")
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "fields.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["field_path", "type", "description", "default", "matches_keyword"])
        seen = set()
        for path, field_type, description, default in fields:
            if path in seen:
                continue
            seen.add(path)
            matches = any(kw in description.lower() for kw in keywords)
            writer.writerow([path, field_type, description, default, matches])

    print(f"Schema commit: {schema_cfg['commit']}")
    print(f"Distinct field paths extracted: {len(seen)}")


if __name__ == "__main__":
    main()
