"""List every root-level (no-dot) field in the full GH-AW schema.

Unlike the earlier root list in results/02_frontmatter_keys/, which only
included keys that some workflow actually used, this reads every root
from results/03_schema_fields/fields.csv (the full schema, ~4000 fields),
so a security-relevant field nobody happens to use is still included.
"""

import csv
import hashlib
import json
from pathlib import Path

FIELDS_CSV = "results/03_schema_fields/fields.csv"
FIELDS_PROVENANCE = "results/03_schema_fields/provenance.json"


def main():
    with open(FIELDS_CSV) as f:
        schema_rows = list(csv.DictReader(f))
    schema_roots = sorted(set(r["field_path"] for r in schema_rows if "." not in r["field_path"]))

    with open("results/02_frontmatter_keys/keys_latest_version.csv") as f:
        observed_rows = list(csv.DictReader(f))
    observed_roots = set(r["key_path"] for r in observed_rows if "." not in r["key_path"])

    schema_root_set = set(schema_roots)
    only_in_schema = sorted(schema_root_set - observed_roots)
    only_in_data = sorted(observed_roots - schema_root_set)

    output_dir = Path("results/10_rq1_schema_roots")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "schema_roots.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["field_path", "used_by_some_workflow"])
        for root in schema_roots:
            writer.writerow([root, root in observed_roots])

    with open(output_dir / "only_in_schema_never_used.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["field_path"])
        writer.writerows([[r] for r in only_in_schema])

    with open(output_dir / "only_in_data_not_in_schema.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["field_path"])
        writer.writerows([[r] for r in only_in_data])

    fields_sha256 = hashlib.sha256(Path(FIELDS_CSV).read_bytes()).hexdigest()
    upstream = json.loads(Path(FIELDS_PROVENANCE).read_text())
    provenance = {
        "fields_csv": FIELDS_CSV,
        "fields_csv_sha256": fields_sha256,
        "matches_03_provenance": fields_sha256 == upstream["fields_csv_sha256"],
        "schema_commit": upstream["commit"],
        "schema_sha256": upstream["schema_sha256"],
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Total schema roots: {len(schema_roots)}")
    print(f"In schema, never used by any workflow: {len(only_in_schema)}")
    print(f"In data, not in current schema: {len(only_in_data)}")


if __name__ == "__main__":
    main()
