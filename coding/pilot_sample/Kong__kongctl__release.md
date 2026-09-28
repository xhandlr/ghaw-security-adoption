
# Release Highlights Generator

Generate an engaging release highlights summary for **${{ github.repository }}**
release `${RELEASE_TAG}`.

**Release ID**: ${{ needs.release.outputs.release_id }}

## Data Available

All data is pre-fetched in `/tmp/gh-aw/release-data/`:
- `current_release.json` - Release metadata and existing generated notes
- `pull_requests.json` - PRs merged between `${PREV_RELEASE_TAG}` and
  `${RELEASE_TAG}`
- `compare.json` - Commit comparison between previous and current tags
- `issues.json` - Repository issues for optional cross-reference
- `CHANGELOG.md` - Changelog context (if present)
- `docs_files.txt` - Markdown documentation files in this repository

## Objective

Generate complete release notes that replace the existing release content,
so users can quickly understand what changed and why it matters.

**Important tool usage notes:**
- All required GitHub release, PR, issue, and compare data has already been
  pre-fetched into `/tmp/gh-aw/release-data/`.
- Use local shell commands only to inspect those pre-fetched files and relevant
  repository files.
- Do NOT use `gh` CLI commands or make additional GitHub API calls from the
  agent. The agent should operate only on the pre-fetched local data.
- Use the `update_release` safe-output tool exactly once for the final write.

The highlights should be:
- User-impact focused, not a raw changelog dump
- Concise and scannable in under one minute
- Accurate and linked (PRs/issues/docs) where useful

## Workflow

### 1. Load and Inspect Inputs

Use shell commands to inspect the pre-fetched files before writing any output.

### 2. Determine What Actually Matters to Users

Prioritize:
- New CLI capabilities, resources, flags, or behaviors
- Bug fixes that unblock common workflows
- Breaking or behavior-changing updates
- DX/documentation improvements that materially help users

De-prioritize or omit:
- Internal-only refactors with no user impact
- CI-only or maintenance-only noise unless significant

### 3. Categorize Changes

Use only relevant sections:
- `⚠️ Breaking Changes` (first when present)
- `✨ What's New`
- `🐛 Fixes & Improvements`
- `📚 Docs & DX`

When helpful, include short command examples in fenced `bash` blocks.

### 4. Build Commit Reference List

Use `compare.json` to generate a complete commit reference section with direct
links, sorted in this order:
1. Features
2. Fixes
3. Other changes

```bash
cat /tmp/gh-aw/release-data/compare.json | jq -r '
  def subject: ((.commit.message // "") | split("\n")[0]);
  def category:
    (subject | ascii_downcase) as $s |
    if ($s | test("^(feat|feature)(\\(|:|\\b)")) or ($s | test("^(add|introduce)\\b")) then "feature"
    elif ($s | test("^(fix|bugfix|hotfix)(\\(|:|\\b)")) or ($s | test("\\bfix(es|ed)?\\b")) then "fix"
    else "other" end;
  [(.commits // [])[] | {
    sha,
    html_url,
    date: (.commit.author.date // ""),
    subject: subject,
    category: category
  }]
  | sort_by(.date)
  | reverse
  | ([.[] | select(.category == "feature")]
     + [.[] | select(.category == "fix")]
     + [.[] | select(.category == "other")])
  | .[]
  | "- [`\(.sha[0:7])`](\(.html_url)) \(.subject)"'
```

Requirements for this section:
- Include all commits from `compare.json` when present.
- Keep each line to one commit with a clickable short SHA link.
- Use only the first line of the commit message.
- Order the final list by category first: Features, then Fixes, then Other.
- If there are no commits, omit this section.

### 5. Community Acknowledgements

If contributor PRs are present, include a short thanks section with links.
Only include this section when there is meaningful community activity.

### 6. First-Release or Low-Change Cases

If this appears to be the first release or has very small surface area,
produce a short, accurate summary rather than forcing all sections.

## Output Requirements

You MUST call the `safeoutputs/update_release` MCP tool exactly once:
- `tag`: `${RELEASE_TAG}`
- `operation`: `replace`
- `body`: full markdown for the complete release notes (highlights + all commit references)
- Mark the release as the latest

The body should begin with:

```markdown
## <img src="https://raw.githubusercontent.com/Kong/kongctl/main/brand/logo/light/Kong-Logomark.svg#gh-light-mode-only" alt="Kong logo" width="20" /> <img src="https://raw.githubusercontent.com/Kong/kongctl/main/brand/logo/dark/Kong-Logomark.svg#gh-dark-mode-only" alt="Kong logo" width="20" /> kongctl Release Highlights
```

The `<img>` tags in the opening heading are intentional and must be preserved so
the theme-aware Kong logo renders in the GitHub release body. Avoid other raw
HTML unless it is required for GitHub-flavored Markdown rendering.

When commits are available, include this section near the end:

```markdown
### 🔗 Commit References
#### Features
- [`abc1234`](https://github.com/OWNER/REPO/commit/abc1234...) Add support for X

#### Fixes
- [`def5678`](https://github.com/OWNER/REPO/commit/def5678...) Fix Y in Z flow

#### Other Changes
- [`0123abc`](https://github.com/OWNER/REPO/commit/0123abc...) Chore/doc update
```

End with a divider, for example:

```markdown
---
```

When `PREV_RELEASE_TAG` is present, you MUST also include this exact style line
at the end of the generated highlights:

```markdown
Full Changelog: https://github.com/${{ github.repository }}/compare/${PREV_RELEASE_TAG}...${RELEASE_TAG}
```

When there is no previous release/tag (first release), include:

```markdown
Full Changelog: Initial release
```

If there are no meaningful user-facing changes, still replace with a concise
maintenance summary instead of skipping the update.
