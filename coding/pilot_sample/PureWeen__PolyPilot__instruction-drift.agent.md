
# Instruction Drift — Detect & Update

> **🚨 No test messages.** Never call any safe-output tool with placeholder or test content.

## Step 1: Read Pre-computed Results

The staleness check ran in `steps:` (before you started) with authenticated `gh` CLI.
**Do NOT run Check-Staleness.ps1 yourself** — `gh` CLI is not authenticated inside this container.

Read the results. The file is large — extract only the releases and key signals:
```bash
# Check if changes were detected
python3 -c "import json; d=json.load(open('/tmp/drift-results/staleness.json')); print('changes_detected:', d.get('changes_detected')); [print(f'  {s[\"type\"]}: {s.get(\"last_reviewed_release\",\"\")} -> releases={len(s.get(\"result\",{}).get(\"releases\",[]))}') for m in d['manifests'] for s in m['sources'] if s['type']=='releases']"
```

If changes detected, extract the release notes:
```bash
python3 -c "
import json
d=json.load(open('/tmp/drift-results/staleness.json'))
for m in d['manifests']:
  for s in m['sources']:
    if s['type']=='releases' and s.get('result',{}).get('releases'):
      for r in s['result']['releases']:
        print(f'=== {r[\"tag\"]} ({r[\"published_at\"]}) ===')
        print(r.get('release_notes','')[:8000])
        print()
"
```

If there were errors, check:
```bash
cat /tmp/drift-results/staleness-errors.log
```

## 🚨 CRITICAL — What To Do

### If `changes_detected` is `false` → call `noop` NOW

Call the `noop` tool immediately:
```
noop(message="All instruction files are fresh — no drift detected.")
```
Do not create issues, PRs, or comments. Stop after calling noop.

### If `changes_detected` is `true` → continue below

---

## Analyze and Update

### Step 2: Build a checklist of ALL changes from release notes

Before editing any files, read EVERY release note above and build a complete list of changes. For each item, classify:
- **P0** = factually wrong in our docs
- **P1** = security-relevant change
- **P2** = new feature, new safe output, new config option, behavior change, bug fix that affects workflow authors
- **P3** = internal/cosmetic only (OTLP traces, CI pipeline changes, internal refactors)

**You MUST implement P0, P1, AND P2 items. Only skip P3.**

### Step 3: Read current skill files

Read ALL of these to understand what we currently cover:
```bash
cat .claude/skills/gh-aw-guide/SKILL.md
cat .claude/skills/gh-aw-guide/references/architecture.md
cat .github/instructions/gh-aw-workflows.instructions.md
cat .github/instructions/gh-aw-workflows.sync.yaml
```

### Step 4: Implement ALL changes

For EACH P0/P1/P2 item from your checklist:
1. Find the right section in the skill files
2. Add or update the content
3. Check off the item

**Where to add each type of change:**
- New safe output → anti-patterns table in SKILL.md + Safe Outputs section
- New frontmatter option → Frontmatter Features section in SKILL.md
- New trigger behavior → Trigger Selection Guide in SKILL.md
- Security change → Security-Critical Patterns in SKILL.md
- Protected files change → architecture.md Protected Files section
- Bug fix affecting workflow authors → relevant section + Known Issues if applicable

### Step 5: Update the sync manifest

In `gh-aw-workflows.sync.yaml`, update `last_reviewed_release` to the latest tag.

### Step 6: Verify completeness

Before committing, re-read your checklist. Every P0/P1/P2 item must be addressed. If any are missing, go back and add them.

### Rules
1. **Respect `divergence` sections** — NEVER remove: "Security Boundaries", "Safe Pattern: Checkout + Restore", "Common Patterns"
2. **Be exhaustive** — every author-facing feature, behavior change, and bug fix must be documented
3. **Include YAML examples** for new config options
4. **List what was skipped as P3** in the PR description with reasoning

Commit all changes together:
```bash
git add .claude/skills/gh-aw-guide/SKILL.md .claude/skills/gh-aw-guide/references/architecture.md .github/instructions/gh-aw-workflows.instructions.md .github/instructions/gh-aw-workflows.sync.yaml
git commit -m "docs: update gh-aw skill for <versions>

Co-authored-by: copilot-agentic-workflow[bot] <224017+copilot-agentic-workflow[bot]@users.noreply.github.com>"
```

## Create PR

The `create-pull-request` safe output packages changes into a draft PR.

In the PR body, include:
1. **Complete list of P0/P1/P2 items** with which file/section was updated
2. **Complete list of P3 items skipped** with reasoning
3. The release versions covered
