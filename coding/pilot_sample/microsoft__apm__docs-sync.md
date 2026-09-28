
# Docs Sync Advisory

You are orchestrating the **docs-sync** skill against pull request
**#${{ github.event.pull_request.number || inputs.pr_number }}** in `${{ github.repository }}`.

> The label-name guard runs at the workflow level via the top-level
> frontmatter `if:` field (skips both `pre_activation` and `activation`
> for unrelated labels). If you are reading this prompt, the triggering
> label is `docs-sync` or this is a manual `workflow_dispatch` --
> proceed.

## Step 1: Gather PR context (read-only)

Use `gh` CLI -- never `git checkout` of PR head. We are running in the
base repo context with read-only permissions; the PR diff is the only
untrusted input we touch, and `gh` returns it as inert data.

```bash
PR=${{ github.event.pull_request.number || inputs.pr_number }}
gh pr view "$PR" --json title,body,author,additions,deletions,changedFiles,files,labels
gh pr diff "$PR"
gh pr diff "$PR" --name-only
```

Also check for the `docs-sync-confirm` label on this PR -- it gates
the optional companion-PR step (Step 7 of the skill).

```bash
gh pr view "$PR" --json labels --jq '.labels[].name' | grep -q docs-sync-confirm && echo "CONFIRM_PRESENT=true" || echo "CONFIRM_PRESENT=false"
```

## Step 2: Run the docs-sync skill

Load the **docs-sync** skill and follow its execution checklist
(Steps 1-7) and output contract exactly. The skill owns:

- Classifier dispatch (the cost gate)
- Localizer or architect dispatch on in_place / structural verdicts
- Per-page fan-out panel (doc-writer + python-architect verifier)
- Editorial-owner and growth-hacker single passes
- CDO synthesis with bounded ALIGNMENT LOOP (N <= 3 redrafts)
- Cost ceiling enforcement (15 LLM calls max per run)
- Single-comment emission via `safe-outputs.add-comment` (NOT the
  GitHub API directly)
- Label sweep via `safe-outputs.remove-labels` (drops `docs-sync` so
  re-applying it re-runs the skill)
- Companion-PR creation IF AND ONLY IF the `docs-sync-confirm`
  label is present (the A9 SUPERVISED EXECUTION boundary)

The skill body is at `.apm/skills/docs-sync/SKILL.md` (resolved
from the import above).

The advisory comment uses the stable header `## Docs sync advisory`
for idempotent edit-in-place on re-runs.
