"""Extract frontmatter field names mentioned in the Security Architecture page.

Downloads the page's source (.mdx) from github/gh-aw at the pinned commit
and extracts candidate field names from two formats only:
- YAML code blocks: every key, with its full path from the nesting. Keys
  inside list items are marked with [] (e.g. threat-detection.steps[].name).
  Plain list values (e.g. "- python") are not keys and are not extracted.
- Inline code (`...`) outside code blocks, including inside tables. If it
  contains ":", only the part before the first ":" is kept.

Mermaid blocks, other code blocks (bash, no language), the page's own
frontmatter, and the imported SVG diagram are excluded and listed in
excluded.csv.

Each mention is validated against results/03_schema_fields/fields.csv:
1. exact match with a field path -> valid (exact)
2. else, match where a * segment in fields.csv stands for any concrete key:
   one path -> valid (wildcard); several -> ambiguous
3. else, field paths ending in "." + name: one -> valid (suffix);
   several -> ambiguous; none -> discarded
Inline mentions that do not look like a field name go to not_name_like.csv.
"""

import csv
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import yaml

FIELDS_CSV = Path("results/03_schema_fields/fields.csv")
OUTPUT_DIR = Path("results/06_arch_doc_fields")

FENCE = re.compile(r"^\s*```(\S*)")
INLINE = re.compile(r"(`+)(.+?)\1")
NAME_LIKE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-\[\]*]*$")
SVG_IMPORT = re.compile(r"^import\s+\w+\s+from\s+['\"](.+\.svg)['\"]")


def load_settings():
    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)


def download(repo, path, commit, raw_dir):
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    request = urllib.request.Request(url, headers={"User-Agent": "ghaw-security-adoption"})
    with urllib.request.urlopen(request) as response:
        content = response.read()
    raw_dir.mkdir(parents=True, exist_ok=True)
    local_path = raw_dir / Path(path).name
    local_path.write_bytes(content)
    return local_path, url


def split_page(lines):
    """Return (yaml_blocks, prose_lines, excluded).

    yaml_blocks: list of (start_line, text) with 1-based line of the first
    content line. prose_lines: list of (line_number, text) outside code
    blocks and outside the page frontmatter.
    """
    yaml_blocks = []
    prose = []
    excluded = []
    i = 0

    if lines and lines[0].strip() == "---":
        end = next(j for j in range(1, len(lines)) if lines[j].strip() == "---")
        excluded.append(("mdx_frontmatter", 1, end + 1))
        i = end + 1

    while i < len(lines):
        match = FENCE.match(lines[i])
        if not match:
            prose.append((i + 1, lines[i]))
            svg = SVG_IMPORT.match(lines[i])
            if svg:
                excluded.append((f"svg:{svg.group(1)}", i + 1, i + 1))
            i += 1
            continue

        language = match.group(1).lower()
        start = i
        i += 1
        while i < len(lines) and not FENCE.match(lines[i]):
            i += 1
        body = "\n".join(lines[start + 1:i])
        if language == "yaml":
            yaml_blocks.append((start + 2, body))
        else:
            excluded.append((language or "no_language", start + 1, i + 1))
        i += 1

    return yaml_blocks, prose, excluded


def yaml_mentions(block_start, text, lines):
    """Every key in a YAML block, with full path and 1-based page line."""
    mentions = []
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    pending = [("", root)]
    while pending:
        prefix, node = pending.pop()
        if isinstance(node, yaml.MappingNode):
            for key_node, value_node in node.value:
                path = key_node.value if prefix == "" else prefix + "." + key_node.value
                line = block_start + key_node.start_mark.line
                mentions.append((path, "yaml", line, lines[line - 1].strip()))
                pending.append((path, value_node))
        elif isinstance(node, yaml.SequenceNode):
            for item in node.value:
                pending.append((prefix + "[]", item))
    return mentions


def inline_mentions(prose, table_lines):
    """Inline code spans outside code blocks. Returns (candidates, not_name_like)."""
    candidates = []
    not_name_like = []
    for line_number, text in prose:
        source = "inline_table" if line_number in table_lines else "inline"
        for match in INLINE.finditer(text):
            content = match.group(2).strip()
            name = content.split(":", 1)[0].strip()
            if NAME_LIKE.match(name):
                candidates.append((name, source, line_number, text.strip()))
            else:
                not_name_like.append((content, source, line_number, text.strip()))
    return candidates, not_name_like


def segments_match(pattern_path, name):
    pattern = pattern_path.split(".")
    concrete = name.split(".")
    if len(pattern) != len(concrete):
        return False
    for p, c in zip(pattern, concrete):
        if p == c:
            continue
        if p == "*" and not c.endswith("[]"):
            continue
        if p == "*[]" and c.endswith("[]"):
            continue
        return False
    return True


def validate(name, field_paths, wildcard_paths):
    """Return (category, match_type, matches)."""
    if name in field_paths:
        return "valid", "exact", [name]
    wildcard = sorted(p for p in wildcard_paths if segments_match(p, name))
    if len(wildcard) == 1:
        return "valid", "wildcard", wildcard
    if len(wildcard) > 1:
        return "ambiguous", "wildcard", wildcard
    suffix = sorted(p for p in field_paths if p.endswith("." + name))
    if len(suffix) == 1:
        return "valid", "suffix", suffix
    if len(suffix) > 1:
        return "ambiguous", "suffix", suffix
    return "discarded", "", []


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    settings = load_settings()
    schema_cfg = settings["gh_aw_schema"]
    doc_path = settings["gh_aw_docs"]["architecture_path"]
    raw_dir = Path(settings["paths"]["raw_dir"])

    local_path, url = download(schema_cfg["repo"], doc_path, schema_cfg["commit"], raw_dir)
    lines = local_path.read_text().splitlines()

    with open(FIELDS_CSV) as f:
        field_paths = {r["field_path"] for r in csv.DictReader(f)}
    wildcard_paths = {p for p in field_paths if "*" in p.split(".") or "*[]" in p.split(".")}

    yaml_blocks, prose, excluded = split_page(lines)
    table_lines = {n for n, text in prose if text.lstrip().startswith("|")}

    mentions = []
    yaml_failures = []
    for block_start, text in yaml_blocks:
        try:
            mentions.extend(yaml_mentions(block_start, text, lines))
        except yaml.YAMLError as error:
            yaml_failures.append((block_start, str(error).replace("\n", " ")))
    inline, not_name_like = inline_mentions(prose, table_lines)
    mentions.extend(inline)
    mentions.sort(key=lambda m: (m[2], m[0]))

    valid, ambiguous, discarded = [], [], []
    for name, source, line, phrase in mentions:
        category, match_type, matches = validate(name, field_paths, wildcard_paths)
        if category == "valid":
            valid.append([name, matches[0], match_type, source, line, phrase])
        elif category == "ambiguous":
            ambiguous.append([name, match_type, source, line, phrase, len(matches), json.dumps(matches)])
        else:
            discarded.append([name, source, line, phrase])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "valid.csv",
              ["name", "matched_path", "match_type", "source_format", "line", "phrase"], valid)
    write_csv(OUTPUT_DIR / "ambiguous.csv",
              ["name", "match_type", "source_format", "line", "phrase", "n_matches", "matches"], ambiguous)
    write_csv(OUTPUT_DIR / "discarded.csv", ["name", "source_format", "line", "phrase"], discarded)
    write_csv(OUTPUT_DIR / "not_name_like.csv", ["content", "source_format", "line", "phrase"],
              [list(r) for r in not_name_like])
    write_csv(OUTPUT_DIR / "excluded.csv", ["kind", "start_line", "end_line"], excluded)
    write_csv(OUTPUT_DIR / "yaml_parse_failures.csv", ["block_start_line", "error"], yaml_failures)

    summary = [
        ["valid", len(valid), len({r[0] for r in valid})],
        ["ambiguous", len(ambiguous), len({r[0] for r in ambiguous})],
        ["discarded", len(discarded), len({r[0] for r in discarded})],
        ["not_name_like", len(not_name_like), len({r[0] for r in not_name_like})],
    ]
    write_csv(OUTPUT_DIR / "summary.csv", ["category", "mentions", "distinct_names"], summary)

    provenance = {
        "repo": schema_cfg["repo"],
        "commit": schema_cfg["commit"],
        "doc_path": doc_path,
        "url": url,
        "doc_sha256": sha256_of(local_path),
        "fields_csv": str(FIELDS_CSV),
        "fields_csv_sha256": sha256_of(FIELDS_CSV),
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    for category, n_mentions, n_names in summary:
        print(f"{category}: {n_mentions} mentions, {n_names} distinct names")
    print(f"excluded blocks: {len(excluded)}, YAML parse failures: {len(yaml_failures)}")


if __name__ == "__main__":
    main()
