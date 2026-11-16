# FULL-PWNAGE-105100 — Deploy live, reboot, verify everything, then ship v0.8.5-beta

**Target:** live S10+ + GitHub repo `illdynamics/nuxel`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-105100.md` (and final roll-up in `REPORT-PWNAGE-104000.md`)
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Everything fixed must be **deployed live**, survive a **reboot**, and then be
released as **v0.8.5-beta**, building the **exact image currently running**.

## 1. Deploy

1. Ensure repo changes are complete and tests pass locally.
2. Deploy with the repo's deploy tooling (`scripts/nuxel-deploy-live.py`,
   `scripts/nuxel-live-install.py` — read `--help` and use the same path CI uses
   so the live image is reproducible from source).
3. Record the deployed identity:
   ```sh
   $SSH $PHONE 'cat /etc/nuxel/build-id /etc/nuxel/VERSION 2>/dev/null; \
     uname -r; sha256sum /boot/Image* 2>/dev/null' > evidence/pwnage-104000/release/build-identity.txt
   ```
   This identity must match the release artifact after the CI build.

## 2. Reboot + verify

Reboot only after all component checks pass pre-reboot, then re-run the full green
table from `full-pwnage-104000.md` §4. Evidence to
`evidence/pwnage-104000/post-reboot/`.

## 3. Release (follow FULL-PWNAGE-104000 §5 verbatim)

- Bump to `0.8.5-beta` everywhere (VERSION, profile.json, manifests, docs).
- Update README / CHANGELOG / RELEASE-NOTES / all docs.
- Branch `feature/v0.8.5-beta` → commit → push → PR → merge to `main`.
- Tag `v0.8.5-beta` on the merge commit on main and push.
- Trigger/monitor `.github/workflows/release.yml` with `gh run watch`.
- On failure: fix → PR → merge → retrigger → monitor. Repeat until green.
- Confirm the release artifact == live build identity.

## 4. Acceptance

- [ ] Live image == released image (build id / commit).
- [ ] Reboot verification table all green.
- [ ] GitHub release `v0.8.5-beta` published, run green, artifact attached.
- [ ] No secrets committed; branch merged; repo clean on main.
