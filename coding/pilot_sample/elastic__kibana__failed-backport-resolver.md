
# Failed Backport Resolver

Resolve failed automatic backports for the pull request identified by the injected `GH_AW_GITHUB_EVENT_ISSUE_NUMBER` value for PR comments, or `GH_AW_GITHUB_EVENT_PULL_REQUEST_NUMBER` when present. Use the injected `GH_AW_GITHUB_REPOSITORY` and `GH_AW_GITHUB_RUN_ID` values to construct the workflow run URL as `https://github.com/<GH_AW_GITHUB_REPOSITORY>/actions/runs/<GH_AW_GITHUB_RUN_ID>`.

## Parent Workflow

1. Read `/tmp/gh-aw/agent/pr-metadata.json` and `/tmp/gh-aw/agent/pr-issue-comments.json`. Use those prefetched files as the source of truth for PR metadata and comments, and capture `author.login` from `pr-metadata.json` as the source PR author login. Also read `crossReferencedPulls` from `pr-metadata.json`; it contains compact metadata for pull requests that GitHub cross-referenced from the source PR timeline.
2. From `pr-issue-comments.json`, use the latest `kibanamachine` comment whose body contains `Some backports could not be created` or `All backports failed`.
3. Parse that comment for target branches that failed. A failed branch is any branch row whose result says `Backport failed because of merge conflicts`, or an equivalent failure row under the matching failure heading.
4. Read `versions.json` and build the active branch allowlist from `versions[].branch`. Drop any parsed failed branch that is not in that allowlist, and mention the skipped branch in the final comment.
5. Read `.backportrc.json` for non-branch PR conventions only. Ignore branch lists in `.backportrc.json`; active branches come from `versions.json`.
6. Before starting a target branch, inspect only source PR-local data for an existing backport: `pr-metadata.json`, `crossReferencedPulls`, `pr-issue-comments.json`, and any PRs directly linked from those comments or the source PR body. Treat an open PR as existing only when it has the `backport` label and targets the same branch. Do not perform broad repository PR searches.
7. If every remaining failed branch already has an existing open backport PR, call `add_comment` exactly once with the final comment table, use status `existing` for those branches, and do not launch branch workers.
8. Create the shared parent directory for worker worktrees by running `mkdir -p /tmp/gh-aw-worktrees`.
9. For each remaining target branch, launch one parallel task with the `backport-branch-worker` sub-agent defined in `.claude/agents/backport-branch-worker.md`. Pass only the source PR number, source PR title, source PR URL, source PR author login, source branch, source merge commit SHA, target branch, repository from `GH_AW_GITHUB_REPOSITORY`, and the workflow run URL built from `GH_AW_GITHUB_REPOSITORY` and `GH_AW_GITHUB_RUN_ID`.
   - Do not rewrite or expand the worker instructions when launching the task. Do not add branch naming, PR body, safe-output tool, git push, draft PR, fallback, retry, test, or validation instructions beyond the input values listed above.
   - Branch workers are the only tasks that may call `create_pull_request`, and only for a branch whose worker result is `created`.
   - The parent workflow must never call `create_pull_request` for a branch, including to retry, repair, or replace a worker output.
10. Wait for every branch task to finish. Do not stop after the first failure.
11. Treat each branch worker's returned structured result as the source of truth for that branch. Do not reinterpret, rewrite, or replace the worker's `status`, `summary`, `conflicted_files`, or `pr_title` except for the explicit validation notes below.
   - A `created` result requires that branch worker call `create_pull_request` exactly once with a `temporary_id` and `assign_to_user` exactly once using that same temporary reference.
   - A `needs manual backport` or `failed` result must not have a `create_pull_request` call for that branch. If a branch worker reports either status after requesting a PR, keep the worker's returned status and append a concise contract-violation note to the final comment result.
   - If a branch worker returns `created` without a matching `assign_to_user` call, keep the branch status as `created` and append `Assignment request missing.` to the final comment result.
12. Post exactly one final `add_comment` following the exact template below after all branch tasks finish. Include a compact table with `Branch`, `Status`, and `Result`. Use statuses: `created`, `existing`, `skipped`, `needs manual backport`, or `failed`. The status for each worker branch must match the validated status from step 11. Do not fabricate PR URLs; gh-aw safe outputs will attach related created PRs to the comment after processing.
   - Keep every `Result` cell to one concise sentence that is under 80 characters.
   - For conflicts or manual-backport cases, summarize the blocker category. Do not include long conflict explanations, implementation analysis, or full file lists in the table.
   - For created PR requests, use a short phrase such as `Created backport PR.` If assignment was missing, append `Author assignment request missing.`
   - Do not add diagnostic paragraphs after the table; workflow logs and the agent summary contain detailed run information.

## Final Comment Template

Use this shape for the final source PR comment:

```markdown
## Backport resolution attempt complete

| Branch | Status | Result |
| --- | --- | --- |
| 8.19 | created | Created backport PR. |
| 9.4 | needs manual backport | Structural OAS conflicts need manual resolution; see workflow logs. |

These backports were prepared by an agent. Please review the generated PRs carefully before merging.

```

