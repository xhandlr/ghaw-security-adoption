
# PR Documentation Check

Analyze a merged pull request in `microsoft/aspire` and determine whether documentation
updates are needed on the `microsoft/aspire.dev` documentation site. If updates are
needed, create a draft PR with the actual documentation changes.

## Context

- **Source repository**: `microsoft/aspire`
- **PR Number**: `${{ github.event.pull_request.number || github.event.inputs.pr_number }}`
- **PR Title**: `${{ github.event.pull_request.title }}`

> [!NOTE]
> The agent runs with `microsoft/aspire.dev` as the current workspace, so use
> GitHub tools for the source `microsoft/aspire` PR details and diff instead of
> expecting a local checkout of the merged PR contents to remain available.
>
> The target `microsoft/aspire.dev` branch (`release/X.Y[.Z]` or `main`) has
> already been resolved deterministically by a `pre-agent-steps:` shell step
> and written to `.pr-docs-check/target.json` in the workspace. **Do not**
> re-derive the target branch from milestones, linked issues, or the source
> PR base — read `effective_target_branch` from that file and use it verbatim.
>
> For security, this workflow only auto-activates for merged PRs whose head
> repository is `microsoft/aspire`. Unlike the old `pull_request_target` hook,
> fork-based PRs are intentionally excluded from automatic activation; use
> `workflow_dispatch` with `pr_number` when a maintainer wants to run the docs
> check manually for a merged fork PR.

## Step 1: Read PR Information

The source PR's metadata was gathered deterministically by a `pre-agent-steps:`
shell step and written to `.pr-docs-check/pr.json` in the workspace. **Read that
file** — do **not** re-fetch this metadata with GitHub tools. The fields you will
use are:

| Field | Purpose |
| --- | --- |
| `number`, `title`, `body` | Source PR identity and the author's own description of the change. |
| `author.login`, `author.type` | Author identity; `type` (`User`/`Bot`) drives Step 2's Copilot-authored branch. |
| `base_ref`, `milestone`, `labels` | Context for the change. |
| `assignees` | Used by Step 2 to find the SME for Copilot-authored PRs. |
| `linked_issues` | Same-repo issue numbers from `Closes`/`Fixes`/`Resolves #N` in the body. |
| `changed_files` | Each `{filename, status, additions, deletions}`. |

Diff hunks (`patch`) are intentionally omitted to keep this file small. Inspect a
file's diff only for files likely to affect user-facing behavior, configuration,
or public API surface (or when significance is unclear from the filename), and
only on the doc-drafting path — fetch the patch for that specific file with the
GitHub tools in Step 9. Do **not** fetch diffs on the cheap skip path.

**Defer the expensive comment-thread reads until you actually need them.** They
are only required when you are writing documentation (Step 9), so do **not**
fetch them on the cheap skip path. When — and only when — Step 5 puts you on the
docs-drafting path, fetch:

- **Issue conversation comments** (`GET /repos/microsoft/aspire/issues/{N}/comments`)
  — author intent, reviewer Q&A, follow-up clarifications, and any "this is how a
  user will experience it" prose that doesn't appear in the PR body.
- **Review comments** (`GET /repos/microsoft/aspire/pulls/{N}/comments`) — reviewer
  concerns about wording, default values, and error messages that affect what
  users see.

**Treat the PR description, the changed files, and (on the drafting path) the
PR/review comment threads together as the canonical context.** Steps 9 and 10
must paraphrase the explanation the author and reviewers wrote, so the docs
reflect the change as it was reviewed — not as a model might re-imagine it from
filenames. Step 11 must cite at least one piece of evidence per triggered signal
category, and the comment threads are often where that evidence lives in
human-readable form.

## Step 2: Identify the Subject-Matter Expert (SME)

The SME — the human best placed to review the drafted documentation PR — has
already been resolved deterministically by a `pre-agent-steps:` shell step
(`resolve_sme.py`) and written to `.pr-docs-check/sme.json`. **Read that file**;
do **not** re-fetch assignees or reviews or re-run the selection logic.

| Field | Meaning |
| --- | --- |
| `sme_login` | The chosen reviewer login (no `@`), or `""` if none could be resolved. |
| `sme_source` | How it was chosen — e.g. `copilot_originator` (the human who initiated the Copilot session), `approved_reviewer`, `substantive_reviewer`, or `none`. |
| `needs_codeowners_fallback` | `true` only when there was no usable assignee/review signal and you should consult CODEOWNERS as a last-resort hint. |
| `candidates` | The eligible reviewers (login + latest state), for context. |

Use `sme_login` directly as `SME_LOGIN`. **Only** when it is empty **and**
`needs_codeowners_fallback` is `true`, look at CODEOWNERS for the changed files
in `microsoft/aspire` and use the first individual login (skip team handles) as
a weak hint. If `sme_login` is empty and the fallback flag is `false`, leave
`SME_LOGIN` empty — the workflow drafts the PR without an explicit reviewer
rather than guess.

Capture the chosen login as `SME_LOGIN`. Do NOT include the `@` prefix. You will pass
this to the `notify_source_pr` safe output later.

## Step 3: Read the Pre-Resolved Target Branch

The target `microsoft/aspire.dev` branch was resolved before the agent started
by a deterministic `pre-agent-steps:` shell step. Its result is at
`.pr-docs-check/target.json` in the workspace. **Do not re-derive the target
branch from milestones, linked issues, or the source PR base** — those inputs
were already considered and the final answer is in this file.

Read `.pr-docs-check/target.json`. The fields you will use are:

| Field | Purpose |
| --- | --- |
| `effective_target_branch` | The branch you must base all docs edits and the draft PR on (`main` or `release/X.Y[.Z]`). |
| `candidate_source` | Why the candidate was chosen: `pr_milestone`, `linked_issue_milestone`, `pr_base`, or `fallback_main`. Use it in the PR description. |
| `candidate_source_detail` | The raw milestone title or base ref that drove the choice. Use it in the PR description. |
| `target_resolution` | How `effective_target_branch` was chosen: `exact_match`, `latest_release_fallback`, or `main_fallback`. Use it in the PR description. |

The remaining fields (`candidate_target_branch`, `available_release_branches`,
`enumeration_source`) are context only — don't second-guess the resolution.

The current workspace is `microsoft/aspire.dev`. Switch it to
`effective_target_branch` before editing docs:

- If `effective_target_branch` is `main`, you are already on the right branch
  by default; no switch is required.
- If `effective_target_branch` starts with `release/`, run
  `git checkout <effective_target_branch>` (the workflow `checkout:` block has
  already fetched `release/*` refs into `refs/remotes/origin/release/*`).

Do **not** create new branches or modify the resolution. The
`create_pull_request` safe output's `base` field must be set to exactly
`effective_target_branch`.

## Step 4: Read the Pre-Computed User-Facing Signals

Whether a docs PR is required is gated by a fixed catalogue of objective
signals computed by the `Compute user-facing signals` pre-agent step.
The result is at `.pr-docs-check/signals.json` in the workspace. **Do
not re-derive these signals from the diff or the PR body** — the file is
the source of truth, and the goal of this design is to make the
decision reproducible across model versions.

Read `.pr-docs-check/signals.json`. The fields you will use are:

| Field | Purpose |
| --- | --- |
| `excluded` | `true` when the PR is out of scope for docs generation (currently: a backport). When `true` it **overrides `recommendation`** — go straight to the Step 5 exclusion branch and skip. |
| `exclusion_reasons` | The reason names that caused `excluded` (e.g. `head_branch_is_backport`, `title_release_prefix`, `body_backport_marker`, `backport_label`; the weak `base_branch_is_release` only appears here as supporting context alongside a strong marker). Empty when `excluded == false`. |
| `recommendation` | `"docs_required"` if any gating signal fired, otherwise `"docs_optional"`. This is the primary gate for Step 5 **unless `excluded == true`**. |
| `triggered_signals` | The names of the boolean signals that fired (the advisory `only_test_or_build_changes` and the meta `is_backport` are excluded from this list and never force `docs_required`). |
| `signal_count` | `len(triggered_signals)`. |
| `signals` | The full boolean map, including the advisory `only_test_or_build_changes` and the meta `is_backport`. |
| `evidence` | Per-triggered-signal list of `{ file, hint }` entries showing the changed file and the matching diff fragment or PR-body snippet. Use these to write the PR description and the `notify_source_pr` summary. |

The catalog favors recall over precision: a false positive at worst
drafts a docs PR a human closes (drafted PRs never auto-merge), while a
false negative ships an undocumented user-facing change. You do **not**
need the full catalog definition here — `triggered_signals` and
`evidence` in `signals.json` tell you exactly which signals fired and
why, and the catalog itself is maintained in `compute_signals.py`.
Signal names are self-describing; they are grouped by source of evidence:

- **Group A — path-pattern** (which files changed): new/changed CLI
  commands, MCP tools, and CLI resource strings; new packages and
  hosting/client integrations; integration READMEs; public-API surface
  files (`src/*/api/*.cs`); dashboard pages; container image-tag files;
  project templates; the diagnostic catalog; analyzers; and
  `*Defaults.cs` / `*Constants.cs`.
- **Group B — diff-content** (what the patch added/removed): new CLI
  `Option<...>`; dashboard API endpoint changes;
  `[Obsolete]` / `[Experimental]` / `[DefaultValue]` attributes; new
  public types; breaking API removals from `api/*.cs`; container image
  version assignments; and target-framework changes.
- **Group C — PR-body**: a user-facing / usage / breaking-change heading,
  a long-form `--flag` mention, or breaking-change / security /
  deprecation prose.
- **Group D — PR-label**: a `breaking`-named or `security`-named label.
- **Advisory** `only_test_or_build_changes` (never gating; only narrows
  the Step 5 allowlist) and the conservative-recall gating fallback
  `diff_scan_skipped_due_to_missing_patch` (a Group B file whose `patch`
  the API omitted — treat as docs-required).

Before deciding in Step 5, **enumerate the triggered signals in your
internal reasoning** like:

> Triggered signals (5): `cli_command_added`, `cli_command_file_changed`, `cli_option_added`, `cli_resource_strings_changed`, `mcp_tool_file_changed`. Evidence: `LogsCommand.cs` is a new command file that adds `Option<string?>("--search")`; `LogsCommandStrings.resx` adds `SearchOptionDescription`; `ListConsoleLogsTool.cs` was modified to wire up the new search option.

This enumeration is not optional. The PR description you write in
Step 10 and the `summary` you emit in Step 11 must both cite at least
one `evidence` entry per triggered signal category so a human auditor
can verify the decision.

**Short-circuit:** if `excluded == true`, you do **not** need the
enumeration above — note the `exclusion_reasons` and go directly to the
Step 5 exclusion branch.

## Step 5: Decide Whether a Docs PR Is Required

The decision is driven by `.pr-docs-check/signals.json`.

### When `excluded == true` (checked first — overrides everything)

When `excluded` is `true`, the PR is **out of scope** for docs
generation and you must **not** draft a docs PR — regardless of
`recommendation`, `triggered_signals`, or the ambiguity rule below.

The current exclusion is **backport PRs**: a backport ports an
already-merged change onto a `release/*` branch, and its user-facing
documentation is authored against the original (forward) PR on the
default branch. Drafting a second docs PR for the backport is pure
duplicate noise. This workflow runs on `release/*` merges as well as
`main` (see the `on:` trigger), so backports reach this step and must
be filtered out here. Note that a `release/*` **base alone does not
exclude** — a direct release-only fix has the same base ref and *should*
be documented; `excluded` is only set when a strong backport marker
(backport head branch, `[release/...]` title, `Backport of #N` body, or
`backport` label) is present.

Take the `skipped` path: go to Step 6 and emit a single
`notify_source_pr` whose Step 5 branch is named
`"excluded → <reason>"`, citing the `exclusion_reasons` from
`signals.json`. Do **not** evaluate the `recommendation` branches below,
and do **not** apply the ambiguity rule.

### When `recommendation == "docs_required"`

A documentation PR is **mandatory**. Proceed to Step 7 and beyond.

There is exactly one allowed exception, and it has a hard evidentiary bar.
You may switch to the `skipped` path **only** when every triggered signal
is already documented by name in the existing `microsoft/aspire.dev`
docs — that is, the docs already mention the specific new flag, option,
API, tool, integration, page, endpoint, or behavior that the signal
identifies. To use this exception you **must** do all of the following:

1. For each triggered signal, search `src/frontend/src/content/docs/`
   (the docs content tree) for the exact identifier from the signal's
   `evidence` (for example, the flag name `--search`, the resx key
   `SearchOptionDescription`, the JSON property name, the API symbol).
2. Open the matching docs file and quote a sentence or code block that
   mentions the identifier by name.
3. In the `notify_source_pr` `summary` (Step 11), include — per
   triggered signal — the docs file path **and** the quoted text. Plain
   statements like *"the existing docs cover this area"* or *"this is
   internal"* are not acceptable; the audit trail must show the
   identifier appears in the docs verbatim.

If you cannot meet this bar for **every** triggered signal, draft the
docs PR. Partial coverage is not enough — if only some of the new
surface is documented, the PR must cover the rest.

### When `recommendation == "docs_optional"`

No deterministic user-facing signal fired. A docs PR is still required
when the change matches any of these positive triggers that the
pre-step cannot detect mechanically:

- A user-visible behavior change to an already-documented feature
  (for example, default values, output formats, error messages, or
  exit codes that ship to users and that the docs describe).
- A new environment variable, configuration key, or connection-string
  field exposed through existing public surface.
- A new supported version, runtime target, or platform mentioned in a
  docs `prerequisites` list.
- A change to user-visible localization strings already referenced by
  the docs site.

Otherwise, the `skipped` path is allowed **only** when the change
falls cleanly into one of these explicit allowlist categories. Pick
the single best fit:

| Allowlist category | Definition |
| --- | --- |
| `test_only` | Only files under `tests/` changed (matches `only_test_or_build_changes` *and* no source files changed). |
| `build_or_ci_only` | Only files under `eng/`, `.github/`, `playground/`, or top-level build config (`.editorconfig`, `global.json`, `Directory.Build.props`, `Directory.Build.targets`, `Directory.Packages.props`) changed. |
| `dependency_bump` | Only `Directory.Packages.props` (or equivalent package version files) changed and the change is purely a version bump with no behavior or surface change in this PR. |
| `internal_refactor` | The change touches `src/` but introduces no new or changed public types, methods, options, or strings. The PR title and body confirm this is purely internal. |
| `formatting_or_comment_only` | Pure typo fix, formatting, or code-comment-only change with no behavioral effect. |
| `bug_fix_restores_documented_behavior` | A bug fix that brings the implementation back in line with already-documented behavior. The docs already describe the intended behavior — the bug was the discrepancy. |
| `agent_or_skill_content` | Only files under `.agents/` changed (agent / skill content does not ship to `microsoft/aspire.dev`). |

If the change does not match exactly one of these categories, draft the
docs PR.

### Ambiguity rule

When the evidence is mixed or you are unsure, **draft the PR** (recall over
precision, as explained in Step 4). The drafted PR is in `draft:` state; it does
not merge until a human flips it out of draft. This rule does **not** apply
when `excluded == true` — an excluded PR is always skipped.

## Step 6: Emit the No-Docs Outcome (only when Step 5 allowed it)

This step runs **only** when Step 5 produced an allowed `skipped`
result. Emit a single `notify_source_pr` safe output with:

- `source_pr_number`: the source PR number from Step 1.
- `result`: `"skipped"`.
- `sme_login`: `SME_LOGIN` from Step 2 (or an empty string if none was found).
- `summary`: a structured markdown rationale that proves the decision.
  It **must** include:
  1. The Step 5 branch you took, named explicitly: either
     `"excluded → <reason>"` (use the `exclusion_reasons` from
     `signals.json`, e.g. `excluded → head_branch_is_backport`),
     `"docs_required → already documented by name"`, *or*
     `"docs_optional → <allowlist_category>"` (use the category name
     from the table above).
  2. The list of triggered signals from `.pr-docs-check/signals.json`
     (or "no signals triggered" when `signal_count == 0`).
  3. For the `already documented by name` branch: the per-signal docs
     file path and quoted sentence/code block from Step 5.
  4. For the allowlist branch: the changed-file globs that justify the
     chosen category (for example, *"all 4 changed files match `tests/**`"*).
  5. For the `excluded` branch: the `exclusion_reasons` from
     `signals.json` (for example, *"backport: base branch is
     `release/13.3` and title is prefixed `[release/13.3]`"*).

Then **stop**. Do **not** emit `create_pull_request` or any other safe
output on the no-docs path.

## Step 7: Read the doc-writer Skill

Read the file `.github/skills/doc-writer/SKILL.md` from the checked-out
`microsoft/aspire.dev` workspace. This skill contains comprehensive guidelines for
writing documentation on the Aspire docs site, including:

- Site structure and file organization
- Astro/MDX conventions and frontmatter requirements
- Required component imports (Starlight components)
- Formatting rules, code block conventions, and linking patterns

**You must follow all guidelines in the doc-writer skill when writing documentation.**

## Step 8: Browse Existing Documentation

Explore the existing documentation in `src/frontend/src/content/docs/` to:

- Identify pages that cover the affected feature area
- Confirm the documentation gap you identified in Step 5
- Determine whether existing pages need updates or new pages should be created
- Understand the current documentation structure, naming conventions, and patterns
- Find related pages that should be cross-referenced

**Keep this targeted.** Browse only the pages for the specific feature area the
triggering change touches — use the changed file paths and triggered signals to
narrow the search (e.g., grep the docs tree for the affected integration,
command, or API name). Do not read the whole docs tree or unrelated sections;
open at most a handful of candidate pages.

## Step 9: Write Documentation Changes

Based on your analysis, make the actual file changes in the workspace:

- **For updates to existing pages**: Edit the relevant `.mdx` files in place
- **For new pages**: Create new `.mdx` files in the appropriate directory following
  the doc-writer skill's conventions for frontmatter, imports, and structure

**Ground the documentation in the context you gathered in Step 1.** Specifically:

- Use the **source PR description** as the primary statement of what the
  change does and why. If the description includes "User-facing usage",
  "Breaking change", or example commands, those map directly to the
  user-oriented sections you write in the docs.
- Use the **list of changed files** (and their diff hunks for the
  surface-area files identified in Step 4's signals) to confirm the
  exact identifiers, flag names, option names, default values, and
  package IDs you cite in the docs. Never re-invent names; copy them
  verbatim from the diff.
- Use the **PR conversation and review comments** to capture nuance
  that doesn't appear in the PR body — reviewer-driven naming changes,
  follow-up clarifications about defaults, edge cases the author
  acknowledged, and any "we decided to do X for this reason" exchanges.
  These often answer the *why* questions a docs reader will ask.

If the PR description and comments contradict the diff (for example, the
body claims a flag is called `--search` but the resx says `--query`),
trust the diff for identifiers and ask the SME via the
`notify_source_pr` summary to clarify before merging the docs PR.

Keep the changes focused on the significant user-facing change that triggered this
workflow. Prefer updating the smallest correct set of pages over broad speculative edits.

Ensure all changes follow the doc-writer skill guidelines from Step 7. Include:
- Proper frontmatter (`title`, `description`)
- Required Starlight component imports
- Code examples where appropriate
- Cross-references to related documentation pages
- Correct use of Aside, Steps, Tabs, and other components

## Step 10: Create Draft PR

> [!IMPORTANT]
> Emit `create_pull_request` **exactly once**, and only after you have actually
> written documentation file changes to the workspace in Step 9. The safe output
> builds the PR from those workspace changes.
>
> **Treat any `create_pull_request` failure as non-retryable and never re-emit the
> same safe output after it.** Re-emitting after a deterministic error (no commits
> found, no diff to commit, an empty/invalid patch, a base-branch or validation
> error, a protected-file rejection, etc.) is a failure loop that burns the run's
> token budget without making progress. Handle a failure exactly once:
>
> - If it failed because you had not yet written any doc changes, write them now
>   (Step 9) and emit `create_pull_request` one more time — at most.
> - If it failed for any other deterministic reason — a base-branch or validation
>   error, a protected-file rejection, or an empty/invalid patch — **stop
>   drafting** and emit a single `notify_source_pr` with `result: "draft_failed"`.
>   Docs were required (Step 5), so this is a genuine failure, not a no-op: the
>   `draft_failed` result is surfaced under a ⚠️ banner so the author knows
>   documentation is still owed. The `summary` must name the failure reason and
>   list the triggered signals. Do not loop.
> - Only if, on inspection, there is genuinely nothing to document — the
>   triggering signal fired on a string that is not actually an Aspire
>   user-facing feature (a true false positive), so there is no concrete
>   documentation edit to make — **stop drafting** and emit a single
>   `notify_source_pr` with `result: "skipped"` whose `summary` explains that the
>   signal was a false positive and lists the triggered signals. Do not loop.

Create a draft pull request on `microsoft/aspire.dev` with:

**Base branch**: the `effective_target_branch` value from
`.pr-docs-check/target.json` (read in Step 3). When emitting the
`create_pull_request` safe output, set its `base` field to that exact string
(for example, `release/13.3`, `release/13.2.1`, or `main`). Do not derive or
modify this value.

**Title**: A clear, concise title describing the documentation work
(the `[docs]` prefix will be added automatically)

**Description** that includes:
- A prominent link to the source PR: `Documents changes from microsoft/aspire#<number>`
- The PR author mention: `@<author>`
- The target branch and how it was chosen, using `candidate_source`,
  `candidate_source_detail`, and `target_resolution` from
  `.pr-docs-check/target.json`. For example:
  - When `target_resolution` is `exact_match`: "Targeting `release/13.4`
    based on the source PR milestone `13.4`."
  - When `target_resolution` is `latest_release_fallback` and the candidate
    was a release branch: "Targeting `release/13.4` — the latest release
    branch on `microsoft/aspire.dev` — because `release/13.3` (from the
    source PR milestone `13.3`) does not exist there."
  - When `target_resolution` is `latest_release_fallback` and the candidate
    was `main`: "Targeting `release/13.4` — the latest release branch on
    `microsoft/aspire.dev` — because the source PR has no milestone or
    `release/*` base ref to derive a more specific target."
  - When `target_resolution` is `main_fallback`: "Falling back to `main`
    because `microsoft/aspire.dev` currently has no `release/*` branches."
- Why this PR is needed (the significant change and the docs gap it addresses)
- A summary of what documentation was added or changed
- A list of files modified or created
- Whether pages were updated or newly created

Do **not** include `reviewers` in the `create_pull_request` emission. The SME
identified in Step 2 is requested as a reviewer by the `notify_source_pr`
safe-output job, not by `create_pull_request`.

## Step 11: Notify Source PR

After emitting `create_pull_request`, emit a single `notify_source_pr` safe output
with:

- `source_pr_number`: the source PR number from Step 1.
- `result`: `"drafted"`.
- `sme_login`: `SME_LOGIN` from Step 2 (or an empty string if none was found).
- `target_branch`: the `effective_target_branch` value from
  `.pr-docs-check/target.json` (read in Step 3) — for example,
  `release/13.3` or `main`. Do not derive or modify this value.
- `summary`: a short markdown summary (1–3 sentences plus optional bullet list)
  of the documentation changes made. List the files modified or created. Do **not**
  describe links here — the workflow injects the drafted PR's URL automatically.

> [!IMPORTANT]
> Do **not** try to compose the drafted PR's URL or PR number yourself in the
> `summary` text. The `notify_source_pr` safe-output job knows the real values
> from the safe-outputs handler and will substitute them when posting the
> comment. Likewise, do **not** call `add_comment` for the "drafted",
> "skipped", or "draft_failed" path — `notify_source_pr` is the only commenting
> path used by this workflow.
