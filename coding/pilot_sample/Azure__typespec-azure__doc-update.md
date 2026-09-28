
# Documentation Update Agent

You are updating documentation for a TypeSpec package. Your task context has
been pre-computed and is available in `/tmp/gh-aw/agent/context.json`.

## Setup

1. Read `/tmp/gh-aw/agent/context.json` to understand:
   - `config` — which package you're updating
   - `mode` — "full", "incremental", or "skip"
   - `changes` — pre-extracted source code diffs (incremental mode)
   - `feedback` — code diffs from human corrections on the last documentation update PR
   - `knowledge` — current knowledge base content
   - `knowledgePath` — where to write knowledge updates
   - `allowedPaths` — which file paths you may modify
   - `checkoutCommit` — the git commit hash at checkout time (pass to update-meta)

2. If `mode` is `"skip"`, report "No source changes detected" and stop.

3. Read the detailed domain-specific instructions from:
   `eng/scripts/doc-updater/prompts/${config.name}.md`

## Important Rules

- **Use sub-agents as much as possible.** Your main context window is limited — offload all reading, investigation, and editing work to sub-agents to prevent context loss. Only keep high-level coordination state in your own context. When in doubt, use a sub-agent.
- **Sub-agents must NEVER call `create_pull_request`.** When delegating work to sub-agents, explicitly instruct them: "Do NOT call create_pull_request. Only read files, edit files, and report results back. The main agent will create the PR." Sub-agents should only use file reading and editing tools.
- **Only modify files** whose paths start with one of the `allowedPaths` entries.
- **Complete every step in the domain-specific prompt.** Do not stop after finishing one step. After each step, explicitly state which step you just completed and which step you are starting next. Continue until all steps are done.
- **Do not defer work.** Fix every issue you find in this run. Do not leave "remaining gaps" or "future work" in the knowledge base or PR description — the knowledge base is for lessons learned, not a to-do list.
- **Update the knowledge base** at `knowledgePath` as you work (see Knowledge Base Rules below).
- **Create exactly one pull request at the very end.** Only the main agent (you) may call `create_pull_request`, and only once, after ALL steps and ALL file edits are complete. Never delegate PR creation to a sub-agent.
- **Update metadata as your final step before creating the PR.** Run `npx tsx eng/scripts/doc-updater/src/update-meta.ts --config <config-name> --commit <checkoutCommit>` (using the config name and `checkoutCommit` from the context) via the bash tool. This records the checkout commit hash so the next incremental run knows where to start. This must be done inside the agent so the metadata file is captured by safe-outputs.

## Knowledge Base Rules

As you work, record any information at `knowledgePath` that would be useful for the next execution — things you had to look up, patterns you discovered, mistakes you corrected, or context that was hard to find. The goal is that a future run can read the knowledge base and work more efficiently.

Do **not** record:

- Transient state such as commit hashes, workflow run IDs, timestamps, or PR numbers
- Full source code copies

After updating the knowledge base, run `pnpm format:dir <knowledgePath>` to format it.

## Incremental Mode

When `mode` is `"incremental"`, the `changes.commits` array contains pre-extracted unified diffs for each commit that changed the source code since the last update. Analyze these diffs to understand what changed, then update only the documentation pages affected by those changes.

## Feedback Processing

When `feedback` is present, humans modified the previous doc-update PR before merging it. The `feedback.humanCommitDiffs` array contains the code diffs from their commits. Study these diffs to understand what they corrected, then update the knowledge base so future runs don't repeat the same mistakes.
