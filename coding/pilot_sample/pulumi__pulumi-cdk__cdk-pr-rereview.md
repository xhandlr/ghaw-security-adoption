
# Internal PR Re-Review (Slash Command)

This workflow runs when a maintainer posts `/review-again` as the first token in a PR comment or review comment.

Review context text: `${{ needs.activation.outputs.text }}`

This workflow imports `pulumi-labs/gh-aw-internal/.github/snippets/code-review.md@main` for the baseline review rubric.

## Trust Model

- This workflow is slash-command triggered and restricted to PR comment/review-comment events.
- `tools.github.lockdown: false` is set to avoid requiring a custom GitHub MCP token.
- If the command was not issued in PR context, call `noop` and stop.

## Workflow-Specific Rules

- Determine the target PR number from the command event context.
- Use that PR number for all review operations in this run.
- Use `create-pull-request-review-comment` for actionable inline findings on changed lines.
- Submit exactly one final review with `submit-pull-request-review`:
  - `REQUEST_CHANGES` when at least one blocking issue exists.
  - `APPROVE` otherwise, including when only non-blocking observations exist.
  - Do not submit `COMMENT` as the final review state.
- If required PR context is missing, call `noop`.

Constraints:
- Post no more than 12 inline comments.
- Do not post free-form issue comments outside review safe outputs.
