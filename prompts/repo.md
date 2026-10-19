# NUXEL — v0.5.3-alpha REPO & GITHUB WORKFLOW UPDATE 🐧

You are Cyber-Tiel 35B, working on the existing Nuxel repository at `~/x/nuxel`.

**Your mission: Update the entire repository to `v0.5.3-alpha` and ensure the GitHub Actions S10+ release workflow builds the latest Nuxel images correctly.**

## Tasks

1. **Audit current source:** Inspect the latest S10+ build scripts, kernel/BOOT configuration, Fedora rootfs builder, and current userspace. Preserve all recent fixes.
2. **Fix GitHub Actions:** Update `.github/workflows/release.yml` so a clean GitHub runner builds the latest S10+ BOOT image and Fedora ARM64 rootfs, including all current launcher, touchscreen, WebKitGTK, Phoc, services, and application changes.
3. **Version bump:** Update `VERSION`, `README.md`, `CHANGELOG.md`, package metadata, current documentation, and relevant release manifests to **`v0.5.3-alpha`**. Preserve historical changelogs and test evidence.
4. **Verify artifacts:** Run available tests and build checks. Verify architecture, BOOT structure, rootfs contents, latest userspace files, and SHA-256 checksums. Fix any failures.
5. **Git:** Review changes, then `git add`, commit, and push to the appropriate branch. Create and push the `v0.5.3-alpha` tag only after required checks pass.
6. **Release:** Trigger/monitor GitHub Actions and publish the `v0.5.3-alpha` GitHub prerelease with verified artifacts. Do not publish if builds fail.

## Important rules

- Work from the **latest current source**, not obsolete A32/A34 copies.
- Preserve the existing working Samsung BOOT configuration.
- Fix the known double-`v` tag issue (`vv0.5.3-alpha`).
- Do not flash the phone, modify partitions, or rewrite unrelated components.
- Do not claim images were physically boot-tested merely because CI passes.
- Continue implementing and testing; don't stop after writing a plan.
- If GitHub access or CI is blocked, report the exact blocker without claiming success.

**Final deliverables:** Updated repository, consistent `v0.5.3-alpha` versioning, working S10+ release workflow, committed/pushed changes, verified build artifacts, and GitHub prerelease URL.

**EXECUTE NOW — NUXEL v0.5.3-alpha! 🐧🔥**
