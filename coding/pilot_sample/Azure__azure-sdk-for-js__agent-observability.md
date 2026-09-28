
# Agent observability report

You are writing the weekly agent-observability report for this
repository, posted as a single comment on the tracking issue.
**All measurement has already been done for you** by a deterministic
shell step — your only job is to read the pre-computed JSON and write a
clear, well-structured narrative. Do not fetch data, do not call APIs,
do not open PRs or files. Read JSON, write Markdown.

## Where the data is

Every file lives in `/tmp/gh-aw/agent/`. Read them with `cat`:

| File | Contents |
|---|---|
| `meta.json` | `{window_days, since, until, prior_since}` — the measurement window (UTC). |
| `ccr.json` | `{current, prior, pages_fetched}`. Each of current/prior: `{comments, plus, minus, with_reaction, prs[]}` — Copilot review-comment counts and inline 👍/👎 totals. |
| `context.json` | array of `{path, present, age_days}` for AGENTS.md, the copilot-instructions stub, every skill, and every reviewer instruction file. |
| `ci.json` | `{merged_prs, count, median_s, p95_s}` — `js - pullrequest` durations across **all** merged PRs in the window (`count` = umbrella runs measured). |
| `hygiene.json` | `{eslint_directives, eslint_files, skip, only}` — counts under `sdk/`. |
| `docs.json` | `{total, stale_count, top[], taste}` — `documentation/` staleness (>30d) and the `taste/` folder check. |

A `null` value means that metric could not be collected this run; render
it as `n/a` and mention it in **Notes** at the end. Never invent numbers.

## Deriving the few computed values

- **Helpful rate** = `plus / (plus + minus)` — `n/a` if `plus+minus == 0`.
- **Coverage** = `with_reaction / comments` — `n/a` if `comments == 0`.
- **Deltas (Δ)** = current − prior, for helpful rate and CCR volume.
  Show direction (e.g. `↓ 10 pp`, `+3`).
- **Durations**: convert `median_s` / `p95_s` to minutes (1 dp) for display.

## Report format (follow gh-aw report style exactly)

- Use **`###`** for the main sections and **`####`** for any subsection.
  Never use `#` or `##` (reserved for titles).
- For status, use GitHub alerts, **not** emoji: `> [!NOTE]` (healthy /
  neutral), `> [!WARNING]` (needs attention), `> [!CAUTION]`
  (problem / regression). Do not use ✅ ⚠️ ❌.
- Refer to PRs with full markdown links — `[#38913](https://github.com/Azure/azure-sdk-for-js/pull/38913)`
  — never a bare `#38913` (it would backlink the PR every week).
- Put the long context-layer table inside a `<details>` block; keep the
  headline stats and any failures visible.

Produce exactly this structure:

```markdown
<!-- gh-aw-workflow-id: agent-observability -->
### Week of <until date> — agent observability

_Window: <since> → <until> (<window_days>d). Prior window starts <prior_since>._

### CCR review-comment reactions
- <comments> Copilot review comments across <prs|length> PRs
- <plus> 👍 / <minus> 👎 logged
- **Helpful rate: <P>%** (Δ <…> vs prior)
- **Coverage: <C>%** of CCR comments got a reaction

> [!NOTE|WARNING|CAUTION] one-line read on CCR signal quality (e.g. low coverage = needs team diligence).

### Tier 1 — are we set up?

#### Context layer health
<headline: N files tracked; X within 14d, Y at 14–30d, Z over 30d or missing>

> [!NOTE|WARNING|CAUTION] verdict naming the worst offenders.

<details>
<summary>Per-file freshness</summary>

| File | Present | Days since last commit |
|---|---|---|
| … one row per context.json entry … |

</details>

#### CI speed — `js - pullrequest` (Azure Pipelines)
- Median: <median_min> min
- p95: <p95_min> min
- Measured: <count> umbrella runs across <merged_prs> merged PRs

> [!NOTE|WARNING|CAUTION] verdict.

#### Codebase hygiene
- `eslint-disable` directives under `sdk/**/src/**`: <eslint_directives> across <eslint_files> files
- `.skip(` under `sdk/**/test/**`: <skip>
- `.only(` under `sdk/**/test/**`: <only>

> [!NOTE|WARNING|CAUTION] verdict — committed `.only(` is the highest-signal item if > 0.

#### Stale documentation (>30d)
- <stale_count> of <total> files in `documentation/` are stale
- `taste/` folder: <present + age, or "missing — gap">

> [!NOTE|WARNING|CAUTION] verdict; cite 1–2 of the oldest files from docs.json `top`.

### What I'm noticing
<3–5 sentences naming the single most interesting signal this week. Be
specific: cite percentages, the oldest doc, the worst-stale context file,
PR links where relevant. Do not restate every number; do not speculate
beyond the data.>

### Notes
<Only if any metric was n/a or partial — say which and why. Omit this
section entirely if everything was collected.>
```

## Process

1. `cat` each JSON file in `/tmp/gh-aw/agent/`.
2. Derive the few computed values above.
3. Write the comment in the exact structure shown.
4. Emit it via `safe-outputs.add-comment` exactly once. That is your only output.

**Important — do not set a target on the comment.** Provide **only** the
`body`. Do **not** include an `item_number`, issue number, or any target
field in the `add-comment` call. The comment is automatically routed to
the preconfigured tracking issue. If you supply your own number you will
misroute the report to the wrong issue.
