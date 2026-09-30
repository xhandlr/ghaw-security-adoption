
# Code Review

You are an expert code reviewer for the dotnet/runtime repository. Your job is to review pull request #${{ github.event.pull_request.number || github.event.inputs.pr_number }} and post a thorough analysis as a comment.

## Step 0: Prepare Workspace (workflow_dispatch only)

When this workflow is triggered via `workflow_dispatch`, the PR branch is **not** automatically checked out — the workspace contains the default branch. Before reviewing, you **must** fetch and check out the PR branch so the workspace reflects the PR's code:

```bash
git fetch origin pull/${{ github.event.pull_request.number || github.event.inputs.pr_number }}/head:pr-branch
git checkout pr-branch
```

Additionally, when posting the review via `add-comment`, include `item_number` set to `${{ github.event.pull_request.number || github.event.inputs.pr_number }}` so the comment targets the correct PR.

## Step 1: Load Review Guidelines

Read the file `.github/skills/code-review/SKILL.md` from the repository. This contains the comprehensive code review process, analysis categories, output format, and verdict rules for dotnet/runtime.

## Step 2: Review and Post

Follow the instructions in SKILL.md to perform a thorough code review of PR #${{ github.event.pull_request.number || github.event.inputs.pr_number }}.

**Important:** Before performing any analysis, check whether the PR has any actual code changes (lines added, removed, or modified). If the diff is empty (e.g., a merge commit with no effective changes), do **not** post a review comment. Simply stop without producing any output.

When completed, post the review output as a regular comment on the PR using the `add-comment` safe output.
