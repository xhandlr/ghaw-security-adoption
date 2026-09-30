"""RQ1 measurement: classify the demo fields of each workflow.

Applies coding/rq1_codebook.yaml to the latest snapshot of each workflow
(highest rank, same criterion as scripts 02 and 12). All values, decisions
and reasons come from the codebook; this script only knows how to compare
a value against each rule type listed in the codebook's tipos_de_regla.

Per workflow and field:
- not declared -> implicito
- declared -> rules are tried in the codebook's order (igual_al_default,
  then formas, then resto). The first match decides. Other rules that also
  match are listed in otras_reglas; if they lead to a different decision,
  the state is conflicto. A value no rule matches is sin_regla.

For modified values, the field's direccion section is applied as a second
layer: the first category that matches gives direccion and amplia; if none
matches, the direction resto rule does.

Workflows whose frontmatter cannot be read as a dict are excluded and
listed in excluded.csv.
"""

import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

CODEBOOK = Path("coding/rq1_codebook.yaml")
DATA_DIR = Path("data/raw/data")
OUTPUT_DIR = Path("results/14_rq1_measurement")
TABLES = ["source_markdown_file_snapshot", "source_markdown_file_version", "repository"]
EQUAL_STATE = "explicito_igual_default"
ADDED_COMMANDS_RULE = "bash_dir_agrega_y_quita"  # direction rule whose added commands are listed


def canonical(value):
    return json.dumps(value, sort_keys=True)


def as_set(items):
    return {canonical(item) for item in items}


def matches(rule, value):
    kind = rule["tipo"]
    if kind == "valor_exacto":
        return canonical(value) == canonical(rule["valor"])
    if kind == "lista_mismo_conjunto":
        return isinstance(value, list) and as_set(value) == as_set(rule["valor"])
    if kind == "lista_otro_conjunto":
        return isinstance(value, list) and as_set(value) != as_set(rule["valor"])
    if kind == "dict_clave_conjunto":
        return (isinstance(value, dict) and set(value) == {rule["clave"]}
                and isinstance(value[rule["clave"]], list)
                and as_set(value[rule["clave"]]) == as_set(rule["valor"]))
    if kind == "lista_contiene_alguno":
        return isinstance(value, list) and bool(as_set(value) & as_set(rule["valor"]))
    if kind == "lista_vs_conjunto":
        if not isinstance(value, list):
            return False
        items, reference = as_set(value), as_set(rule["valor"])
        if items & as_set(rule.get("excluye", [])):
            return False
        relation = rule["relacion"]
        if relation == "subconjunto":
            return items < reference
        if relation == "superconjunto":
            return items > reference
        if relation == "agrega_y_quita":
            return bool(items - reference) and bool(reference - items)
        raise ValueError(f"unknown relacion: {relation}")
    if kind == "dict_condiciones":
        return isinstance(value, dict) and all(condition_holds(c, value) for c in rule["condiciones"])
    if kind == "resto":
        return True
    raise ValueError(f"unknown rule type: {kind}")


def condition_holds(condition, value):
    """One condition of a dict_condiciones rule, as listed in tipos_de_regla."""
    (name, args), = condition.items()
    if name in ("alguna_clave_con_valor", "ninguna_clave_con_valor"):
        found = any(k not in args["excepto"] and canonical(v) == canonical(args["valor"])
                    for k, v in value.items())
        return found if name == "alguna_clave_con_valor" else not found
    if name in ("clave_con_valor", "clave_distinta_de"):
        equal = args["clave"] in value and canonical(value[args["clave"]]) == canonical(args["valor"])
        return equal if name == "clave_con_valor" else not equal
    if name == "clave_presente":
        return args["clave"] in value
    if name in ("lista_en_clave_contiene", "lista_en_clave_no_contiene"):
        items = value.get(args["clave"])
        if not isinstance(items, list):
            return False
        present = canonical(args["valor"]) in as_set(items)
        return present if name == "lista_en_clave_contiene" else not present
    if name == "lista_en_clave_no_vacia":
        items = value.get(args["clave"])
        return isinstance(items, list) and len(items) > 0
    if name == "otras_claves":
        return set(value) <= set(args["permitidas"])
    raise ValueError(f"unknown condition: {name}")


def load_codebook():
    codebook = yaml.safe_load(CODEBOOK.read_text())
    known = set(codebook["tipos_de_regla"])
    fields = {}
    for name, spec in codebook["campos"].items():
        rules = [(r, EQUAL_STATE) for r in spec["igual_al_default"]["valores"]]
        rules += [(r, r["decision"]) for r in spec.get("formas", [])]
        resto = spec.get("resto")
        direction = spec.get("direccion", {})
        categories = direction.get("categorias", [])
        direction_resto = direction.get("resto")
        checked = [r for r, _ in rules] + categories
        checked += [r for r in (resto, direction_resto) if r]
        for rule in checked:
            if rule["tipo"] not in known:
                raise ValueError(f"{name}: rule {rule['id']} has a type not in tipos_de_regla")
        fields[name] = (rules, resto, categories, direction_resto)
    return fields


def direction_of(value, categories, direction_resto):
    """(direccion, amplia, rule_id, other_rule_ids) for a modified value.

    The first category that matches decides; other matching categories are
    listed, and if any of them has a different direccion the result is
    conflicto. With no match, the direction resto rule applies.
    """
    hits = [rule for rule in categories if matches(rule, value)]
    if not hits:
        if direction_resto:
            return (direction_resto["direccion"], direction_resto.get("amplia", ""),
                    direction_resto["id"], [])
        return "", "", "", []
    first, others = hits[0], hits[1:]
    other_ids = [rule["id"] for rule in others]
    if any(rule["direccion"] != first["direccion"] for rule in others):
        return "conflicto", "", first["id"], other_ids
    return first["direccion"], first.get("amplia", ""), first["id"], other_ids


def classify(value, rules, resto):
    """(state, rule_id, other_rule_ids) for a declared value."""
    hits = [(rule, decision) for rule, decision in rules if matches(rule, value)]
    if not hits:
        if resto and matches(resto, value):
            return resto["decision"], resto["id"], []
        return "sin_regla", "", []
    (first, decision), others = hits[0], hits[1:]
    other_ids = [rule["id"] for rule, _ in others]
    if any(d != decision for _, d in others):
        return "conflicto", first["id"], other_ids
    return decision, first["id"], other_ids


def field_value(doc, name):
    current = doc
    for key in name.split("."):
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current


def frontmatter_loader():
    spec = importlib.util.spec_from_file_location("keys02", "scripts/02_list_frontmatter_keys.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FrontmatterLoader


def latest_snapshots():
    snapshots = pd.read_parquet(DATA_DIR / "source_markdown_file_snapshot.parquet")
    versions = pd.read_parquet(DATA_DIR / "source_markdown_file_version.parquet")
    repos = pd.read_parquet(DATA_DIR / "repository.parquet")
    latest = versions.loc[versions.groupby("source_markdown_file_history_id")["rank"].idxmax()]
    return (latest[["source_markdown_file_history_id", "source_markdown_file_snapshot_id"]]
            .merge(snapshots, on="source_markdown_file_snapshot_id")
            .merge(repos[["repository_id", "repo_full_name"]], on="repository_id", how="left")
            .sort_values("source_markdown_file_history_id"))


def parse(text, loader):
    try:
        doc = yaml.load(text, Loader=loader)
    except yaml.YAMLError as error:
        return None, f"yaml error: {str(error).splitlines()[0]}"
    if doc is None:
        return None, "empty frontmatter"
    if not isinstance(doc, dict):
        return None, f"not a dict: {type(doc).__name__}"
    return doc, ""


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    fields = load_codebook()
    loader = frontmatter_loader()

    measurement, excluded = [], []
    for _, row in latest_snapshots().iterrows():
        ids = [row["source_markdown_file_history_id"], row["source_markdown_file_snapshot_id"],
               row["repo_full_name"], row["path"]]
        doc, reason = parse(row["frontmatter"], loader)
        if doc is None:
            excluded.append(ids + [reason])
            continue
        for name, (rules, resto, categories, direction_resto) in fields.items():
            declared, value = field_value(doc, name)
            if declared:
                state, rule_id, others = classify(value, rules, resto)
                written = canonical(value)
            else:
                state, rule_id, others, written = "implicito", "", [], ""
            if state == "modificado":
                d_dir, d_amplia, d_rule, d_others = direction_of(value, categories, direction_resto)
                d_others = json.dumps(d_others)
            else:
                d_dir, d_amplia, d_rule, d_others = "", "", "", ""
            measurement.append(ids + [name, declared, written, state, rule_id, json.dumps(others),
                                      d_dir, d_amplia, d_rule, d_others])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    header = ["history_id", "snapshot_id", "repo_full_name", "path"]
    write_csv(OUTPUT_DIR / "measurement.csv",
              header + ["field", "declared", "value", "estado", "regla_id", "otras_reglas",
                        "direccion", "amplia", "direccion_regla_id", "direccion_otras_reglas"],
              measurement)
    write_csv(OUTPUT_DIR / "excluded.csv", header + ["reason"], excluded)

    states = Counter((m[4], m[7]) for m in measurement)
    write_csv(OUTPUT_DIR / "summary.csv", ["field", "estado", "workflows"],
              [[f, s, n] for (f, s), n in sorted(states.items())])

    for state_or_rule, filename in [("sin_regla", "sin_regla.csv"), ("resto", "resto.csv")]:
        if state_or_rule == "sin_regla":
            selected = [m for m in measurement if m[7] == "sin_regla"]
        else:
            resto_ids = {resto["id"] for _, resto, _, _ in fields.values() if resto}
            selected = [m for m in measurement if m[8] in resto_ids]
        counts = Counter((m[4], m[6]) for m in selected)
        write_csv(OUTPUT_DIR / filename, ["field", "value", "workflows"],
                  [[f, v, n] for (f, v), n in sorted(counts.items(), key=lambda x: (x[0][0], -x[1]))])

    modified = [m for m in measurement if m[7] == "modificado"]
    directions = Counter((m[4], m[10], m[11]) for m in modified)
    write_csv(OUTPUT_DIR / "direction_summary.csv", ["field", "direccion", "amplia", "workflows"],
              [[f, d, a, n] for (f, d, a), n in sorted(directions.items())])

    checks = []
    for name in fields:
        rows = [m for m in modified if m[4] == name]
        checks.append([name, len(rows),
                       sum(m[13] not in ("", "[]") for m in rows),
                       sum(m[10] == "conflicto" for m in rows)])
    write_csv(OUTPUT_DIR / "direction_overlaps.csv",
              ["field", "modificados", "superposiciones", "conflictos"], checks)

    direction_resto_ids ={r["id"] for _, _, _, r in fields.values() if r}
    write_csv(OUTPUT_DIR / "direction_resto.csv",
              header + ["field", "value", "direccion_regla_id"],
              [m[:4] + [m[4], m[6], m[12]] for m in modified if m[12] in direction_resto_ids])

    # Commands added by lists in ADDED_COMMANDS_RULE, outside the codebook's default list.
    default_commands = set(yaml.safe_load(CODEBOOK.read_text())["campos"]["tools.bash"]["default"])
    added = Counter(command for m in modified if m[12] == ADDED_COMMANDS_RULE
                    for command in set(json.loads(m[6])) - default_commands)
    write_csv(OUTPUT_DIR / "bash_added_commands.csv", ["command", "workflows"],
              sorted(added.items(), key=lambda x: (-x[1], x[0])))

    with open("config/settings.yaml") as f:
        dataset = yaml.safe_load(f)["dataset"]
    provenance = {
        "codebook": str(CODEBOOK),
        "codebook_sha256": sha256_of(CODEBOOK),
        "dataset_repo_id": dataset["repo_id"],
        "dataset_revision": dataset["revision"],
        "input_sha256": {t: sha256_of(DATA_DIR / f"{t}.parquet") for t in TABLES},
        "workflows_measured": len({m[0] for m in measurement}),
        "workflows_excluded": len(excluded),
        "outputs_sha256": {p.name: sha256_of(p) for p in sorted(OUTPUT_DIR.glob("*.csv"))},
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Measured: {provenance['workflows_measured']}, excluded: {len(excluded)}")
    for (field, state), n in sorted(states.items()):
        print(f"{field} {state}: {n}")


if __name__ == "__main__":
    main()
