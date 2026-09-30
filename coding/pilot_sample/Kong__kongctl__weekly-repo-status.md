
# Weekly Repo Status

Create an upbeat weekly status report for the repo as a GitHub Discussion.

**Important tool usage notes:**
- Use GitHub MCP tools for all GitHub reads when gathering repository activity.
- Use safe-output tools (`create_discussion`, `noop`) for all GitHub writes and
  completion signaling.
- Do NOT use `gh` CLI commands for GitHub API reads or writes because the CLI
  is not authenticated in this environment.

## What to include

- Recent repository activity (issues, PRs, discussions, releases, code changes)
- Progress tracking, goal reminders and highlights
- Project status and recommendations
- Actionable next steps for maintainers

## Style

- Be positive, encouraging, and helpful 🌟
- Use emojis lightly for engagement
- Keep it concise - adjust length based on actual activity

## Process

1. Gather recent activity from the repository
2. Study the repository, its issues and its pull requests
3. Create a new GitHub discussion with your findings and insights

## Finalization

Before finishing, emit exactly one safe output.

- Prefer `create_discussion` with the weekly report.
- If no meaningful report can be created, emit `noop` explaining why.
- If the discussion tool is unavailable or fails, emit `missing_tool` or `noop`
  so the workflow never finishes with no safe outputs.
