
Triage the following GitHub issue using the Prowler Issue Triage Agent persona.

## Context

- **Repository**: ${{ github.repository }}
- **Issue Number**: #${{ github.event.issue.number }}
- **Issue Title**: ${{ github.event.issue.title }}

## Sanitized Issue Content

${{ needs.activation.outputs.text }}

## Instructions

Follow the triage workflow defined in the imported agent. Use the sanitized issue content above — do NOT read the raw issue body directly. After completing your analysis, post your assessment comment. Do NOT call `add_labels` or `remove_labels` — label automation is not yet enabled.
