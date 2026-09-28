
# Flaky Test Fixer

Open a single draft PR with the smallest possible test-side fix for this flaky-test issue. Do not open a PR if either of the following is true: you find an existing open PR with an identical or similar fix (search PRs for ones that reference this issue number in their body, or check the issue timeline for PRs that reference it), or you cannot identify a credible fix.

## Steps

1. Read the investigator's comment on the issue for the suspected root cause and proposed fix. If no action is needed, stop.
2. Read the failing test and the helpers, fixtures, and page objects it imports.
3. Apply the smallest test-side patch that addresses the root cause.
4. Run the test locally until it passes.
5. Open the PR (see "PR format" below).

## PR format

- **Title**: `[<Plugin name>] <concise summary of the fix>`. Derive the plugin name from the test file path (e.g. `x-pack/solutions/security/plugins/security_solution/...` → `Security Solution`).
- **Body**:

  ```
  Fixes #<issue-number> (add more issue numbers here if this fix resolves multiple issues)

  ### Summary
  <a few bullet points: what was failing, and what this patch changes - keep it very concise, every bullet point must be earned>

  <if this fix matches what the failed test investigator already proposed in the issue, reference it instead of repeating it here; otherwise, explain how and why it differs>

  <details>
  <summary>Verification</summary>

  #### Verified locally

  <bullet list of what you successfully ran on this branch — e.g. `yarn kbn bootstrap`, `node scripts/check --profile agent`, the targeted test passed N times in a row, etc. Include the exact commands.>

  #### Not verified locally

  <bullet list of what you could not verify and why. E.g., behavior under CI parallel load, on a different stack version, against a real Elasticsearch instance, etc. Omit this section if there is nothing to mention.>

  </details>
  ```

Add the following at the very end of the PR description (and outside of the details block):

```markdown
> [!NOTE]
> Created by the Flaky Test Fixer workflow. Share feedback or questions in #appex-qa.
```
