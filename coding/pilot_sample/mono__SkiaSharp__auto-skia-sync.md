
# Sync - Skia Upstream

Base milestone (current): `m${{ needs.pre_activation.outputs.current }}`.  
Target milestone: `m${{ needs.pre_activation.outputs.target }}`.  
Upstream ref (merge from): `${{ needs.pre_activation.outputs.upstream_ref }}` (google/skia) — `main` means the bleeding-edge tip.  
Base branch (SkiaSharp): `${{ needs.pre_activation.outputs.base_branch }}` — mono/skia base: `${{ needs.pre_activation.outputs.skia_base_branch }}`.  
Sync (head) branch: `${{ needs.pre_activation.outputs.head_branch }}` (same name in both repos).  
Release-line sync: `${{ needs.pre_activation.outputs.is_release }}`.

> **About the base branch.** Most syncs target `main` (the newest, in-development line) with
> `skiasharp` as the mono/skia base. When an older milestone is requested AND a matching
> `release/<major>.<milestone>.x` branch exists, this is a **release-line sync**: both PRs target
> that release branch instead (mono/skia base = the same `release/<major>.<milestone>.x` branch,
> which the release process guarantees exists). In that case `current == target`, so it is always a
> **bug-fix-only sync** — do NOT bump the milestone, soname, or nuget versions; only the upstream
> merge + `cgmanifest.json` commit hash change. Use the base/head branch values above everywhere
> instead of hardcoding `main`/`skiasharp`/`skia-sync/m{target}`.
>
> **`main` (tip) mode.** When the upstream ref above is `main` (head branch `skia-sync/main`), this is a
> **bleeding-edge sync from the very tip of upstream Skia** (google/skia `main` HEAD), not a `chrome/m<N>`
> milestone branch. It targets the newest line (`main`/`skiasharp`) and `current == target`, so it is
> **NOT a version bump** — keep the milestone, soname, and nuget versions unchanged. It may still include
> new APIs / binding changes (regenerate + build + test as normal), and a tip merge can be large and
> conflict-heavy because the submodule base is well behind google/skia main; resolve what you reasonably
> can and record anything unresolved under "items needing human attention".

**Read `.agents/skills/update-skia/SKILL.md` and follow Phases 2-10.** Notes specific to this automated workflow:

- **Phase 1 is pre-computed** (above). Skip it — but you still need to add the `upstream` remote
  and fetch the upstream ref `${{ needs.pre_activation.outputs.upstream_ref }}` (Phase 1 step 4) since Phase 5 depends on it.
  For every mode except `main` this is a `chrome/m${{ needs.pre_activation.outputs.target }}` milestone branch;
  for `main` (tip) mode it is google/skia's `main` HEAD (bleeding edge — may include new APIs/binding changes,
  but it is NOT a version bump, and the head branch is `skia-sync/main`).
- **First thing**: run `dotnet tool restore` (pre-agent-steps can't do this for the chroot).
- **Phase 4**: The parent base branch is `origin/${{ needs.pre_activation.outputs.base_branch }}` and the
  submodule base branch is mono/skia `${{ needs.pre_activation.outputs.skia_base_branch }}` — use these in
  place of `origin/main` / `skiasharp` for every step. The sync branch in BOTH repos is
  `${{ needs.pre_activation.outputs.head_branch }}`. Before creating a fresh branch, check if
  `origin/${{ needs.pre_activation.outputs.head_branch }}` already exists; if so, check it out — the
  pre-activation step already verified new upstream commits exist. Even when current == target there may
  be new upstream bug-fix commits — a matching milestone does NOT mean no work.
  **Skip Phase 4 step 5** (submodule SHA alignment) — the pre-agent step already aligned the submodule to
  the base branch's pointer (on mono/skia `${{ needs.pre_activation.outputs.skia_base_branch }}`).
  Branch from the current HEAD when creating the submodule feature branch in step 6.
- **Phase 6 (version files)**: For a release-line sync (`is_release == true`, so `current == target`) this is a
  bug-fix-only sync — keep the release line's milestone/soname/nuget versions unchanged; the only expected
  parent-repo change is `cgmanifest.json`'s commit hash. Do NOT advance the milestone.
- **Build platform**: use Linux x64 (`dotnet cake --target=externals-linux --arch=x64`). Clang is pre-configured via env vars.
  This also applies to Phase 10 if a native rebuild is needed.
- **Native build environment is fully provisioned by the workflow** (clang, `libc++-dev`/`libc++abi-dev`,
  fontconfig, ninja). Do NOT modify any native build files (`native/**/build.cake`, `scripts/infra/native/**`)
  and do NOT change compiler/linker flags (e.g. `-stdlib=libc++`) to work around a build error. You also CANNOT
  install packages (no apt/sudo inside the sandbox, and the firewall blocks OS package mirrors). If a native
  build genuinely fails because a dependency is missing from the host, that is a workflow bug: STOP, do not hack
  the build, and record it in the mono/SkiaSharp summary under "items needing human attention" so the
  `Install native build dependencies` step can be fixed.
- **NEVER run `externals-download`** in this workflow — not even for debugging or baseline comparison. Build from source only.
- **Phase 9 reminder**: a green C# build is NOT sufficient - run the new-function diff check from Phase 9 step 1.
- **Phase 11 — do NOT execute it.** Replace it entirely with the file writes below.
  Do NOT push branches, create PRs, or create issues — all GitHub artifacts are handled by the post-step.
  Just commit locally. Do NOT call `create_issue` or `create_pull_request`.
- **"No work" signal**: the pre-activation step skips the workflow when there are no new upstream commits,
  so this should not happen. If somehow it does, do NOT write `skia-sync-env.sh` and stop.

After Phase 10, write these files:

1. `/tmp/gh-aw/agent/skia-sync-env.sh` — **required** for the post-step to know what to push:
   ```bash
   mkdir -p /tmp/gh-aw/agent
   cat > /tmp/gh-aw/agent/skia-sync-env.sh << EOF
   TARGET=${{ needs.pre_activation.outputs.target }}
   CURRENT=${{ needs.pre_activation.outputs.current }}
   UPSTREAM_REF=${{ needs.pre_activation.outputs.upstream_ref }}
   IS_RELEASE=${{ needs.pre_activation.outputs.is_release }}
   BASE_BRANCH=${{ needs.pre_activation.outputs.base_branch }}
   SKIA_BASE_BRANCH=${{ needs.pre_activation.outputs.skia_base_branch }}
   HEAD_BRANCH=${{ needs.pre_activation.outputs.head_branch }}
   EOF
   ```

2. `/tmp/gh-aw/agent/skia-sync-skia-summary.md` - for the mono/skia PR:
   - Upstream merge details, conflicts resolved, C API fixes, items needing human attention

3. `/tmp/gh-aw/agent/skia-sync-skiasharp-summary.md` - for the mono/SkiaSharp PR:
   - Breaking change analysis, version/binding updates, C# changes, build/test results, items needing human attention

All files written to `/tmp/gh-aw/agent/` are automatically uploaded as workflow artifacts.
Write test output there too (`/tmp/gh-aw/agent/test-output.txt`) so failures can be inspected after the run.

Commit submodule changes inside `externals/skia` on `${{ needs.pre_activation.outputs.head_branch }}`.
Commit parent repo changes on `${{ needs.pre_activation.outputs.head_branch }}` in the parent.
