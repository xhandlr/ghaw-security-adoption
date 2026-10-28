"""Compare the two RQ1 coders on a range of rows. Read-only on the sheets.

Reads coding/rq1_security_coding_coder1.csv (coder 1) and
coding/rq1_security_coding_coder2.csv (coder 2), joined by row number
(1-based, in file order). Stops if the path differs for the same row, if
any row in the range is not coded by both coders, or if is_security_field
has a value other than "true" or "false".

Usage: python scripts/17_rq1_intercoder_agreement.py FIRST LAST
Rows 1-190 are the calibration set, rows 191-270 the second set and rows
271-386 the third set. Rows 191-386 together give the overall agreement
outside calibration.

Writes to results/17_rq1_intercoder_agreement/rows_FIRST-LAST/:
- agreement.csv: rows compared, percent agreement, Cohen's kappa (left
  empty, with a note, when it is undefined), and positive and negative
  agreement on is_security_field;
- confusion_is_security_field.csv: 2x2 table, coder 1 in rows, coder 2 in
  columns;
- disagreements.csv: rows where is_security_field differs, with both
  coders' rationale and notes side by side;
- provenance.json: SHA-256 of both sheets and of the coding guide.
"""

import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

CODER1 = Path("coding/rq1_security_coding_coder1.csv")
CODER2 = Path("coding/rq1_security_coding_coder2.csv")
GUIDE = Path("coding/rq1_security_coding_guide.md")
OUTPUT_ROOT = Path("results/17_rq1_intercoder_agreement")
VALUES = ["true", "false"]


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    sheet = pd.read_csv(path, dtype=str, keep_default_na=False)
    sheet["is_security_field"] = sheet["is_security_field"].str.strip()
    unexpected = sorted(set(sheet["is_security_field"]) - set(VALUES) - {""})
    if unexpected:
        raise SystemExit(f"{path}: unexpected is_security_field values {unexpected}")
    sheet.index = range(1, len(sheet) + 1)
    return sheet


def cohen_kappa(a, b):
    """(kappa, note) for two equal-length lists of labels."""
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = sum((a.count(v) / n) * (b.count(v) / n) for v in VALUES)
    if expected == 1:
        return None, "undefined: both coders used a single, identical value"
    return (observed - expected) / (1 - expected), ""


def specific_agreement(a, b, value):
    """Proportion of specific agreement on value: 2 * both / (count in a + count in b)."""
    both = sum(x == value and y == value for x, y in zip(a, b))
    total = a.count(value) + b.count(value)
    return 2 * both / total if total else None


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/17_rq1_intercoder_agreement.py FIRST LAST")
    first, last = int(sys.argv[1]), int(sys.argv[2])
    coder1, coder2 = load(CODER1), load(CODER2)
    if not 1 <= first <= last <= min(len(coder1), len(coder2)):
        raise SystemExit(f"Row range {first}-{last} is outside the sheets")

    rows = list(range(first, last + 1))
    mismatched = [r for r in rows if coder1.loc[r, "path"] != coder2.loc[r, "path"]]
    if mismatched:
        raise SystemExit(f"Paths differ for rows: {mismatched}")
    uncoded = [r for r in rows
               if coder1.loc[r, "is_security_field"] not in VALUES
               or coder2.loc[r, "is_security_field"] not in VALUES]
    if uncoded:
        raise SystemExit(f"Rows not coded by both coders: {uncoded}")

    a = [coder1.loc[r, "is_security_field"] for r in rows]
    b = [coder2.loc[r, "is_security_field"] for r in rows]
    agree = sum(x == y for x, y in zip(a, b))
    kappa, note = cohen_kappa(a, b)
    positive = specific_agreement(a, b, "true")
    negative = specific_agreement(a, b, "false")

    output_dir = OUTPUT_ROOT / f"rows_{first}-{last}"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "agreement.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["measure", "rows_compared", "agreements", "percent_agreement",
                         "cohen_kappa", "positive_agreement", "negative_agreement", "note"])
        writer.writerow(["is_security_field", len(rows), agree, agree / len(rows),
                         "" if kappa is None else kappa,
                         "" if positive is None else positive,
                         "" if negative is None else negative, note])

    with open(output_dir / "confusion_is_security_field.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["coder1 \\ coder2", *VALUES])
        for v1 in VALUES:
            writer.writerow([v1, *[sum(x == v1 and y == v2 for x, y in zip(a, b)) for v2 in VALUES]])

    detail = ["is_security_field", "rationale", "notes"]
    with open(output_dir / "disagreements.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row", "path"] + [f"{c}_{k}" for c in detail for k in ("coder1", "coder2")])
        for r, x, y in zip(rows, a, b):
            if x != y:
                writer.writerow([r, coder1.loc[r, "path"]]
                                + [v for c in detail for v in (coder1.loc[r, c], coder2.loc[r, c])])

    provenance = {
        "coder1_sheet": str(CODER1),
        "coder1_sheet_sha256": sha256_of(CODER1),
        "coder2_sheet": str(CODER2),
        "coder2_sheet_sha256": sha256_of(CODER2),
        "guide": str(GUIDE),
        "guide_sha256": sha256_of(GUIDE),
        "rows": [first, last],
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(output_dir.glob("*.csv"))},
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Rows {first}-{last}: agreement {agree}/{len(rows)}; kappa "
          + ("undefined" if kappa is None else f"{kappa:.3f}"))


if __name__ == "__main__":
    main()
