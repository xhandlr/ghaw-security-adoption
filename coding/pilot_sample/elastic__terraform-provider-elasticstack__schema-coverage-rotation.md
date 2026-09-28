
# Schema Coverage Rotation Worker

You are responsible for running schema-coverage analysis on up to `${{ needs.pre_activation.outputs.issue_slots_available }}` provider entities per run, prioritizing the entities that have not been analyzed for the longest time.

## Pre-activation context

A deterministic pre-activation step has already computed schema-coverage issue capacity for this run. Do **not** query GitHub issue counts yourself; use only the values below.

- **Open schema-coverage issues**: `${{ needs.pre_activation.outputs.open_issues }}`
- **Issue slots available**: `${{ needs.pre_activation.outputs.issue_slots_available }}`
- **Gate reason**: ${{ needs.pre_activation.outputs.gate_reason }}

The workflow reached this point only because `issue_slots_available` is non-zero. You may open up to `${{ needs.pre_activation.outputs.issue_slots_available }}` new issues in this run.

## Required inputs and references

- Skill instructions: `.agents/skills/schema-coverage/SKILL.md`

## Repository toolchain

Deterministic workflow steps have already installed Go from `go.mod`, exported `GOROOT`, `GOPATH`, and `GOMODCACHE` for AWF, installed Node from `package.json`, and run `make setup` at the repository root. Use the resulting `go` and Node/npm tooling (including `npx openspec` when applicable) as-is for repository-local commands. Do **not** install alternate Go or Node versions, run ad hoc toolchain installers, or spend steps discovering toolchain versions.

## Execution steps

1. Read `.agents/skills/schema-coverage/SKILL.md` and follow it strictly when evaluating coverage.
2. Build the canonical entity inventory with:
   ```
   go run ./scripts/schema-coverage-rotation prepare \
     --memory /tmp/gh-aw/repo-memory/schema-coverage-rotation/memory/schema-coverage-rotation/schema-coverage.json
   ```
3. After the inventory has been prepared, select exactly `${{ needs.pre_activation.outputs.issue_slots_available }}` entities to analyze by running:
   ```
   go run ./scripts/schema-coverage-rotation select \
     --memory /tmp/gh-aw/repo-memory/schema-coverage-rotation/memory/schema-coverage-rotation/schema-coverage.json \
     --count ${{ needs.pre_activation.outputs.issue_slots_available }}
   ```
   The command prints a JSON array on stdout. Each entry has a `type` field (`"resource"` or `"data source"`) and a `name` field (the Terraform entity name). Log that exact JSON array to the job output, then use it to determine which entities to analyze and their types.
   Reuse this exact JSON array for step 5 without mixing in non-JSON log lines.
4. For each selected entity:
   - Perform schema coverage analysis using the skill rubric.
   - Determine whether there are actionable testing gaps.
5. After completing analysis of all selected entities, persist all analysis timestamps in a single atomic write by running:
   ```
   go run ./scripts/schema-coverage-rotation record \
     --memory /tmp/gh-aw/repo-memory/schema-coverage-rotation/memory/schema-coverage-rotation/schema-coverage.json \
     --entities '<json>'
   ```
   where `<json>` is the full JSON array returned by step 3 (the `select` output), unchanged except for shell-safe quoting.
## Issue creation rules

- Create one issue per analyzed entity only when actionable testing gaps exist.
- Never create more issues than `${{ needs.pre_activation.outputs.issue_slots_available }}` for the current run.

Issue content must include:
- Entity name.
- Entity type (`resource` or `data source`).
- Entity implementation directory path.
- Attributes with no coverage.
- Attributes with poor coverage.
- Prioritized top 5 gaps (or fewer if less exist).
- Concrete acceptance-test additions that would close those gaps.

If an analyzed entity has no actionable gaps, do not create an issue for it.

If at least one entity was analyzed but none has actionable gaps, you MUST call `noop` with a short reason.

## Dispatch
After creating all issues for this run (or if no issues were created), call the `dispatch_code_factory` safe output tool once to dispatch the `code-factory` workflow for each created issue.
