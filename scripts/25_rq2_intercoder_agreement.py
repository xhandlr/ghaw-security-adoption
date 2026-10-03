"""Compare the two RQ2 coders on the rows both have coded. Read-only on the sheets.

Reads coding/rq2_coding.csv (coder 1) and coding/rq2_coding_coder2.csv
(coder 2), joined by orden. Stops if archivo, repositorio or workflow
differ for the same orden. Only rows where both coders wrote "true" or
"false" in tiene_defensa are compared; any other non-empty value stops
the script.

Writes to results/25_rq2_intercoder_agreement/:
- agreement.csv: rows compared, percent agreement and Cohen's kappa on
  tiene_defensa (kappa is left empty, with a note, when it is undefined);
- confusion_tiene_defensa.csv: 2x2 table, coder 1 in rows, coder 2 in
  columns;
- disagreements.csv: rows where tiene_defensa differs, with both coders'
  phrase, line and notes side by side;
- categories_side_by_side.csv: rows that either coder marked with defense,
  with both coders' categories side by side, for joint consolidation (no
  agreement is computed on categories);
- provenance.json: SHA-256 of both sheets and of the codebook.
"""

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd

CODER1 = Path("coding/rq2_coding.csv")
CODER2 = Path("coding/rq2_coding_coder2.csv")
CODEBOOK = Path("coding/rq2_codebook.md")
OUTPUT_DIR = Path("results/25_rq2_intercoder_agreement")
ID_COLUMNS = ["archivo", "repositorio", "workflow"]
VALUES = ["true", "false"]


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    sheet = pd.read_csv(path, dtype=str, keep_default_na=False)
    sheet["tiene_defensa"] = sheet["tiene_defensa"].str.strip()
    unexpected = sorted(set(sheet["tiene_defensa"]) - set(VALUES) - {""})
    if unexpected:
        raise SystemExit(f"{path}: unexpected tiene_defensa values {unexpected}")
    return sheet.set_index("orden")


def cohen_kappa(a, b):
    """(kappa, note) for two equal-length lists of labels."""
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = sum((a.count(v) / n) * (b.count(v) / n) for v in VALUES)
    if expected == 1:
        return None, "undefined: both coders used a single, identical value"
    return (observed - expected) / (1 - expected), ""


def main():
    coder1, coder2 = load(CODER1), load(CODER2)

    common = coder1.index.intersection(coder2.index)
    mismatched = [o for o in common if list(coder1.loc[o, ID_COLUMNS]) != list(coder2.loc[o, ID_COLUMNS])]
    if mismatched:
        raise SystemExit(f"Identification columns differ for orden: {mismatched}")

    both = [o for o in common
            if coder1.loc[o, "tiene_defensa"] in VALUES and coder2.loc[o, "tiene_defensa"] in VALUES]
    if not both:
        raise SystemExit("No rows coded by both coders yet")
    a = [coder1.loc[o, "tiene_defensa"] for o in both]
    b = [coder2.loc[o, "tiene_defensa"] for o in both]
    agree = sum(x == y for x, y in zip(a, b))
    kappa, note = cohen_kappa(a, b)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "agreement.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["measure", "rows_compared", "agreements", "percent_agreement",
                         "cohen_kappa", "note"])
        writer.writerow(["tiene_defensa", len(both), agree, agree / len(both),
                         "" if kappa is None else kappa, note])

    with open(OUTPUT_DIR / "confusion_tiene_defensa.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["coder1 \\ coder2", *VALUES])
        for v1 in VALUES:
            writer.writerow([v1, *[sum(x == v1 and y == v2 for x, y in zip(a, b)) for v2 in VALUES]])

    def side_by_side(o, columns):
        row = [o, coder1.loc[o, "archivo"]]
        for column in columns:
            row += [coder1.loc[o].get(column, ""), coder2.loc[o].get(column, "")]
        return row

    detail = ["tiene_defensa", "frase_textual", "linea", "notas"]
    with open(OUTPUT_DIR / "disagreements.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["orden", "archivo"] + [f"{c}_{k}" for c in detail for k in ("coder1", "coder2")])
        writer.writerows(side_by_side(o, detail) for o, x, y in zip(both, a, b) if x != y)

    category_columns = ["tiene_defensa", "categoria_provisional", "categoria", "frase_textual"]
    with open(OUTPUT_DIR / "categories_side_by_side.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["orden", "archivo"]
                        + [f"{c}_{k}" for c in category_columns for k in ("coder1", "coder2")])
        writer.writerows(side_by_side(o, category_columns)
                         for o, x, y in zip(both, a, b) if "true" in (x, y))

    provenance = {
        "coder1_sheet": str(CODER1),
        "coder1_sheet_sha256": sha256_of(CODER1),
        "coder2_sheet": str(CODER2),
        "coder2_sheet_sha256": sha256_of(CODER2),
        "codebook": str(CODEBOOK),
        "codebook_sha256": sha256_of(CODEBOOK),
        "rows_compared": len(both),
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Compared {len(both)} rows; agreement {agree}/{len(both)}; kappa "
          + ("undefined" if kappa is None else f"{kappa:.3f}"))


if __name__ == "__main__":
    main()
