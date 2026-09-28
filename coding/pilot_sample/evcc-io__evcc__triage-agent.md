
# Triage Agent

## Context

- **Repository**: ${{ github.repository }}

## Label the Issue/Pull Request

Look at the issue/pull request. Analyze title and body, then add one of the allowed labels: `bug`, `enhancement`, `documentation`, `question`, `device`, `tariff`, `vehicle`, `heating`.

Skip updating the issue/pull request if it already has a label attached.

If you add the `bug` label, also set the issue type to `bug`.

## Identify Supporters

If an issue is a `bug`, try to identify potential causes by looking at recent pull requests not older than 3 months.

If you find pull requests that may have introduced the bug, try identifying potential supporters for the issue. Supporters may be:

- authors or commentators of the pull request
- code owners for the code modified in the pull request (see CODEOWNERS file)

If you can identify a pull request that may have introduced the bug, mention the pull request in the issue. If identified, mention the supporter, explaining why he was mentioned.
