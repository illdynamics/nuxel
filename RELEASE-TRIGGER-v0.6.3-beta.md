# Nuxel v0.6.3-beta — clean, branch-protection-compatible GitHub release

The `VERSION` file says `v0.6.3-beta`. Do not push directly to protected
`main`. There are two supported trigger routes, and they must not race.

## Preferred: PR merge automatically tags and publishes

From an existing **Git clone** of Nuxel (the downloadable ZIP has no `.git`):

```sh
git fetch origin --tags
git switch main
git pull --ff-only origin main
git switch -c release/v0.6.3-beta
# Copy the patched ZIP's tree into this clone, without overwriting .git,
# untracked personal files, build outputs or local secrets.
git add -A
git diff --cached --stat
git commit -m "release: Nuxel v0.6.3-beta S10+ fixes"
git push -u origin release/v0.6.3-beta
gh pr create --base main --head release/v0.6.3-beta --title "Nuxel v0.6.3-beta" --body "S10+ image, connectivity UI, dock and release fixes"
```

Review the PR and wait for required checks. Merge using GitHub's PR UI,
which is compatible with branch protection. GitHub's push-to-main Release
workflow sees a **new VERSION**, builds S10+ from the merge commit, validates
artifacts, creates the annotated `v0.6.3-beta` tag and publishes a **prerelease**.
An unchanged VERSION on a later merge does not overwrite that same release.

```sh
gh run list --workflow release.yml --branch main --limit 5
# Choose the actual run ID above, then:
gh run watch RUN_ID --exit-status
git ls-remote --tags origin 'refs/tags/v0.6.3-beta*'
gh release view v0.6.3-beta --json url,isDraft,isPrerelease,assets
mkdir -p /tmp/nuxel063
cd /tmp/nuxel063
gh release download v0.6.3-beta --pattern '*s10plus.tar.gz' --pattern SHA256SUMS.txt
sha256sum -c SHA256SUMS.txt
```

## Fallback: manually push the tag AFTER PR merge (only if no auto tag exists)

```sh
git fetch origin --tags
git switch main
git pull --ff-only origin main
cat VERSION   # exactly v0.6.3-beta
git ls-remote --tags origin 'refs/tags/v0.6.3-beta*'
# Only when the command above confirms the tag does not exist:
git tag -a v0.6.3-beta -m 'Nuxel v0.6.3-beta' "$(git rev-parse HEAD)"
git push origin refs/tags/v0.6.3-beta
```

Tag push triggers Release. Do **not** run `git push origin main` simply to
trigger a release: branch protection will reject it, and a tag is a separate
ref. Never force-push tags or rewrite an existing released tag.

If the tag already exists but the release did not publish, find and fix the
failing workflow rather than retagging. After fixing workflow on a *new*
version commit, tag the new version; or manually dispatch the existing workflow
for the existing tag if its workflow revision supports it:

```sh
gh workflow run release.yml --ref main -f tag=v0.6.3-beta -f devices=s10plus -f publish=true
```

This manual action never overrides existing release assets. On a protected tag
namespace, an admin must explicitly allow release automation to create version
tags. Under **Settings → Actions → General**, verify that workflow permissions
include **Read and write permissions**. Repository/organization policies may
restrict this or require a dedicated release GitHub App.

## Strict release gates

- Tag commit belongs to `main` (checked in prepare).
- Source `VERSION` matches exact tag (checked in prepare).
- Fresh Fedora 43 ARM64 S10+ image build and package tests finish green.
- `tools/verify-artifacts.sh` passes; no placeholder archive is published.
- Release includes S10+ `.tar.gz`, `SHA256SUMS.txt`, release notes.
- GitHub reports `isDraft=false`, `isPrerelease=true`.
- **A successful CI build does not verify physical Wi-Fi/speaker/device boot.**
