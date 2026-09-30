
# PR Review Panel

You are orchestrating the **apm-review-panel** skill against pull request
**#${{ github.event.pull_request.number || inputs.pr_number }}** in `${{ github.repository }}`.

> The label-name guard runs at the workflow level via the top-level
> frontmatter `if:` field (skips both `pre_activation` and `activation`
> for unrelated labels). If you are reading this prompt, the triggering
> label is `panel-review` or this is a manual `workflow_dispatch` --
> proceed.

## Step 1: Gather PR context (read-only)

Use `gh` CLI -- never `git checkout` of PR head. We are running in the base
repo context with read-only permissions; the PR diff is the only untrusted
input we touch, and `gh` returns it as inert data.

```bash
PR=${{ github.event.pull_request.number || inputs.pr_number }}
gh pr view "$PR" --json title,body,author,additions,deletions,changedFiles,files,labels
gh pr diff "$PR"
```

## Step 2: Run the panel via the apm-review-panel skill

Load the **apm-review-panel** skill and follow its execution checklist
and output contract exactly. The skill owns reviewer routing, persona
dispatch, the Auth Expert and Doc Writer conditional rules, the
pre-arbitration completeness gate, CEO arbitration, template loading,
the advisory recommendation shape, and the one-comment emission
contract -- including writing the final comment to
`safe-outputs.add-comment` rather than the GitHub API and the
defensive sweep of legacy verdict labels via
`safe-outputs.remove-labels`.
