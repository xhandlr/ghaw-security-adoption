"""Build the RQ1 consensus coding sheet. Read-only on both coders' sheets.

Starts from the rows coded by both coders in
coding/rq1_security_coding_coder1.csv and coding/rq1_security_coding_coder2.csv
(is_security_field "true" or "false" in both), joined by row number
(1-based, in file order). Every row starts with the first coder's values.
The decisions in coding/rq1_consensus_decisions.csv (one row per row number
and field, with the agreed value and the reason) are then applied.

Checks, each of which stops the script:
- both sheets have the same path for each row;
- every decision points to a compared row, a known column and the right path;
- every decided is_security_field is "true" or "false";
- every row where the coders disagree on is_security_field has a decision for it.

Writes coding/rq1_security_coding_consensus.csv with a row column and a
fuente column: "coder1" when the row is unchanged, "consenso" when at least
one decision changed it. A decision whose value equals the first coder's
value is recorded but changes nothing. Never overwrites the consensus sheet
if it already exists.
"""

import csv
from pathlib import Path

import pandas as pd

CODER1 = Path("coding/rq1_security_coding_coder1.csv")
CODER2 = Path("coding/rq1_security_coding_coder2.csv")
DECISIONS = Path("coding/rq1_consensus_decisions.csv")
OUTPUT = Path("coding/rq1_security_coding_consensus.csv")
VALUES = {"true", "false"}


def load(path):
    sheet = pd.read_csv(path, dtype=str, keep_default_na=False)
    sheet["is_security_field"] = sheet["is_security_field"].str.strip()
    sheet.index = [str(r) for r in range(1, len(sheet) + 1)]
    sheet.index.name = "row"
    return sheet


def main():
    if OUTPUT.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {OUTPUT}")

    coder1, coder2 = load(CODER1), load(CODER2)
    common = coder1.index.intersection(coder2.index)
    mismatched = [r for r in common if coder1.loc[r, "path"] != coder2.loc[r, "path"]]
    if mismatched:
        raise SystemExit(f"Paths differ for rows: {mismatched}")
    both = [r for r in common
            if coder1.loc[r, "is_security_field"] in VALUES and coder2.loc[r, "is_security_field"] in VALUES]

    consensus = coder1.loc[both].copy()
    consensus["fuente"] = "coder1"

    decisions = pd.read_csv(DECISIONS, dtype=str, keep_default_na=False)
    for _, d in decisions.iterrows():
        r, column = d["row"], d["campo"]
        if r not in consensus.index:
            raise SystemExit(f"Decision for row {r}, which was not coded by both coders")
        if column not in consensus.columns or column in ("path", "fuente"):
            raise SystemExit(f"Decision for row {r} uses an unknown or protected column: {column}")
        if d["path"] != consensus.loc[r, "path"]:
            raise SystemExit(f"Decision for row {r} names {d['path']}, sheet has {consensus.loc[r, 'path']}")
        if column == "is_security_field" and d["valor"] not in VALUES:
            raise SystemExit(f"Decision for row {r} has an invalid is_security_field: {d['valor']}")
        if consensus.loc[r, column] != d["valor"]:
            consensus.loc[r, column] = d["valor"]
            consensus.loc[r, "fuente"] = "consenso"

    decided = set(decisions.loc[decisions["campo"] == "is_security_field", "row"])
    unresolved = [r for r in both
                  if coder1.loc[r, "is_security_field"] != coder2.loc[r, "is_security_field"]
                  and r not in decided]
    if unresolved:
        raise SystemExit(f"Disagreements on is_security_field without a decision: {unresolved}")

    consensus.reset_index().to_csv(OUTPUT, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    changed = sorted(consensus.index[consensus["fuente"] == "consenso"], key=int)
    print(f"Consensus sheet: {len(consensus)} rows -> {OUTPUT}; changed by decisions: {changed}")


if __name__ == "__main__":
    main()
