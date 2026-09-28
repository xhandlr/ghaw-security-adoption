
# Documentation Link Checker

A link checker (`lychee`) has already validated every URL in `**/*.md` from a regular GitHub Actions step **outside** the AI sandbox — so the network is no longer your problem. Your job is to read its report and propose only high-confidence fixes.

The report is at `/tmp/gh-aw/lychee-report.json`. It is the source of truth for which links are broken; do not re-check URLs yourself.

## Phase 1: Read the report

1. Load `/tmp/gh-aw/lychee-report.json`. The schema is roughly:
   ```json
   { "success_map": { "<file>": [ { "url": "...", "status": { ... } } ] },
     "error_map":   { "<file>": [ { "url": "...", "status": { ... } } ] } }
   ```
2. Use `cat` and `jq` to extract every entry in `error_map` (these are the broken links).
3. Print a quick count by status code so the run log is useful even if nothing else is.

## Phase 2: Triage into three buckets

For each broken link, decide which bucket it belongs in.

- **Auto-fix:** You can name a replacement URL with high confidence based on documentation knowledge — for example, a Microsoft Learn page that moved under a new path, or a GitHub repo that was renamed. The replacement must be a well-known canonical URL. **Do not invent URLs.** If you are guessing, it belongs in "Needs review".
- **Needs review:** The link is broken but the right replacement isn't obvious, or multiple candidates exist, and the host is not on the rate-limiting allowlist below.
- **Skip:** Transient errors, or links inside `node_modules/`, build outputs, or vendored content. **Also skip rate-limited or timed-out responses from hosts that are known to block CI crawlers** (see below) — these are environmental, not broken links.

### Rate-limiting hosts (treat timeouts / 403 / 429 as Skip, not Needs review)

Several Microsoft and partner hosts actively block, throttle, or time out automated crawlers like the GitHub-hosted runner lychee uses. A failure from one of these hosts is almost never a real broken link — it's the host refusing the bot. Categorize them as **Skip** and do **not** file them under "Needs review" (filing them just churns a new issue every week for a link that's actually fine).

Treat the following as rate-limited unless you have other evidence the page is genuinely gone:

- `azure.microsoft.com/**/pricing/**` — Azure pricing pages aggressively block crawlers; the canonical pricing URLs are still cited verbatim by Microsoft Learn.
- `azure.microsoft.com/**/products/**` — same crawler-blocking behavior as pricing.
- `learn.microsoft.com/**` — occasional 403/429 under burst load; almost always recovers on the next run.
- `techcommunity.microsoft.com/**` — frequent 403 to non-browser user agents.
- `devblogs.microsoft.com/**` and `*.microsoft.com/en-us/legal/**` — same pattern.

Heuristic: if the lychee status is `Timeout`, `403`, or `429` **and** the host matches one of the patterns above, it goes in **Skip**. Only escalate to "Needs review" when the same URL has failed on multiple consecutive runs *and* you can't load it manually, or the host is not on this allowlist.

When you skip a link for this reason, mention it in the report's "Skipped" section with a one-line note like `azure.microsoft.com pricing — known CI rate-limiting, link verified canonical`. That keeps the audit trail honest.

## Phase 3: Execute

1. For **Auto-fix** items only, edit the markdown files to swap **only the URL**. Preserve link text, prose, indentation, and markdown formatting exactly. Never touch surrounding sentences.
2. Open a draft pull request via the `create-pull-request` safe output. The body must contain:
   - Total links scanned, total broken (from the lychee report)
   - **Auto-fixed** table: file, old URL → new URL, reason
   - **Needs review** table: file, URL, status code, your best guess (or "no clear replacement")
   - Skipped count
3. If you have **nothing** to auto-fix (zero high-confidence changes), call `create-issue` instead of opening an empty PR.
4. If the org blocks Actions-created PRs, `fallback-as-issue: true` converts the PR into an issue automatically — no extra work needed.

## Guardrails

- **URL swaps only.** Never modify prose, headings, code blocks, or formatting.
- **Never invent replacements.** If you can't cite the new canonical URL from documentation you actually know, the item belongs in "Needs review".
- **Never touch** `CONSTITUTION.md`, `.github/copilot-instructions.md`, or anything under `.github/aw/`.
- **Never alter** more than 20 files in a single PR. If you'd exceed that, group fixes by domain and only ship the most confident batch; flag the rest for review.
