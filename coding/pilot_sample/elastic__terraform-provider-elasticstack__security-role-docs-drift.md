
# Security role docs drift worker

Pre-activation has computed drift against the live Kibana features API. Read the drift report at `/tmp/gh-aw/agent/drift-report.json` and open exactly one pull request when drift exists.

## Pre-activation context

- **Report path**: `/tmp/gh-aw/agent/drift-report.json`

## Task

1. Read `/tmp/gh-aw/agent/drift-report.json`.
2. Update `scripts/security-role-docs/kibana-features.json` so it reflects the live Kibana feature set from the report:
   - add unknown features to `documented` when they should appear in the guide
   - remove features from `documented` when they appear in `removed_features`
   - if a feature should stay undocumented, reviewers can move it from `documented` to `skip`
3. Update the Kibana feature privilege reference in `templates/guides/security-roles.md.tmpl` to match the feature changes.
4. Run `make docs-generate` so `docs/guides/security-roles.md` matches the updated template.
5. Create exactly one pull request with the resulting changes.

## Pull request requirements

- Explain the drift found using `unknown_features` and `removed_features` from the report.
- State that reviewers may move newly added features from `documented` to `skip` when the feature should remain excluded from the guide.
- Do not create issues.
- If the report contains no actionable drift after inspection, call `noop` instead of opening a pull request.
