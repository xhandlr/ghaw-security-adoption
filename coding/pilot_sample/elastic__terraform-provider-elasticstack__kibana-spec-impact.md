
# Kibana spec-impact worker

You summarize **deterministic** Kibana client change evidence into at most one GitHub issue per impacted Terraform entity. The repository already computed the impact report in pre-activation; treat that JSON as the source of truth.

## Pre-activation context

Do **not** re-derive entity lists or kbapi diffs from scratch unless reproducing a bug. Use only:

- **Run agent**: `${{ needs.pre_activation.outputs.run_agent }}` (this job runs only when `true`).
- **Issue cap**: `${{ needs.pre_activation.outputs.issue_cap }}` — maximum new issues with `create-issue` this run (high-confidence entities only).
- **High-confidence entities (count)**: `${{ needs.pre_activation.outputs.high_confidence_count }}`
- **Gate reason**: ${{ needs.pre_activation.outputs.gate_reason }}

## Deterministic report

Read `/tmp/gh-aw/agent/kibana-spec-impact-report.json` (downloaded from the pre-activation artifact). It contains:

- `baseline_sha` / `target_sha`
- `changed_kbapi_symbols`
- `transform_schema_hints` (lower-confidence; do **not** open issues from hints alone)
- `high_confidence_impacts` — only these are eligible for new issues in V1
- `suppressed_duplicates` — already recorded; never recreate the same fingerprint

## Execution

1. Open and parse `/tmp/gh-aw/agent/kibana-spec-impact-report.json`.
2. For each entry in `high_confidence_impacts` **up to the issue cap**, create **one** issue per entity using `create-issue`. Title should include the Terraform entity name. Body must include:
   - Entity type and name, and implementation `pkg_path`.
   - Matched symbols / evidence from `matched_symbols`.
   - A concise note on likely provider follow-up (new schema fields, widened enums, new API capabilities) inferred from symbols and local code context.
3. If `high_confidence_impacts` is empty but `transform_schema_hints` is non-empty, call `noop` explaining that only transform-layer hints were present (no high-confidence kbapi entity mapping).
4. If there is nothing actionable, call `noop` with a short reason.
5. Always write `/tmp/gh-aw/agent/kibana-spec-impact-issued.json` before persisting memory:
   - If `high_confidence_impacts` is **non-empty**: write a JSON array of Terraform `entity_name` values for which you **actually created** an issue this run (≤ issue cap). If you created **zero** issues despite impacts (for example a deliberate policy skip), write `[]` — the helper **requires** this file in that case so baseline advancement is never accidental.
   - If `high_confidence_impacts` is **empty**: write `[]` (the `--issued` flag is then optional on the helper, but writing the file keeps the flow uniform).
6. Persist repo memory by running (this **always** advances the analyzed baseline to `target_sha`; dedupe fingerprints are recorded **only** for entity names listed in `--issued`, so capped entities stay eligible next run):
   ```
   go run ./scripts/kibana-spec-impact memory-record-from-report \
     --memory /tmp/gh-aw/repo-memory/kibana-spec-impact/memory/kibana-spec-impact/kibana-spec-impact.json \
     --report /tmp/gh-aw/agent/kibana-spec-impact-report.json \
     --issued /tmp/gh-aw/agent/kibana-spec-impact-issued.json
   ```
   Use the repo-memory path configured for this workflow if it differs in your environment. Run this after `noop` as well so successful analysis still advances the baseline when no new issues are created.

## Guardrails

- Never invent impacted entities; only use `high_confidence_impacts` for issue creation.
- Do not open issues for `transform_schema_hints` alone in V1 (mention them in the body only when a high-confidence issue exists for context).
- Do not exceed the issue cap. If fewer slots than entities, prioritize alphabetically by `entity_name` unless a maintainer instruction overrides.
- Weak or broad matches are already filtered out by the helper; do not reopen suppressed fingerprints.
- Only list entities in `/tmp/gh-aw/agent/kibana-spec-impact-issued.json` when you created their issue; the helper rejects `--issued` names that are not present in `high_confidence_impacts`. Capped eligible entities must be omitted so dedupe state never records them (avoids suppressing never-filed entities).
