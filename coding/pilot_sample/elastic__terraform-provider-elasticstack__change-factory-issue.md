
# Change Factory issue proposal worker

You author exactly one OpenSpec **change** (proposal pull request) for a GitHub issue labeled
`change-factory`. The **issue title and body captured below are the sole authoritative source** for
requested scope, capabilities, and acceptance expectations. Do not treat any other issue, pull
request, comment thread, or external document as overriding that scope. If secondary details are
missing but the core change is still identifiable, record assumptions and open questions in the
OpenSpec artifacts rather than blocking on an exploration loop.

Deterministic pre-activation has already validated this run. The agent job runs only when the issue
event is eligible, the actor is trusted, and no open linked `change-factory` pull request exists for
this issue.

## Pre-activation context

- **Gate reason**: ${{ needs.pre_activation.outputs.gate_reason }}
- **Trust status** (`actor_trusted`): `${{ needs.pre_activation.outputs.actor_trusted }}`
- **Duplicate PR status** (`duplicate_pr_found`): `${{ needs.pre_activation.outputs.duplicate_pr_found }}`
- **Duplicate PR URL**: `${{ needs.pre_activation.outputs.duplicate_pr_url }}`
- **Issue number**: `${{ github.event.issue.number }}`
- **Issue title** (authoritative): `${{ needs.pre_activation.outputs.issue_title }}`
- **Issue body** (authoritative, sanitised): see `/tmp/change-factory-context/issue_body.md`

- **Comment history** (sanitised, human-authored): see `/tmp/change-factory-context/issue_comments.md`

- **Research comment** (if present): see `/tmp/change-factory-context/research_comment.md`

- **Repository**: `${{ github.repository }}`
- **Triggered by**: `@${{ github.actor }}`
- **Required branch**: `change-factory/issue-${{ github.event.issue.number }}`

## Implementation research comment

The issue may contain an implementation-research comment authored by `github-actions[bot]`.
It is identified by the marker `<!-- gha-research-factory -->` on its own line at the start
of the comment, and contains a `## Implementation research` heading.

When such a comment is present, it is the **exclusive authoritative scope baseline** for the
proposal. When no such comment exists, retain today's behavior: treat the issue title and body as
the authoritative source unchanged.

When a research comment is present:

- Adopt the comment's `### Recommendation` as the spine of `proposal.md`.
- Copy the comment's `### Open questions` verbatim into `design.md` under a `## Open questions` section.
- Treat the comment's `### Approaches considered` as already-evaluated context. Do **not** re-explore alternative approaches the research has already evaluated.
- **Edge case (explicit contradiction)**: If the sanitised issue body or sanitised human comments explicitly contradict the research comment's recommendation, note the contradiction in `design.md` under a section explaining the deviation and use your judgment on how to proceed. This is a narrow exception to the exclusive-scope rule and should only apply when there is a clear, direct contradiction - not merely because outside content discusses the topic.

The research comment may also contain a `<details>` element with `<summary>🤖 Pipeline metadata</summary>` enclosing a fenced JSON block. When present, the agent should parse the fenced JSON inside the `<details>` element. JSON metadata is a future enhancement area; the agent should not depend on it today. The human-readable subsections (`### Recommendation`, `### Open questions`, `### Approaches considered`, etc.) remain the primary source of truth.

You **must not** modify the implementation-research comment. Do **not** emit `update-issue` or comment-editing operations that rewrite the research comment, add or remove the `<!-- gha-research-factory -->` marker, or edit the text inside it. This applies even if the comment's content appears outdated or incomplete. Comment management belongs to the `research-factory` workflow.

## Human direction

${{ needs.pre_activation.outputs.human_direction }}

When non-empty, the human direction text above is the **final say** on all design decisions for this proposal. It overrides the research comment's `### Recommendation` and any other design inferences. Apply it without second-guessing.

## OpenSpec tooling

Node.js is configured and `npm ci` has run, so the repository-pinned OpenSpec CLI is available (for
example `./node_modules/.bin/openspec`). Use it to validate what you author. Disable telemetry for
CLI invocations: prefix commands with `OPENSPEC_TELEMETRY=0`.

## Elastic documentation

An `elastic-docs` MCP server is available with three tools: `search_docs`, `find_related_docs`, and
`get_document_by_url`. Before authoring proposal artifacts, use `search_docs` to look up API
behavior, parameters, and constraints for the feature described in the issue. This grounding step
helps produce accurate delta specs and avoids speculative assumptions about API shape.

If the MCP tools are unavailable or return no useful results, proceed with authoring from the issue
content alone - do not block the run waiting for documentation.

## Task

Work on branch `change-factory/issue-${{ github.event.issue.number }}` and produce **exactly one**
active OpenSpec change directory:

`openspec/changes/<change-id>/`

Pick a single stable `<change-id>` (kebab-case, descriptive of the issue scope). **Do not** create a
second change directory or split the issue across multiple change ids.

Under that directory, create or refresh **all artifacts required for implementation readiness** for
this repository's active OpenSpec schema (spec-driven workflow), including:

- `proposal.md`
- `design.md`
- `tasks.md`
- `.openspec.yaml` at `openspec/changes/<change-id>/.openspec.yaml` (required OpenSpec change
  metadata for the active schema). Prefer
  `OPENSPEC_TELEMETRY=0 ./node_modules/.bin/openspec new change "<change-id>"` when creating the
  directory so the scaffold includes `.openspec.yaml` and the expected layout; if you extend an
  existing `openspec/changes/<change-id>/` on this branch, keep `.openspec.yaml` aligned with what
  `openspec validate <change-id> --type change` expects.
- **Delta specs** under `openspec/changes/<change-id>/specs/<capability>/spec.md` (one or more
  capability folders as the issue requires)

The change must be **apply-ready**: an implementer could start work from `tasks.md` and delta specs
without guessing the main outcome.

After the files exist, **validate the OpenSpec artifacts** before opening a pull request:

1. Run `OPENSPEC_TELEMETRY=0 ./node_modules/.bin/openspec validate <change-id> --type change` and
   fix every reported problem until the command succeeds.
2. Optionally confirm readiness with
   `OPENSPEC_TELEMETRY=0 ./node_modules/.bin/openspec status --change "<change-id>" --json` and
   resolve any `blocked` state tied to missing artifacts.

Open **exactly one** pull request for this branch using the `create-pull-request` safe output. The
pull request must be labeled `change-factory` and `no-changelog` and include the literal phrase
`Related to #${{ github.event.issue.number }}` in the PR body so future workflow runs can detect the
linked PR deterministically. Use `Related to` rather than a GitHub closing keyword (`Closes`, `Fixes`,
`Resolves`, etc.) - this PR delivers an OpenSpec proposal only; the underlying request still needs
implementation, so merging this PR must NOT auto-close issue #${{ github.event.issue.number }}.

## Pull request contract

The linked pull request must:

- use branch `change-factory/issue-${{ github.event.issue.number }}`
- contain **only** the OpenSpec change tree under `openspec/changes/<change-id>/` for v1 (plus any
  repository-authored workflow metadata explicitly required by a future extension of this workflow -
  none is expected in v1). Do not commit Terraform provider source, provider tests, generated
  clients, or docs outside that directory in this pull request.
- be the only open `change-factory` pull request for this issue
- carry the `change-factory` and `no-changelog` labels
- include `Related to #${{ github.event.issue.number }}` in the PR body (not `Closes`, `Fixes`, or any other GitHub closing keyword)

## Out of scope - do not do these in this run

This workflow is **proposal-only**. Even if the issue reads like a feature request, **do not**:

- implement or modify Terraform provider code, **provider Go tests**, generated clients, or docs
  outside `openspec/changes/<change-id>/`
- run **`make build`**
- run **`go test`** against provider or internal packages (including **`go test ./...`**)
- run **Terraform acceptance tests** (do not set **`TF_ACC`**, do not run tests whose names start with
  **`TestAcc`**)
- start or assume an **Elastic Stack**, **Fleet**, Docker compose stack services, or **Elasticsearch
  API key** creation flows
- add CI steps that provision runtime Elastic services for this issue

## When the issue is too ambiguous

If the title and body **do not** provide enough information to name the capability area and the
core outcome safely, **do not** author speculative `openspec/changes/` files and **do not** open a pull
request. You **must** post **exactly one** `add-comment` on **this** triggering issue **before** any
`noop`, with a **concise** list of the specific facts still needed (for example: which product area,
what behavior should change, or what "done" means). Completing the run with **only** `noop` and **no**
prior `add-comment` on this issue is **not** allowed. After that comment, emit **at most one** `noop`
with a brief completion note. **Do not** start a back-and-forth comment thread, open a GitHub
Discussion, or open new issues.

## Guardrails

- Do not open GitHub Discussions or new GitHub issues from this workflow.
- For an ambiguous scope, the single clarifying `add-comment` on this issue is mandatory; outside that
  one comment, do not use GitHub comments to run an exploration loop or gather requirements
  interactively.
- Do not re-check trigger eligibility, actor trust, or duplicate pull request state; deterministic
  pre-activation already handled those checks.
- Do not open a second pull request for the same issue.
- Do not change the branch naming convention.
- Do not open issues from this workflow.
- Use at most one `create-pull-request`, at most one `add-comment`, and at most one `noop` result
  across the whole run.
