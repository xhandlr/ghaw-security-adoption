"""Extract fixed evidence columns from the lock file of each workflow.

One row per workflow (latest snapshot, highest rank, chosen before joining
the lock). Only extracts; it does not read the frontmatter, classify, or
compare against coding/rq1_codebook.yaml (that is script 08).

Everything about the agent is read only inside jobs.agent of the parsed
lock, so the threat-detection job's firewall and tools are never mixed in.
Comment lines inside run scripts (e.g. "# --allow-tool shell(cat)") are
ignored.

When a value cannot be extracted, its cell is left empty and a *_status
column says why. No row is dropped.
"""

import csv
import hashlib
import json
import re
import shlex
from pathlib import Path

import pandas as pd
import yaml

DATA_DIR = Path("data/raw/data")
OUTPUT_DIR = Path("results/07_lock_evidence")
TABLES = ["source_markdown_file_snapshot", "source_markdown_file_version",
          "lock_file_snapshot", "repository"]

METADATA = re.compile(r"^#\s*gh-aw-metadata:\s*(\{.*\})\s*$", re.MULTILINE)
DECLARED = re.compile(r"GH_AW_INFO_ALLOWED_DOMAINS:\s*'([^']*)'")
AWF = re.compile(r"\bawf\b")
AWF_JSON = re.compile(r'(\\?)"allowDomains\\?"\s*:\s*\[([^\]]*)\]')
AWF_FLAG = re.compile(r"--allow-domains[ =]+['\"]?([^\s'\"]+)")
COPILOT_ALL = re.compile(r"--allow-all-tools\b")
COPILOT_TOOL = re.compile(r"--allow-tool\b")
CLAUDE_TOOLS = re.compile(r"--allowed-tools\b")


def load_settings():
    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def latest_rows():
    """Latest version of each workflow, then its lock (left join)."""
    snapshots = pd.read_parquet(DATA_DIR / "source_markdown_file_snapshot.parquet")
    versions = pd.read_parquet(DATA_DIR / "source_markdown_file_version.parquet")
    locks = pd.read_parquet(DATA_DIR / "lock_file_snapshot.parquet")
    repos = pd.read_parquet(DATA_DIR / "repository.parquet")

    latest = versions.loc[versions.groupby("source_markdown_file_history_id")["rank"].idxmax()]
    rows = (latest
            .merge(snapshots[["source_markdown_file_snapshot_id", "repository_id", "path"]],
                   on="source_markdown_file_snapshot_id")
            .merge(repos[["repository_id", "repo_full_name"]], on="repository_id", how="left")
            .merge(locks[["source_markdown_file_version_id", "content"]].rename(columns={"content": "lock"}),
                   on="source_markdown_file_version_id", how="left"))
    return rows.sort_values("source_markdown_file_history_id")


def agent_run_text(lock_doc):
    """All run scripts of jobs.agent, without comment lines."""
    steps = ((lock_doc.get("jobs") or {}).get("agent") or {}).get("steps") or []
    lines = []
    for step in steps:
        run = step.get("run") if isinstance(step, dict) else None
        if isinstance(run, str):
            lines.extend(l for l in run.splitlines() if not l.lstrip().startswith("#"))
    return "\n".join(lines)


def extract_metadata(lock):
    match = METADATA.search(lock)
    if not match:
        return {"metadata_status": "no_metadata"}
    try:
        meta = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {"metadata_status": "unrecognized_format"}
    return {
        "compiler_version": meta.get("compiler_version", ""),
        "agent_id": meta.get("agent_id", ""),
        "strict_lock": json.dumps(meta["strict"]) if "strict" in meta else "",
        "metadata_status": "ok",
    }


def extract_declared(lock):
    values = set(DECLARED.findall(lock))
    if not values:
        return {"declared_domains_status": "no_line"}
    if len(values) > 1:
        return {"declared_domains_status": "multiple_values"}
    try:
        domains = json.loads(values.pop())
    except json.JSONDecodeError:
        return {"declared_domains_status": "unrecognized_format"}
    return {"declared_domains": json.dumps(domains), "declared_domains_status": "ok"}


def extract_firewall(run_text):
    if not AWF.search(run_text):
        return {"firewall_status": "no_firewall"}
    domains, formats = set(), set()
    for escaped, body in AWF_JSON.findall(run_text):
        formats.add("awf_config_json_escaped" if escaped else "awf_config_json")
        domains |= {d.strip().strip('\\"') for d in body.split(",") if d.strip()}
    for body in AWF_FLAG.findall(run_text):
        formats.add("allow_domains_flag")
        domains |= {d for d in body.split(",") if d}
    if not formats:
        return {"firewall_status": "unrecognized_format"}
    return {
        "firewall_domains": json.dumps(sorted(domains)),
        "firewall_domains_n": len(domains),
        "firewall_format": "+".join(sorted(formats)),
        "firewall_status": "ok",
    }


def flag_values(run_text, flag):
    """Values passed to a command-line flag, with shell quoting undone.

    The agent command is usually nested inside bash -c '...', so a token
    that itself contains the flag is split again. Raises ValueError when
    the quoting cannot be parsed.
    """
    values = []
    pending = [line for line in run_text.replace("\\\n", " ").splitlines() if flag in line]
    while pending:
        tokens = shlex.split(pending.pop())
        for i, token in enumerate(tokens):
            if token == flag and i + 1 < len(tokens):
                values.append(tokens[i + 1])
            elif flag in token and token != flag:
                pending.append(token)
    return values


def split_top_level(text):
    """Split on commas that are not inside parentheses."""
    items, depth, current = [], 0, ""
    for char in text:
        if char == "," and depth == 0:
            items.append(current)
            current = ""
            continue
        depth += (char == "(") - (char == ")")
        current += char
    items.append(current)
    return [item.strip() for item in items if item.strip()]


def tool_commands(items, tool):
    """(unrestricted, commands) from entries like tool or tool(command)."""
    unrestricted = tool in items
    commands = sorted({item[len(tool) + 1:-1] for item in items
                       if item.startswith(tool + "(") and item.endswith(")")})
    return unrestricted, commands


def extract_bash(run_text):
    try:
        if COPILOT_ALL.search(run_text):
            return {"bash_mode": "all_tools", "bash_commands": "[]", "bash_status": "ok"}
        if COPILOT_TOOL.search(run_text):
            unrestricted, commands = tool_commands(flag_values(run_text, "--allow-tool"), "shell")
        elif CLAUDE_TOOLS.search(run_text):
            items = [item for value in flag_values(run_text, "--allowed-tools")
                     for item in split_top_level(value)]
            unrestricted, commands = tool_commands(items, "Bash")
        else:
            return {"bash_status": "unrecognized_format"}
    except ValueError:
        return {"bash_status": "unparseable_quoting"}
    mode = "shell_unrestricted" if unrestricted else ("list" if commands else "no_shell")
    return {"bash_mode": mode, "bash_commands": json.dumps(commands), "bash_status": "ok"}


def extract(row):
    out = {
        "history_id": row["source_markdown_file_history_id"],
        "snapshot_id": row["source_markdown_file_snapshot_id"],
        "version_id": row["source_markdown_file_version_id"],
        "repo_full_name": row["repo_full_name"],
        "path": row["path"],
        "committed_at": row["committed_at"],
    }
    lock = row["lock"]
    if not isinstance(lock, str):
        status = "no_lock"
    else:
        out.update(extract_metadata(lock))
        out.update(extract_declared(lock))
        try:
            lock_doc = yaml.load(lock, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
            status = "ok" if isinstance(lock_doc, dict) else "invalid_yaml"
        except yaml.YAMLError:
            status = "invalid_yaml"
        if status == "ok" and "agent" not in (lock_doc.get("jobs") or {}):
            status = "no_agent_job"
    out["lock_status"] = status

    if status != "ok":
        for column in ["metadata_status", "declared_domains_status"]:
            out.setdefault(column, status)
        for column in ["agent_permissions_status", "firewall_status", "bash_status"]:
            out[column] = status
        return out

    agent = lock_doc["jobs"]["agent"]
    if "permissions" in agent:
        out["agent_permissions"] = json.dumps(agent["permissions"], sort_keys=True)
        out["agent_permissions_status"] = "ok"
    else:
        out["agent_permissions_status"] = "no_key"

    run_text = agent_run_text(lock_doc)
    out.update(extract_firewall(run_text))
    out.update(extract_bash(run_text))
    return out


COLUMNS = [
    "history_id", "snapshot_id", "version_id", "repo_full_name", "path", "committed_at",
    "lock_status",
    "compiler_version", "agent_id", "strict_lock", "metadata_status",
    "agent_permissions", "agent_permissions_status",
    "declared_domains", "declared_domains_status",
    "firewall_domains", "firewall_domains_n", "firewall_format", "firewall_status",
    "bash_mode", "bash_commands", "bash_status",
]
STATUS_COLUMNS = [c for c in COLUMNS if c.endswith("_status")]


def main():
    settings = load_settings()
    rows = [extract(row) for _, row in latest_rows().iterrows()]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = OUTPUT_DIR / "lock_evidence.csv"
    with open(evidence_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in COLUMNS})

    summary = []
    for column in STATUS_COLUMNS:
        counts = {}
        for row in rows:
            counts[row[column]] = counts.get(row[column], 0) + 1
        summary.extend([column, status, n] for status, n in sorted(counts.items()))
    with open(OUTPUT_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["column", "status", "rows"])
        writer.writerows(summary)

    provenance = {
        "dataset_repo_id": settings["dataset"]["repo_id"],
        "dataset_revision": settings["dataset"]["revision"],
        "snapshot_selection": settings["snapshot_selection"]["criterion"],
        "input_sha256": {t: sha256_of(DATA_DIR / f"{t}.parquet") for t in TABLES},
        "lock_evidence_csv_sha256": sha256_of(evidence_path),
        "rows": len(rows),
    }
    (OUTPUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    print(f"Rows: {len(rows)}")
    for column, status, n in summary:
        print(f"{column}: {status} = {n}")


if __name__ == "__main__":
    main()
