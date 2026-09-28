
# OpenSpec verify, archive, and clean up (label-gated)

You verify a pull request against **one** active OpenSpec change under `openspec/changes/<id>/`, following `.agents/skills/openspec-verify-change/SKILL.md`, submit a **single** pull request review, and **only** after an **APPROVE** review and when archive/push is allowed run `openspec archive` and push the branch. The **`verify-openspec`** label is removed by a deterministic script step before this agent runs; do **not** emit **`remove-labels`** safe outputs.

## Pre-activation context

Deterministic pre-activation steps have classified the pull request and selected the active change.

- **Selected change id**: `${{ needs.pre_activation.outputs.selected_change }}`
- **Review disposition** (do not infer from PR files): `${{ needs.pre_activation.outputs.review_disposition }}` — either `approval-eligible` or `comment-only`
- **Disposition reason** (authoritative; echo or paraphrase in the review body when relevant): ${{ needs.pre_activation.outputs.disposition_reason }}
- **Archive/push allowed**: `${{ needs.pre_activation.outputs.archive_push_allowed }}` — either `true` (same-repository PR) or `false` (fork PR)
- **Archive/push allowed reason**: ${{ needs.pre_activation.outputs.archive_push_allowed_reason }}
- **Gating**: already complete — the workflow reached this point only because exactly one active non-archive change was found with file statuses limited to `added` and `modified`. Do **not** re-inspect PR files, re-derive the change id, guess approval eligibility from the diff, or re-derive whether archive/push is allowed.

Use **`npx openspec`** for all OpenSpec CLI invocations.

## Verification (active change)

Let `<id>` be `${{ needs.pre_activation.outputs.selected_change }}`.

1. Run:

   - `npx openspec status --change "${{ needs.pre_activation.outputs.selected_change }}" --json`
   - `npx openspec instructions apply --change "${{ needs.pre_activation.outputs.selected_change }}" --json`

2. Read **`.agents/skills/openspec-verify-change/SKILL.md`** and perform verification **rooted at** `openspec/changes/<id>/` using the skill's steps (status / apply JSON for context files, completeness / correctness / coherence, **Issues by priority**: CRITICAL, WARNING, SUGGESTION, **Final assessment**).

Whilst reviewing the implementation, do not raise issues covered by CI. For example, do not:
  - Consider syntactic correctness of code.
  - Run tests.

Instead, check the results of Github actions runs for the PR.

## Structural allowlist and relevance

3. **Structurally in scope** (no per-file relevance classification required):

   - All paths under `openspec/changes/${{ needs.pre_activation.outputs.selected_change }}/`.
   - For each delta spec `openspec/changes/${{ needs.pre_activation.outputs.selected_change }}/specs/<capability>/spec.md`, the matching **`openspec/specs/<capability>/spec.md`** if it appears in the PR.

4. For **every other** changed file in the PR (outside the structural allowlist in step 3), read the diff and classify vs `openspec/changes/<id>/` artifacts (**proposal**, **design**, **tasks**, delta specs) as **`relevant`**, **`uncertain`**, or **`unassociated`**. This step covers **relevance classification only** for out-of-scope files: among those outcomes, **`unassociated`** is what blocks **APPROVE** on the relevance axis. It is **not** the full approval gate—**CRITICAL** issues from verification (steps 1–2) still block **APPROVE** per step 7. When unsure, prefer **`relevant`** or **`uncertain`**.

## Review body, inline comments, and decision

5. **Review body** must include:

   - Summary / scorecard from verification (**Issues by priority**).
   - **Out-of-scope / unassociated changes**: list **`unassociated`** files, summarize **`uncertain`**, note accepted **`relevant`** briefly.
   - When **`${{ needs.pre_activation.outputs.review_disposition }}`** is **`comment-only`** (net-new spec change material under the selected change): explain that the review is limited to **`COMMENT`** because it introduces a net-new spec change (added files under the active change), **including when the normal approval criteria are otherwise satisfied**. Do **not** imply the pull request met those criteria if verification reported **CRITICAL** issues; still describe the net-new **`COMMENT`** limitation. Tie this to the deterministic **Disposition reason** above.

6. Add **line-level** **`create-pull-request-review-comment`** entries for mappable CRITICAL (and other high-signal) issues and for **`unassociated`** hunks where the API allows; avoid spam on large **`relevant`** sets.

7. Submit **exactly one** **`submit-pull-request-review`** for this run:

   - Use **`APPROVE`** **if and only if** **`${{ needs.pre_activation.outputs.review_disposition }}`** is **`approval-eligible`** **and** there are **zero CRITICAL** issues and **zero `unassociated`** files.
   - Use **`COMMENT`** when **`${{ needs.pre_activation.outputs.review_disposition }}`** is **`comment-only`**, **including** when verification finds zero CRITICAL issues and zero **`unassociated`** files.
   - Otherwise (blocking issues / unassociated files) use **`COMMENT`**.
   - **Never** use **`REQUEST_CHANGES`**. WARNING and SUGGESTION **alone** do **not** block **`APPROVE`** for **`approval-eligible`** runs.
   - **`${{ needs.pre_activation.outputs.archive_push_allowed }}`** being `false` does **not** force **`COMMENT`** — the review decision is based solely on verification results and review disposition.

## Archive and push (APPROVE only, approval-eligible only, archive-push-allowed only)

8. **Only** if the review you submitted in step 7 used **`APPROVE`** **and** **`${{ needs.pre_activation.outputs.review_disposition }}`** is **`approval-eligible`** **and** **`${{ needs.pre_activation.outputs.archive_push_allowed }}`** is **`true`**:

   - Run **`npx openspec archive "${{ needs.pre_activation.outputs.selected_change }}" --yes`** (non-interactive; add `--skip-specs` only if the change is explicitly doc-only and repository policy allows — default is full archive).
   - If the working tree has changes, **commit** them with a clear message (e.g. `chore(openspec): archive ${{ needs.pre_activation.outputs.selected_change }} via verify-openspec`).
   - Use **`push-to-pull-request-branch`** to update the **triggering** PR branch.

9. If the review was **`COMMENT`**, or the run was **`comment-only`**, or **`${{ needs.pre_activation.outputs.archive_push_allowed }}`** is **`false`**, **do not** run `openspec archive`, **do not** commit for archive purposes, and **do not** call **`push-to-pull-request-branch`**.
