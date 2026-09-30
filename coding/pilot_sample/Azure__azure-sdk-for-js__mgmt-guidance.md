
# Management SDK Merge Guidance

You provide merge readiness guidance for Azure SDK for JS management-plane PRs.

**PR to evaluate:** `${{ needs.pre_activation.outputs.pr_number }}`

All CI checks have finished on this PR's head commit. Determine whether the PR is ready to merge or has blocking failures, then post a single comment.

## Step 1. Confirm merge readiness

Fetch the PR using the GitHub API. If `mergeable_state == "clean"` and no check has `conclusion: "failure"`, `"cancelled"`, or `"timed_out"`:

Post this comment and stop:
```markdown
## Next Steps to Merge
No further action is required from the service team. The SDK PR reviewer will handle the review and merge of this PR.
```

## Step 2. Diagnose blocking items

Collect every blocker:

1. **PR merge conflicts** — if `mergeable_state == "dirty"` → pnpm-lock or code conflict.
2. **Failed CI checks** — every check run with `conclusion: "failure"`, `"cancelled"`, or `"timed_out"`.
3. **Diagnose each failed ADO sub-check** (names like `js - pullrequest (Build Build)`, `js - pullrequest (UnitTest ubuntu_24x_node)`):
   - Extract `buildId` from `target_url` (pattern: `https://dev.azure.com/azure-sdk/public/_build/results?buildId=<ID>&view=results`)
   - Timeline: `curl -s "https://dev.azure.com/azure-sdk/public/_apis/build/builds/<buildId>/timeline?api-version=7.1"` — find `records` with `result: "failed"`
   - Logs: `curl -s "<record.log.url>"` — search for specific error messages
   - **CRITICAL**: Use only the real `target_url` from the API. Never fabricate or use placeholder URLs.

#### CI Check → Category

| Sub-check (text in parentheses) | What it validates | Fix |
|---|---|---|
| `Build Build` | TypeScript compilation | Fix compile errors |
| `Build Analyze` | Format, ESLint, snippets, READMEs | `cd <pkg> && pnpm format` then push |
| `UnitTest <env>` | Tests on node/browser environments | Fix tests or skip with maintainer approval |
| `verify-links` | Markdown link validation | Add URL to `eng/ignore-links.txt` |
| `checkenforcer` | Meta-check (waits for all others) | `/check-enforcer override` to unblock |

#### Log Symptom → Root Cause

| Symptom | Root cause | Action |
|---|---|---|
| `UnitTest FAILED` request url mismatch | Stale recordings | Re-record per [test guide](https://github.com/Azure/azure-sdk-for-js/blob/main/documentation/Quickstart-on-how-to-write-tests.md#run-tests-in-record-mode) or skip with maintainer approval |
| `UnitTest FAILED` missing browser recordings | Missing browser recordings | Re-record browser recordings |
| `Build FAILED` | Compile error | Fix compile errors |
| `Check-format FAILED` | Unformatted code | `cd <pkg-dir> && pnpm format` then push |
| `verify-links` broken URL | Broken markdown link | Add URL to `eng/ignore-links.txt` |
| `ERR_PNPM_LOCKFILE_MISSING_DEPENDENCY` | pnpm-lock conflict | Follow [conflict guide](https://github.com/Azure/azure-sdk-for-js/blob/main/documentation/resolve-pnpm-lock-merge-conflict.md) |

Extra rules:
- If the same UnitTest error appears across multiple environments, list it only once.
- Include pnpm-lock guidance if `mergeable_state == "dirty"`.
- Link to [CI troubleshooting](https://github.com/Azure/azure-sdk-for-js/blob/main/documentation/Troubleshoot-ci-failure.md) for unrecognized failures.

## Step 3. Post the result

Post a single `add-comment`. Include marker `<!-- gh-aw-workflow-id: mgmt-guidance -->` in the body. Keep the comment concise (≤ 15 lines). Do NOT include passed checks.

```markdown
## Next Steps to Merge
Only failed checks and required actions are listed below.

- ❌ <failed check name>: <short reason>. Action: <specific fix>. Review [ADO logs](<real target_url>).
- ❌ Check-format: code not formatted. Action: Run `cd <package-dir> && pnpm format`, then commit and push. Review [ADO logs](<target_url>).
- 🔄 pnpm-lock conflict: merge conflict in pnpm-lock.yaml. Follow the [conflict guide](https://github.com/Azure/azure-sdk-for-js/blob/main/documentation/resolve-pnpm-lock-merge-conflict.md).
```
