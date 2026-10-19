"""List the level 1 and level 2 schema paths for the RQ1 security coding.

Reads results/03_schema_fields/fields.csv (the gh-aw schema at the pinned
commit, one row per field path and oneOf/anyOf branch, see script 03) and
checks its SHA-256 against script 03's provenance.

Levels: a path's level is its number of "." segments once "[]" is removed,
so a list does not count as a level (enclaves[].runtime is level 2, root
enclaves). Free-form keys stay as * (mcp-servers.* is level 2). Nothing
below level 2 is listed.

One row per path. When a path has several branches, the distinct non-empty
descriptions are joined with " | ", and so are the distinct non-empty types
(in order of appearance). A type that no branch declares is left empty.

Object and list forms of the same field (checkout.fetch and
checkout[].fetch) are merged into one row, written in the object form, only
when both have the same descriptions and types; otherwise both rows are kept.

Paths with no description in any branch are not codable, since the decision
is taken only from the description: they are left out of the coding sheets
and listed in no_description.csv.

Writes to results/16_rq1_security_field_candidates/:
- paths.csv: every listed path with level, root, type, description and, for
  merged rows, the list form merged into it.
- no_description.csv: paths left out because they have no description.
- summary.csv: paths per level and per treatment.
- provenance.json: SHA-256 of fields.csv and of the outputs.

Writes coding/rq1_security_coding_coder1.csv and
coding/rq1_security_coding_coder2.csv: identical sheets with the codable
paths and empty coding columns. Never overwrites either sheet if it exists.
"""

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

FIELDS_DIR = Path("results/03_schema_fields")
FIELDS_CSV = FIELDS_DIR / "fields.csv"
OUTPUT_DIR = Path("results/16_rq1_security_field_candidates")
SHEETS = [Path("coding/rq1_security_coding_coder1.csv"),
          Path("coding/rq1_security_coding_coder2.csv")]
SEPARATOR = " | "
MAX_LEVEL = 2
SHEET_COLUMNS = ["path", "level", "root", "type", "schema_description",
                 "is_security_field", "rationale", "notes"]


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def without_lists(path):
    return path.replace("[].", ".").replace("[]", "")


def level_of(path):
    return len(without_lists(path).split("."))


def distinct(values):
    """Distinct non-empty values, in order of appearance."""
    return list(dict.fromkeys(v for v in values if v))


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    fields_sha = sha256_of(FIELDS_CSV)
    expected = json.loads((FIELDS_DIR / "provenance.json").read_text())["fields_csv_sha256"]
    if fields_sha != expected:
        raise SystemExit(f"fields.csv SHA-256 {fields_sha} does not match 03 provenance {expected}")

    branches = defaultdict(list)
    with open(FIELDS_CSV, newline="") as f:
        for r in csv.DictReader(f):
            if level_of(r["field_path"]) <= MAX_LEVEL:
                branches[r["field_path"]].append(r)

    def described(path):
        rows = branches[path]
        return (SEPARATOR.join(distinct(r["type"] for r in rows)),
                SEPARATOR.join(distinct(r["description"] for r in rows)))

    # Group object and list forms of the same field.
    forms = defaultdict(list)
    for path in branches:
        forms[without_lists(path)].append(path)

    listed, kept_apart = [], 0
    for _, paths in sorted(forms.items()):
        object_forms = [p for p in paths if "[]" not in p]
        if len(paths) > 1 and len({described(p) for p in paths}) == 1 and object_forms:
            merged = sorted(p for p in paths if p != object_forms[0])
            listed.append((object_forms[0], merged))
        else:
            kept_apart += len(paths) > 1
            listed += [(p, []) for p in sorted(paths)]

    rows = []
    for path, merged in listed:
        type_, description = described(path)
        root = without_lists(path).split(".")[0]
        rows.append([path, level_of(path), root, type_, description, "|".join(merged)])
    rows.sort(key=lambda r: (r[2], r[1], r[0]))

    codable = [r for r in rows if r[4]]
    no_description = [r for r in rows if not r[4]]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "paths.csv",
              ["path", "level", "root", "type", "schema_description", "merged_list_forms"], rows)
    write_csv(OUTPUT_DIR / "no_description.csv", ["path", "level", "root", "type"],
              [r[:4] for r in no_description])

    summary = [
        ["level_1_paths", sum(r[1] == 1 for r in rows)],
        ["level_2_paths", sum(r[1] == 2 for r in rows)],
        ["listed_paths", len(rows)],
        ["merged_list_forms", sum(bool(r[5]) for r in rows)],
        ["form_pairs_kept_apart", kept_apart],
        ["paths_with_several_branches", sum(len(branches[r[0]]) > 1 for r in rows)],
        ["paths_without_type", sum(not r[3] for r in rows)],
        ["no_description_paths", len(no_description)],
        ["codable_paths", len(codable)],
        ["codable_level_1", sum(r[1] == 1 for r in codable)],
        ["codable_level_2", sum(r[1] == 2 for r in codable)],
    ]
    write_csv(OUTPUT_DIR / "summary.csv", ["measure", "value"], summary)

    provenance = {
        "fields_csv": str(FIELDS_CSV),
        "fields_csv_sha256": fields_sha,
        "max_level": MAX_LEVEL,
        "separator": SEPARATOR,
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    for sheet in SHEETS:
        if sheet.exists():
            print(f"{sheet} already exists, not overwritten")
            continue
        write_csv(sheet, SHEET_COLUMNS, [r[:5] + ["", "", ""] for r in codable])
        print(f"Coding sheet: {len(codable)} rows -> {sheet}")

    for measure, value in summary:
        print(f"{measure}: {value}")


if __name__ == "__main__":
    main()
