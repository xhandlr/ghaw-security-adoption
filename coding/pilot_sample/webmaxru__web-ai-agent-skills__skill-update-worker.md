
# Skill Update Worker

Read `.github/aw/skill-update-runtime.md` first, then execute the selected saved prompt described there and produce one pull request if that prompt leads to material repository changes.

## Inputs

- Runtime context file: `.github/aw/skill-update-runtime.md`

## Process

1. Read `.github/aw/skill-update-runtime.md` in full before taking any action.
2. Treat the markdown body of that saved prompt as the authoritative task definition for this run. Use its frontmatter only as routing and context metadata unless the body explicitly relies on it.
3. Resolve any relative file links in the saved prompt relative to the prompt file location.
4. Use the prefetched external-source copies and URL-to-file mapping listed in `.github/aw/skill-update-runtime.md` as the local substitutes for the saved prompt's built-in URLs.
5. Follow the saved prompt faithfully inside this repository: inspect the referenced files, use the prefetched source copies when the prompt refers to built-in URLs, and make only the edits justified by that prompt.
6. Reuse repository conventions from AGENTS.md and any checklist, template, validator, or support file that the saved prompt references.
7. Run the validation commands requested by the saved prompt when they apply to the files you changed and the command is available in this environment.
8. If the prompt leads to material repository changes, create exactly one pull request for this prompt run.
9. If the prompt determines that no material update is needed, or if it does not justify file edits, call `noop` with a short explanation instead of forcing a pull request.

## Pull Request Requirements

- Keep the branch and PR scoped only to the selected prompt described in `.github/aw/skill-update-runtime.md`.
- Use a concise PR title derived from the selected prompt slug in `.github/aw/skill-update-runtime.md`.
- Summarize the material deltas, validations run, and unresolved risks in the PR body.

## Constraints

- Do not process any prompt file other than the one identified in `.github/aw/skill-update-runtime.md`.
- Do not batch multiple prompt tasks into one branch or one pull request.
- Do not modify `.github/workflows/` or other automation files unless the saved prompt explicitly requires it.
- If no action is needed, call `noop` with a concise explanation.