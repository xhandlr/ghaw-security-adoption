"""Prepare the RQ2 manual coding sheets. Does not code anything.

Writes coding/rq2_coding_coder1.csv: one row per body in coding/pilot_sample/, in
the random order fixed by script 20 (coding/pilot_sample_index.csv), with
empty coding columns. The line column refers to the line number inside
the body file in coding/pilot_sample/.

Writes coding/rq2_recoding_sample.csv: rows drawn at random (size and seed
in config/settings.yaml) for re-coding, in draw order, with identification
columns only, so the first coding is not visible.

Never overwrites either file if it already exists, so manual coding is
never lost by re-running this script.
"""

from pathlib import Path

import pandas as pd
import yaml

CODING_COLUMNS = ["tiene_defensa", "frase_textual", "linea", "categoria_provisional", "notas"]
ID_COLUMNS = ["orden", "archivo", "repositorio", "workflow"]


def main():
    with open("config/settings.yaml") as f:
        settings = yaml.safe_load(f)
    coding_dir = Path(settings["paths"]["coding_dir"])
    rq2 = settings["rq2"]

    coding_path = coding_dir / "rq2_coding_coder1.csv"
    recoding_path = coding_dir / "rq2_recoding_sample.csv"
    existing = [str(p) for p in (coding_path, recoding_path) if p.exists()]
    if existing:
        raise SystemExit(f"Refusing to overwrite existing file(s): {', '.join(existing)}")

    index = pd.read_csv(coding_dir / "pilot_sample_index.csv")
    missing = [f for f in index["filename"] if not (coding_dir / "pilot_sample" / f).exists()]
    if missing:
        raise SystemExit(f"Body files missing in pilot_sample/: {missing}")

    sheet = pd.DataFrame({
        "orden": range(1, len(index) + 1),
        "archivo": index["filename"],
        "repositorio": index["repo_full_name"],
        "workflow": index["path"],
    })
    for column in CODING_COLUMNS:
        sheet[column] = ""
    sheet.to_csv(coding_path, index=False)

    recoding = sheet[ID_COLUMNS].sample(n=rq2["recoding_sample_size"], random_state=rq2["recoding_seed"])
    recoding.to_csv(recoding_path, index=False)

    print(f"Coding sheet: {len(sheet)} rows -> {coding_path}")
    print(f"Recoding sample: {len(recoding)} rows (seed={rq2['recoding_seed']}) -> {recoding_path}")


if __name__ == "__main__":
    main()
