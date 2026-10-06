"""Compute the RQ2 sample size for estimating a proportion.

The population size N is the number of eligible workflows written by
script 20 (results/20_rq2_pilot_sample/eligibility.csv, status eligible).

Formula (proportion, normal approximation, finite population correction):
    n0 = z^2 * p * (1 - p) / e^2
    n  = n0 / (1 + (n0 - 1) / N)
with z the two-sided normal quantile for the confidence level, p the
expected proportion and e the margin of error. The required size is n
rounded up.

The confidence level, e and p are read from config/settings.yaml
(rq2.sample_size). The values used are 95% (z = 1.959964), e = 0.05 and
p = 0.5, the most conservative value since p * (1 - p) is largest at 0.5.

Writes to results/27_rq2_sample_size/:
- sample_size.csv: N, parameters, n0, n without rounding and n rounded up;
- provenance.json: SHA-256 of eligibility.csv and of the output.
"""

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist

import yaml

ELIGIBILITY = Path("results/20_rq2_pilot_sample/eligibility.csv")
OUTPUT_DIR = Path("results/27_rq2_sample_size")


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    with open("config/settings.yaml") as f:
        params = yaml.safe_load(f)["rq2"]["sample_size"]
    confidence, margin, p = params["confidence"], params["margin"], params["p"]

    with open(ELIGIBILITY, newline="") as f:
        population = int(next(r["workflows"] for r in csv.DictReader(f) if r["status"] == "eligible"))

    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    n0 = z ** 2 * p * (1 - p) / margin ** 2
    n = n0 / (1 + (n0 - 1) / population)
    required = math.ceil(n)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "sample_size.csv"
    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["population", "confidence", "z", "margin", "p", "n0", "n", "n_rounded_up"])
        writer.writerow([population, confidence, z, margin, p, n0, n, required])

    provenance = {
        "eligibility_csv": str(ELIGIBILITY),
        "eligibility_csv_sha256": sha256_of(ELIGIBILITY),
        "outputs_sha256": {out.name: sha256_of(out)},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"N = {population}; n0 = {n0:.2f}; n = {n:.2f}; required = {required}")


if __name__ == "__main__":
    main()
