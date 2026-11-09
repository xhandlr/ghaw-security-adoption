"""Build the final RQ2 coding sheet and summarize it. Read-only on the coders' sheets.

Each of the 240 sample rows takes its values from one source:
- rows 1 to 70 (coded by both coders): coding/rq2_coding_consensus.csv,
  built by script 26;
- odd rows from 71: coding/rq2_coding_coder1.csv;
- even rows from 72: coding/rq2_coding_coder2.csv.
The decisions in coding/rq2_final_decisions.csv (one row per orden and
field, same columns as coding/rq2_consensus_decisions.csv) are then applied.

Checks, each of which stops the script:
- the three sheets have the same archivo, repositorio and workflow for each orden;
- every row has tiene_defensa "true" or "false";
- every decision points to a sample row, a known column and the right archivo;
- every categoria is listed in config/settings.yaml (rq2.categories);
- copies of the same body (results/23_rq2_workflow_families/body_copies.csv)
  have the same tiene_defensa.

Writes coding/rq2_coding_final.csv (with a fuente column: consenso, coder1
or coder2) and, to results/22_rq2_summary/:
- summary.csv: workflows with at least one defensive instruction over the
  240 rows and over the distinct bodies (each copy group counted once),
  with 95% Wilson intervals;
- categories.csv: workflows with defense per categoria_provisional
  (written as provisional_category);
- categories_consolidated.csv: workflows with defense per consolidated
  categoria (written as category; a workflow may have more than one,
  separated by |);
- by_owner.csv: workflows with defense per owner;
- provenance.json: SHA-256 of every input and output;
- results/22_rq2_summary/pilot/: summary.csv, categories.csv and categories_consolidated.csv for
  the pilot (rows 1 to 30 of the consensus sheet), in the original format.
"""

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

CONSENSUS = Path("coding/rq2_coding_consensus.csv")
CODER1 = Path("coding/rq2_coding_coder1.csv")
CODER2 = Path("coding/rq2_coding_coder2.csv")
DECISIONS = Path("coding/rq2_final_decisions.csv")
COPIES = Path("results/23_rq2_workflow_families/body_copies.csv")
CODEBOOK = Path("coding/rq2_codebook.md")
FINAL = Path("coding/rq2_coding_final.csv")
OUTPUT_DIR = Path("results/22_rq2_summary")
PILOT_DIR = OUTPUT_DIR / "pilot"
ID_COLUMNS = ["archivo", "repositorio", "workflow"]
VALUES = {"true", "false"}
DOUBLE_CODED = 70
PILOT_ROWS = 30
CATEGORY_SEPARATOR = "|"
Z_95 = 1.959963984540054  # two-sided 95% normal quantile


def wilson_interval(successes, n, z=Z_95):
    p = successes / n
    denominator = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denominator
    half_width = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denominator
    return center - half_width, center + half_width


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    sheet = pd.read_csv(path, dtype=str, keep_default_na=False)
    sheet["tiene_defensa"] = sheet["tiene_defensa"].str.strip().str.lower()
    return sheet.set_index("orden")


def categories_of(cell):
    # a category repeated in the same cell counts once for that workflow
    return sorted({c.strip() for c in cell.split(CATEGORY_SEPARATOR) if c.strip()})


def build_final():
    consensus, coder1, coder2 = load(CONSENSUS), load(CODER1), load(CODER2)
    order = list(coder1.index)
    if list(coder2.index) != order:
        raise SystemExit("Coder sheets list different orden values")
    mismatched = [o for o in order
                  if list(coder1.loc[o, ID_COLUMNS]) != list(coder2.loc[o, ID_COLUMNS])
                  or (o in consensus.index
                      and list(consensus.loc[o, ID_COLUMNS]) != list(coder1.loc[o, ID_COLUMNS]))]
    if mismatched:
        raise SystemExit(f"Identification columns differ for orden: {mismatched}")

    rows = []
    for o in order:
        if int(o) <= DOUBLE_CODED:
            if o not in consensus.index:
                raise SystemExit(f"Orden {o} is missing from the consensus sheet")
            row, source = consensus.loc[o].drop("fuente").copy(), "consenso"
        elif int(o) % 2:
            row, source = coder1.loc[o].copy(), "coder1"
        else:
            row, source = coder2.loc[o].copy(), "coder2"
        row["fuente"] = source
        rows.append(row)
    final = pd.DataFrame(rows)
    final.index.name = "orden"

    decisions = pd.read_csv(DECISIONS, dtype=str, keep_default_na=False)
    for _, d in decisions.iterrows():
        o, column = d["orden"], d["campo"]
        if o not in final.index:
            raise SystemExit(f"Decision for orden {o}, which is not in the sample")
        if column not in final.columns or column in ID_COLUMNS + ["fuente"]:
            raise SystemExit(f"Decision for orden {o} uses an unknown or protected column: {column}")
        if d["archivo"] != final.loc[o, "archivo"]:
            raise SystemExit(f"Decision for orden {o} names {d['archivo']}, sheet has {final.loc[o, 'archivo']}")
        if final.loc[o, column] != d["valor"]:
            final.loc[o, column] = d["valor"]
            final.loc[o, "fuente"] = "consenso"

    invalid = [o for o in final.index if final.loc[o, "tiene_defensa"] not in VALUES]
    if invalid:
        raise SystemExit(f"tiene_defensa is not true or false for orden: {invalid}")
    return final


def write_pilot(final, allowed, output_dir):
    pilot = final[[int(o) <= PILOT_ROWS for o in final.index]]
    with_defense = pilot[pilot["tiene_defensa"] == "true"]
    n, k = len(pilot), len(with_defense)
    low, high = wilson_interval(k, n)
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sheet_rows", "coded_rows", "with_defense", "proportion",
                         "wilson_95_low", "wilson_95_high"])
        writer.writerow([n, n, k, k / n, low, high])
    provisional = Counter(c.strip() or "(no category)" for c in with_defense["categoria_provisional"])
    with open(output_dir / "categories.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["provisional_category", "workflows"])
        writer.writerows(sorted(provisional.items(), key=lambda x: (-x[1], x[0])))
    consolidated = Counter(c for cell in pilot["categoria"] for c in categories_of(cell))
    with open(output_dir / "categories_consolidated.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "workflows"])
        writer.writerows([c, consolidated[c]] for c in allowed)
    print(f"Pilot: {k} of {n} with defense ({k / n:.3f}, Wilson 95% [{low:.3f}, {high:.3f}])")


def main():
    with open("config/settings.yaml") as f:
        allowed = yaml.safe_load(f)["rq2"]["categories"]

    final = build_final()
    unknown = sorted({c for cell in final["categoria"] for c in categories_of(cell)} - set(allowed))
    if unknown:
        raise SystemExit(f"Categories not in rq2.categories: {unknown}")

    by_key = {(r["repositorio"], r["workflow"].split("/")[-1]): o for o, r in final.iterrows()}
    group_of = {}
    with open(COPIES, newline="") as f:
        for r in csv.DictReader(f):
            if r["in_sample"] == "True":
                group_of[by_key[(r["repository"], r["filename"])]] = r["copy_group"]
    values_by_group = {}
    for o, g in group_of.items():
        values_by_group.setdefault(g, set()).add(final.loc[o, "tiene_defensa"])
    conflicting = sorted(g for g, v in values_by_group.items() if len(v) > 1)
    if conflicting:
        raise SystemExit(f"Copies of the same body coded differently: {conflicting}")

    final.reset_index().to_csv(FINAL, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")

    with_defense = final[final["tiene_defensa"] == "true"]
    seen, distinct, distinct_with_defense = set(), 0, 0
    for o, r in final.iterrows():
        g = group_of.get(o)
        if g:
            if g in seen:
                continue
            seen.add(g)
        distinct += 1
        distinct_with_defense += r["tiene_defensa"] == "true"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["population", "workflows", "with_defense", "proportion",
                         "wilson_95_low", "wilson_95_high"])
        for population, k, n in [("sample", len(with_defense), len(final)),
                                 ("distinct_bodies", distinct_with_defense, distinct)]:
            low, high = wilson_interval(k, n)
            writer.writerow([population, n, k, k / n, low, high])

    provisional = Counter(c.strip() or "(no category)" for c in with_defense["categoria_provisional"])
    with open(OUTPUT_DIR / "categories.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["provisional_category", "workflows"])
        writer.writerows(sorted(provisional.items(), key=lambda x: (-x[1], x[0])))

    consolidated = Counter(c for cell in with_defense["categoria"] for c in categories_of(cell))
    with open(OUTPUT_DIR / "categories_consolidated.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["category", "workflows"])
        writer.writerows([c, consolidated[c]] for c in allowed)

    owners = Counter(r.split("/")[0] for r in with_defense["repositorio"])
    with open(OUTPUT_DIR / "by_owner.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["owner", "with_defense"])
        writer.writerows(sorted(owners.items(), key=lambda x: (-x[1], x[0])))

    write_pilot(final, allowed, PILOT_DIR)

    inputs = [CONSENSUS, CODER1, CODER2, DECISIONS, COPIES, CODEBOOK]
    outputs = [FINAL] + sorted(OUTPUT_DIR.glob("*.csv")) + sorted(PILOT_DIR.glob("*.csv"))
    provenance = {
        "inputs_sha256": {str(p): sha256_of(p) for p in inputs},
        "outputs_sha256": {str(p): sha256_of(p) for p in outputs},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    multi = sum(len(categories_of(c)) > 1 for c in with_defense["categoria"])
    print(f"Final sheet: {len(final)} rows -> {FINAL}; with defense {len(with_defense)}; "
          f"distinct bodies {distinct_with_defense}/{distinct}; more than one category {multi}")


if __name__ == "__main__":
    main()
