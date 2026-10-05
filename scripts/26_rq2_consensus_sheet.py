"""Build the RQ2 consensus coding sheet. Read-only on both coders' sheets.

Starts from the rows coded by both coders in coding/rq2_coding_coder1.csv
and coding/rq2_coding_coder2.csv (tiene_defensa "true" or "false" in
both). Every row starts with the first coder's values, which include the
consolidated categoria column. The decisions in
coding/rq2_consensus_decisions.csv (one row per orden and field, with the
agreed value and the reason) are then applied.

Checks, each of which stops the script:
- both sheets have the same archivo, repositorio and workflow for each orden;
- every decision points to a compared row, a known column and the right archivo;
- every row where the coders disagree on tiene_defensa has a decision for it;
- every resulting categoria is listed in config/settings.yaml (rq2.categories).

Writes coding/rq2_coding_consensus.csv with a fuente column: "coder1" when
the row is unchanged, "consenso" when at least one decision changed it.
A decision whose value equals the first coder's value is recorded but
changes nothing. Never overwrites the consensus sheet if it already exists.
"""

import csv
from pathlib import Path

import pandas as pd
import yaml

CODER1 = Path("coding/rq2_coding_coder1.csv")
CODER2 = Path("coding/rq2_coding_coder2.csv")
DECISIONS = Path("coding/rq2_consensus_decisions.csv")
OUTPUT = Path("coding/rq2_coding_consensus.csv")
ID_COLUMNS = ["archivo", "repositorio", "workflow"]
VALUES = {"true", "false"}
CATEGORY_SEPARATOR = "|"


def load(path):
    sheet = pd.read_csv(path, dtype=str, keep_default_na=False)
    sheet["tiene_defensa"] = sheet["tiene_defensa"].str.strip()
    return sheet.set_index("orden")


def main():
    if OUTPUT.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {OUTPUT}")
    with open("config/settings.yaml") as f:
        allowed = set(yaml.safe_load(f)["rq2"]["categories"])

    coder1, coder2 = load(CODER1), load(CODER2)
    common = coder1.index.intersection(coder2.index)
    mismatched = [o for o in common if list(coder1.loc[o, ID_COLUMNS]) != list(coder2.loc[o, ID_COLUMNS])]
    if mismatched:
        raise SystemExit(f"Identification columns differ for orden: {mismatched}")
    both = [o for o in common
            if coder1.loc[o, "tiene_defensa"] in VALUES and coder2.loc[o, "tiene_defensa"] in VALUES]

    consensus = coder1.loc[both].copy()
    consensus["fuente"] = "coder1"

    decisions = pd.read_csv(DECISIONS, dtype=str, keep_default_na=False)
    for _, d in decisions.iterrows():
        o, column = d["orden"], d["campo"]
        if o not in consensus.index:
            raise SystemExit(f"Decision for orden {o}, which was not coded by both coders")
        if column not in consensus.columns or column in ID_COLUMNS + ["fuente"]:
            raise SystemExit(f"Decision for orden {o} uses an unknown or protected column: {column}")
        if d["archivo"] != consensus.loc[o, "archivo"]:
            raise SystemExit(f"Decision for orden {o} names {d['archivo']}, sheet has {consensus.loc[o, 'archivo']}")
        if consensus.loc[o, column] != d["valor"]:
            consensus.loc[o, column] = d["valor"]
            consensus.loc[o, "fuente"] = "consenso"

    decided = set(decisions.loc[decisions["campo"] == "tiene_defensa", "orden"])
    unresolved = [o for o in both
                  if coder1.loc[o, "tiene_defensa"] != coder2.loc[o, "tiene_defensa"] and o not in decided]
    if unresolved:
        raise SystemExit(f"Disagreements on tiene_defensa without a decision: {unresolved}")

    unknown = sorted({c.strip() for cell in consensus["categoria"]
                      for c in cell.split(CATEGORY_SEPARATOR) if c.strip()} - allowed)
    if unknown:
        raise SystemExit(f"Categories not in rq2.categories: {unknown}")

    consensus.reset_index().to_csv(OUTPUT, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    changed = sorted(consensus.index[consensus["fuente"] == "consenso"], key=int)
    print(f"Consensus sheet: {len(consensus)} rows -> {OUTPUT}; changed by decisions: {changed}")


if __name__ == "__main__":
    main()
