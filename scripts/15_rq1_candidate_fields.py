"""Count the RQ1 candidate fields: schema paths with a declared default.

Reads results/03_schema_fields/fields.csv (one row per field path and
oneOf/anyOf branch, see script 03). Selection rule: a field path is a
candidate when at least one of its exported branches has a declared
default (has_default is True in at least one of its rows). Every other
path is excluded. A path's root is its first level: the part before the
first "." or "[".

Writes to results/15_rq1_candidate_fields/:
- summary.csv: distinct paths, candidate paths, roots of the candidates
  and excluded paths;
- candidates.csv: one row per candidate path, with its root and how many
  of its branches declare a default;
- candidate_roots.csv: one row per root, with its number of candidate paths;
- provenance.json: SHA-256 of fields.csv (checked against script 03's
  provenance) and of the outputs.
"""

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

FIELDS_DIR = Path("results/03_schema_fields")
FIELDS_CSV = FIELDS_DIR / "fields.csv"
OUTPUT_DIR = Path("results/15_rq1_candidate_fields")


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def root_of(path):
    return re.split(r"[.\[]", path, maxsplit=1)[0]


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

    with open(FIELDS_CSV, newline="") as f:
        rows = list(csv.DictReader(f))

    branches_with_default = defaultdict(int)
    paths = set()
    for r in rows:
        paths.add(r["field_path"])
        if r["has_default"] == "True":
            branches_with_default[r["field_path"]] += 1

    candidates = sorted(branches_with_default)
    roots = Counter(root_of(p) for p in candidates)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = [
        ["distinct_paths", len(paths)],
        ["candidate_paths", len(candidates)],
        ["candidate_roots", len(roots)],
        ["excluded_paths", len(paths) - len(candidates)],
    ]
    write_csv(OUTPUT_DIR / "summary.csv", ["measure", "value"], summary)
    write_csv(OUTPUT_DIR / "candidates.csv", ["field_path", "root", "branches_with_default"],
              [[p, root_of(p), branches_with_default[p]] for p in candidates])
    write_csv(OUTPUT_DIR / "candidate_roots.csv", ["root", "candidate_paths"],
              sorted(roots.items(), key=lambda x: (-x[1], x[0])))

    provenance = {
        "fields_csv": str(FIELDS_CSV),
        "fields_csv_sha256": fields_sha,
        "selection_rule": "path with has_default True in at least one exported branch",
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    for measure, value in summary:
        print(f"{measure}: {value}")


if __name__ == "__main__":
    main()
