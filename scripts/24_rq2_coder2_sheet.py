"""Prepare the materials for the second RQ2 coder. Does not code anything.

Writes coding/rq2_coding_coder2.csv: rows 1 to N of coding/rq2_coding_coder1.csv
(N = rq2.coder2_rows in config/settings.yaml), in the same order, with
the identification columns only and empty coding columns. None of the
first coder's decisions, phrases, categories or notes are copied.

Writes coding/rq2_codebook_coder2.md: the version 1 definition from
coding/rq2_codebook.md (from the first paragraph after the version 1
heading up to, not including, the preliminary categories), without the
version note, the categories or version 0, so the second coder builds
their own categories. The file starts with the title in CODEBOOK_TITLE.

Never overwrites either file if it already exists.
"""

from pathlib import Path

import pandas as pd
import yaml

CODING_SHEET = Path("coding/rq2_coding_coder1.csv")
CODEBOOK = Path("coding/rq2_codebook.md")
SHEET_OUT = Path("coding/rq2_coding_coder2.csv")
CODEBOOK_OUT = Path("coding/rq2_codebook_coder2.md")
ID_COLUMNS = ["orden", "archivo", "repositorio", "workflow"]
CODING_COLUMNS = ["tiene_defensa", "frase_textual", "linea", "categoria_provisional", "notas"]
VERSION_1_HEADING = "## Versión 1"
CATEGORIES_HEADING = "### Categorías preliminares del piloto"
CODEBOOK_TITLE = "# Libro de códigos RQ2, versión 1 (segundo codificador)"


def version_1_definition(text):
    """Version 1 body: after its heading and version note, before the categories."""
    start = text.index(VERSION_1_HEADING)
    end = text.index(CATEGORIES_HEADING, start)
    lines = text[start:end].splitlines()[1:]  # drop the version heading
    lines = [line for line in lines if not line.startswith(">")]  # drop the version note
    return "\n".join(lines).strip() + "\n"


def main():
    with open("config/settings.yaml") as f:
        rows_for_coder2 = yaml.safe_load(f)["rq2"]["coder2_rows"]

    existing = [str(p) for p in (SHEET_OUT, CODEBOOK_OUT) if p.exists()]
    if existing:
        raise SystemExit(f"Refusing to overwrite existing file(s): {', '.join(existing)}")

    sheet = pd.read_csv(CODING_SHEET, dtype=str, keep_default_na=False)
    selected = sheet[sheet["orden"].astype(int) <= rows_for_coder2][ID_COLUMNS].copy()
    if len(selected) != rows_for_coder2:
        raise SystemExit(f"Expected {rows_for_coder2} rows, found {len(selected)}")
    missing = [f for f in selected["archivo"] if not (Path("coding/pilot_sample") / f).exists()]
    if missing:
        raise SystemExit(f"Body files missing in coding/pilot_sample/: {missing}")
    for column in CODING_COLUMNS:
        selected[column] = ""

    definition = version_1_definition(CODEBOOK.read_text())

    selected.to_csv(SHEET_OUT, index=False)
    CODEBOOK_OUT.write_text(f"{CODEBOOK_TITLE}\n\n{definition}")
    print(f"Coder 2 sheet: {len(selected)} rows -> {SHEET_OUT}")
    print(f"Coder 2 codebook -> {CODEBOOK_OUT}")


if __name__ == "__main__":
    main()
