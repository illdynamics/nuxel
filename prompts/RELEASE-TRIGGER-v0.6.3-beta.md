# Nuxel v0.6.3-beta — PR-only GitHub release

`VERSION` is `v0.6.3-beta`. **The release flow runs only when a pull request is
merged into `main`.** `main` is protected and requires a PR. Tag pushes and
direct pushes do not trigger it.

## Release route

```sh
git switch -c release/v0.6.3-beta
git add -A
git commit -m "release: Nuxel v0.6.3-beta"
git push -u origin release/v0.6.3-beta
gh pr create --base main --head release/v0.6.3-beta \
  --title "Nuxel v0.6.3-beta" \
  --body "S10+ image, A44 launcher/metrics fixes, Wi-Fi UI and PR-only release flow"
```

Merge the PR with GitHub's UI or:

```sh
gh pr merge --merge --delete-branch
```

The resulting push to `main`:

1. resolves `VERSION` to `v0.6.3-beta`;
2. builds the S10+ boot image and Fedora 43 ARM64 phone rootfs from the merge
   commit, including the A34 userspace, A40/A44 metrics daemon and A44 PWA;
3. builds and verifies the hash-manifested live userspace payload;
4. runs the A33/A34/A40 regression suites and the strict artifact gates;
5. creates the annotated `v0.6.3-beta` tag on that exact commit; and
6. publishes a GitHub **prerelease** with the device archive, live payload,
   `SHA256SUMS.txt` and release notes.

A merge that does not change `VERSION` is skipped rather than rebuilding or
overwriting an existing release.

## Verify

```sh
gh run list --workflow release.yml --branch main --limit 5
gh run watch RUN_ID --exit-status
git ls-remote --tags origin 'refs/tags/v0.6.3-beta*'
gh release view v0.6.3-beta --json url,isDraft,isPrerelease,assets
mkdir -p /tmp/nuxel063 && cd /tmp/nuxel063
gh release download v0.6.3-beta --pattern '*s10plus.tar.gz' --pattern SHA256SUMS.txt
sha256sum -c SHA256SUMS.txt
```

## Manual recovery only

If the automatic run failed after a valid merge, dispatch the workflow against
`main`. This does not make tag pushes a trigger and does not overwrite a release
that already exists:

```sh
gh workflow run release.yml --ref main -f devices=s10plus -f publish=true
```

## Strict release gates

- Trigger is a push to `main`, which branch protection only permits via a
  merged pull request.
- Source `VERSION` matches the tag (`v0.6.3-beta`).
- Fresh S10+ boot image + Fedora 43 ARM64 rootfs build finishes green.
- Rootfs contains the exact source bytes for the A44 Home PWA, bridge, metrics
  units/daemon, configuration and current A34 userspace binaries.
- The live userspace payload hash manifest verifies and includes the A44
  system-monitor and navigation fixes.
- `tools/verify-artifacts.sh --device s10plus` passes; no placeholder archive is
  published.
- Release is a prerelease with the S10+ archive, `SHA256SUMS.txt` and notes.
- **A successful CI build does not verify physical Wi-Fi/speaker/device boot.**
