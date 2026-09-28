
# Validate Pull Request

Validate if this Pull Request meets our project criteria.

## Trigger

This workflow is triggered by label command on Pull Request.

## Checks

- **Commit Signing**
  - **Input**: Read `/tmp/gh-aw/agent/pr_commits.json` for summarized commit objects.
  - **Verification**: Inspect the `verification` object of every commit on this Pull Request, and verify if all commits on this Pull Request are properly signed.
  - **Context**: Refer to `CONTRIBUTING.md` for this commit signing policy.

- **DCO (Developer’s Certificate of Origin)**
  - **Input**: Read `/tmp/gh-aw/agent/pr_commits.json` for summarized commit objects.
  - **Verification**: Inspect the `message` field of every commit on this Pull Request, and verify if all commits on this Pull Request contain a valid `Signed-off-by:` trailer for DCO compliance.
  - **Context**: Refer to `CONTRIBUTING.md` for this policy.

- **Pull Request Checklist**
  - **Input**: Read `/tmp/gh-aw/agent/pr_checklist.md` for extracted and sanitized Pull Request checklist using whitelist.
  - **Verification:** Read the extracted Pull Request checklist, and verify if it contains the Pull Request template and all the items are checked.

## Outputs

You MUST add a single pull request comment and use the accept tool once as described below.

**Pull Request Comment**:

- **Condition**: Always add a summary comment, regardless of the check result.
- **Output Format**: You MUST add a summary comment that describes what you verify on the Pull Request.
- **Summary Line**: The first line of your comment MUST be a single-line summary of this validation, starting with either ✅ or 🚫.

**Accept tool**:

- **Condition**: Always call the `accept_validate_pr` tool, regardless of the check result.
- **Output Format**: You MUST send the check result to the `accept_validate_pr` tool to control merge admittance, providing the three boolean fields: `commit_signing`, `dco`, and `pull_request_checklist`.
