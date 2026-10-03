"""Summarize the RQ2 pilot coding done so far. Read-only on the sheet.

Reads coding/rq2_coding_coder1.csv and keeps only the rows already coded
(tiene_defensa is "true" or "false"). Any other non-empty value in
tiene_defensa stops the script, so a typo is never silently counted.

Writes to results/22_rq2_pilot_summary/:
- summary.csv: coded rows, rows with defense, proportion and its 95%
  Wilson interval;
- categories.csv: coded rows with defense per categoria_provisional;
- categories_consolidated.csv: coded rows per consolidated categoria
  (several categories in one cell are separated by |). Only the
  categories listed in config/settings.yaml (rq2.categories) are allowed;
  any other value stops the script;
- provenance.json: SHA-256 of the coding sheet and of the codebook.
"""

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import yaml

CODING_SHEET = Path("coding/rq2_coding_coder1.csv")
CODEBOOK = Path("coding/rq2_codebook.md")
OUTPUT_DIR = Path("results/22_rq2_pilot_summary")
CODED_VALUES = {"true": True, "false": False}
CATEGORY_SEPARATOR = "|"
Z_95 = 1.959963984540054  # two-sided 95% normal quantile


def wilson_interval(successes, n, z=Z_95):
    if n == 0:
        return None, None
    p = successes / n
    denominator = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denominator
    half_width = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denominator
    return center - half_width, center + half_width


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    with open(CODING_SHEET, newline="") as f:
        rows = list(csv.DictReader(f))

    unexpected = sorted({r["tiene_defensa"].strip() for r in rows} - set(CODED_VALUES) - {""})
    if unexpected:
        raise SystemExit(f"Unexpected tiene_defensa values: {unexpected}")

    if rows and "categoria" not in rows[0]:
        raise SystemExit("The coding sheet has no 'categoria' column")
    with open("config/settings.yaml") as f:
        allowed = yaml.safe_load(f)["rq2"]["categories"]

    coded = [r for r in rows if r["tiene_defensa"].strip() in CODED_VALUES]
    consolidated = Counter()
    for r in coded:
        # a category repeated in the same cell counts once for that workflow
        consolidated.update({c.strip() for c in r["categoria"].split(CATEGORY_SEPARATOR) if c.strip()})
    unknown = sorted(set(consolidated) - set(allowed))
    if unknown:
        raise SystemExit(f"Categories not in rq2.categories: {unknown}")
    with_defense = [r for r in coded if CODED_VALUES[r["tiene_defensa"].strip()]]
    n, k = len(coded), len(with_defense)
    low, high = wilson_interval(k, n)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sheet_rows", "coded_rows", "with_defense", "proportion",
                         "wilson_95_low", "wilson_95_high"])
        writer.writerow([len(rows), n, k, k / n if n else "", low if n else "", high if n else ""])

    categories = Counter(r["categoria_provisional"].strip() or "(sin categoría)" for r in with_defense)
    with open(OUTPUT_DIR / "categories.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["categoria_provisional", "workflows"])
        writer.writerows(sorted(categories.items(), key=lambda x: (-x[1], x[0])))

    with open(OUTPUT_DIR / "categories_consolidated.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["categoria", "workflows"])
        writer.writerows([c, consolidated[c]] for c in allowed)

    provenance = {
        "coding_sheet": str(CODING_SHEET),
        "coding_sheet_sha256": sha256_of(CODING_SHEET),
        "codebook": str(CODEBOOK),
        "codebook_sha256": sha256_of(CODEBOOK),
        "coded_rows": n,
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Coded {n} of {len(rows)}; with defense {k}"
          + (f" ({k / n:.3f}, Wilson 95% [{low:.3f}, {high:.3f}])" if n else ""))


if __name__ == "__main__":
    main()
