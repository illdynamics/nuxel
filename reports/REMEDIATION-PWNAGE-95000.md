# REMEDIATION — NUXEL PWNAGE-95000

**Audit:** PWNAGE-95000  
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`) at `192.168.178.167`  
**Audit verdict:** `PARTIALLY_DEPLOYED`  
**Remediation status:** **PROPOSED ONLY — no remediation was executed during this audit.**  
**Machine-readable plan:** `evidence/pwnage-95000/PWNAGE-95000-REMEDIATION.csv` (3,069 non-verified rows)

---

## 0. Authorization and safety boundary

The audit phase is complete. No deployment, reboot, service restart, package re-signing, configuration overwrite, commit, flash, kernel write, firmware write, partition write or user-data change was performed.

The remediation below is ordered by risk. P0 items are reversible userspace/provenance fixes. Hardware/blocked items must remain fail-closed and must not be attempted as a blind bulk redeploy.

Before any P0 execution:

1. Preserve the current working tree and a copy of the current live payload.
2. Do not run `git reset --hard`, `git clean -fd`, or overwrite unrelated modified/untracked files.
3. Use the existing canonical deployment scripts, not a new parallel workflow.
4. Re-run file hashes and service checks after every scoped change.
5. Keep the existing p93/p94 backups and `/root/p94/installed-20261108T173717.list`.

---

## 1. P0 — Critical provenance and integrity fixes

### P0-1 — Commit PWNAGE-93000/94000 source before any rebuild

**Original IDs:** PWNAGE-93000, PWNAGE-94000  
**Affected requirement groups:** `PWNAGE-93000-REQ-*`, `PWNAGE-94000-REQ-*`  
**Observed state:** deployed, but 34 modified + 53 untracked working-tree paths; no P93/P94 commit exists.  
**Root cause:** implementation and deployment were done from the dirty worktree without committing the source or adding the new files.

**Required action:**

- Selectively stage only the intended P93/P94 files, preserving unrelated user changes.
- Include at minimum:
  - `pwa/nuxel-home/{index.html,manifest.json,sw.js,css/status-bar.css,css/style.css}`
  - `pwa/nuxel-home/js/{app.js,apps.js,status-bar.js,qs.js,immersive.js,topbar-machine.js,bridge.js,gestures.js,navigation.js}`
  - `pwa/nuxel-apps/doom/{index.html,js/doom.js,tests/test-doom.js}`
  - `services/nuxel-bridge/src/api.py`
  - `services/nuxel-notifications/src/notifications.py`
  - `tools/s10plus/a45/{nuxel-session.sh,nuxel-pwa-host.c,nuxel-statusbar.c,nuxel-navdock.c}`
  - `tools/s10plus/a59/nuxel-foreign-toplevel.c`
  - `tools/s10plus/a33/doom-engines/nuxel-doom-engine`, `tools/s10plus/a33/nuxel-crispy-doom`
  - `configs/nuxel/gtk/`, `configs/nuxel/dconf/`, `configs/nuxel/flatpak/`
  - `tools/pwnage93000/`, `tools/pwnage94000/`, `tests/pwnage93000/`, `tests/pwnage94000/`

**Dependencies:** none.  
**Risk:** MEDIUM — accidental staging of unrelated user reports/screenshots. Use explicit paths, not `git add -A`.  
**Verification:** `git diff --cached --stat`; confirm only intended files; run P93/P94 tests.  
**Rollback:** `git restore --staged <paths>` (does not touch working tree).

### P0-2 — Re-sign/restage the live NuXtore Doom bundle

**Original IDs:** PWNAGE-94000 / PWNAGE-63000  
**Affected requirement groups:** Doom/NuXtore packaging and integrity requirements.  
**Observed state:** live `nuxtore-verify.py` exits 1 with `INTEGRITY FAILURE`; Doom bundle expects old digests.

| File | Bundle digest | Live/current digest |
|---|---|---|
| `pwa/nuxel-apps/doom/index.html` | `c500c861d30c…` | `d382047d970b…` |
| `pwa/nuxel-apps/doom/js/doom.js` | `44acef38cbd8…` | `eb7e1e3ab0b6…` |

**Required action:**

1. Rebuild/restage the `org.nuxel.Doom-2.0.0` bundle from the committed 94000 files.
2. Re-sign the catalog with the existing dev signing key (`nuxel-beta-dev-2026`); do not print secret material.
3. Deploy the corrected bundle/catalog through the existing deployment path.
4. Verify both repository and live:
   - `python3 pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py`
   - live `/usr/share/nuxel/pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py`
   - both must exit 0 with no `DIGEST_MISMATCH`.

**Dependencies:** P0-1 (commit the exact Doom files first).  
**Risk:** MEDIUM — wrong signing key or partial bundle would worsen integrity state. Back up `catalog/` first.  
**Verification:** verifier exit 0; NuXtore Doom install/launch/catalog status from Settings/NuXtore.  
**Rollback:** restore the backed-up `nuxtore/catalog/` directory and restart only the bridge/NuXtore-facing services.

### P0-3 — Create a truthful deployment manifest and fix version surfaces

**Observed state:**

- `/usr/share/nuxel/VERSION` = `v0.7.9-beta`
- PWA/bridge = `0.8.1-beta`
- no `/etc/nuxel-version`
- no per-deployment commit/build manifest

**Required action:**

- Extend the canonical payload/deploy mapping to install `/usr/share/nuxel/VERSION` from the repository `VERSION` (or install a generated build descriptor).
- Record at least: project, build ID, Git commit, branch, build timestamp, deployment script, target device, component hashes.
- Keep the existing per-file SHA-256 plan and rollback directory.
- Make the post-deploy check fail if `VERSION`, `pwa_version`, `host_version` and the deployment manifest disagree.

**Dependencies:** P0-1.  
**Risk:** LOW for a metadata-only manifest; MEDIUM if modifying the canonical installer without tests. Add host tests first.  
**Verification:** deploy dry run; compare all version surfaces; read back manifest on phone.  
**Rollback:** restore the prior `/usr/share/nuxel/VERSION`, installer, and manifest; no service or data impact.

### P0-4 — Regenerate the canonical live payload from the committed tree

**Observed state:** on-disk `build/out/s10plus/nuxel-v0.8.1-beta-live-userspace.tar.gz` is stale (`2f18ddf1…`, 421 files, 11:05) and predates p93/p94.

**Required action:**

1. Build with `tools/s10plus/a43/package-live.py`.
2. Verify with `tools/s10plus/a43/verify-live.py`.
3. Record the exact payload SHA-256 and file count.
4. Compare every target before deployment; expect 423 targets and 423 matching target bytes for a clean deploy (the current test file mismatch is not runtime-critical but should be resolved by P0-1/P1-3).
5. Deploy only through `scripts/nuxel-deploy-live.py --user root --apply` after review.

**Dependencies:** P0-1, P0-2, P0-3.  
**Risk:** MEDIUM — restart set includes `nuxel-bridge`, `nuxel-http-bridge`, `nuxel-soundd`, `nuxel-clockd`; preserve rollback. Do not include kernel/boot/firmware.  
**Verification:** 423/423 canonical targets match; services active; notification hub, icon resolver and PWA endpoints respond; device stays on USB/WiFi recovery paths.  
**Rollback:** `scripts/nuxel-live-install.py` created per-stamp rollback; do not delete it.

---

## 2. P1 — Verification and release-input fixes

### P1-1 — Resolve launcher lifecycle test discrepancies

**Observed failures:**

- `Home backgrounds the frame and returns to the launcher`
- `activation leaves exactly one visible app surface`

**Required action:** instrument the real launcher and the test DOM harness; determine whether the P94 inline `!important` visibility helper or the harness is at fault. Do not change live lifecycle semantics merely to satisfy an outdated test. Add a live evidence probe that reports frame count, hidden state, `display`, `visibility`, `pointer-events`, and active session after background and after switching apps.

**Verification:** launcher registry suite green; live P94 cycle evidence still 20/20 with no input offenders.

### P1-2 — Reconcile the P93 notification-placement test with the P94 level model

`tests/pwnage93000` currently fails 1/14 because it expects `notifications.hidden = !on`; PWNAGE-94000 uses the one-owner level machine (`0..3`) and gates the list at `EXTENDED`. Update the P93 assertion or add a compatibility surface only if live notification placement regressed.

### P1-3 — Reconcile stale historical test suites

The audit found stale assumptions in `pwnage31000`, `pwnage33000`, `pwnage37000`, `pwnage40000`, `pwnage46000`, `pwnage49000`, `pwnage52000`, `pwnage60000`, `pwnage82000` and non-collectable test directories. Triage each as:

- intentional architectural change → update test;
- real defect → fix source;
- obsolete suite → retire with a dated note.

Do not mark the suite green by weakening a safety assertion.

### P1-4 — Synchronize release GPU assets

`release/s10plus/gpu/nuxel-session.sh` is stale. Re-run the repository’s GPU release sync and verify all `release/s10plus/gpu/SHA256SUMS` entries.

### P1-5 — Human physical acceptance

Owner-only tests still pending:

- one-finger Back/Home/drawer and Quick Settings gestures;
- notification swipe read/archive;
- speaker audibility and Doom SFX;
- lockscreen unlock/lock;
- landscape app -> Home restoration;
- Doom touch HUD feel;
- VNC/RDP direct LAN acceptance if remote access is desired.

Record YES/NO outcomes; do not infer human success from process state.

---

## 3. P2 — Blocked hardware/subsystem remediation

These are not safe blind redeploy candidates. Keep their fail-closed states.

| Area | Current status | First required action | Reversible? |
|---|---|---|---|
| Camera | `BLOCKED_FIRMWARE` | Obtain lawful sensor setfiles/ISP/calibration and implement/validate FIMC-IS pipeline; separate kernel/DT work if required | No userspace-only complete fix |
| Satellite GNSS | `BLOCKED_FIRMWARE` | Obtain exact BCM4773 BBD patch and implement native BBD/LHD runtime; verify outdoor receiver fix | Firmware/system-image work required |
| NFC | `BLOCKED_KERNEL` / physical | Decide native `/dev/sec-nfc` protocol vs kernel NFC class; verify one physical NDEF tag | Kernel or vendor transport work |
| Fingerprint | `BLOCKED_SECURE_PROVIDER` | Obtain lawful TEE-backed qbt2000 provider; never fake match | Secure-world/vendor material required |
| Auto-rotation | `BLOCKED_VENDOR_RUNTIME` | Restore SSP/BBD sensor-hub runtime; prove non-zero accelerometer samples | Vendor runtime/firmware work |
| MFC decode | `BLOCKED` | Land patched kernel + matching `mfc_fw.bin`; prove one real decode | Kernel/firmware/boot work; requires explicit approval |
| DP Alt Mode / HDMI / casting | `BLOCKED` / not implemented | Determine whether DRM/DP connector can be exposed; build NuXtream only after real capture/encode/receiver proof | Kernel/product work |
| Cellular | `BLOCKED_FIRMWARE`/host transport | Native Shannon CP transport + ModemManager plugin; owner SIM and radio test | Kernel/userspace work |

---

## 4. P3 — Housekeeping and future prompts

1. Give the new NEXUS+NEO prompts unique IDs; do not reuse `12000`.
2. Decide whether `10000`, `11000`, `12000` and `96000` are current work; they are untracked and unimplemented as of this audit.
3. Add a release-check that fails if the checked-in release copy diverges from canonical source.
4. Add a deployment provenance check that fails if Git commit, build ID, payload hash and VERSION disagree.
5. Retain all existing rollback directories; do not clean `/var/lib/nuxel/live-deploy`, `/var/backups/nuxel`, `.nuxel-rollback-p93-*`, `.nuxel-rollback-p94-*`, or `/root/p94`.

---

## 5. Verification matrix for remediation

| Check | Pass condition |
|---|---|
| Repository | P93/P94 files committed; no unrelated user work lost |
| Build | Current payload builds and verifies; hash and commit recorded |
| Version | `/usr/share/nuxel/VERSION`, PWA manifest, status bar and bridge all agree |
| Deployment | 423/423 canonical targets match installed bytes |
| NuXtore | live `nuxtore-verify.py` exits 0; Doom bundle signed |
| Services | bridge/http/notifications/wayland/wl-fb/soundd/clockd/web active; no failed units |
| Recovery | WiFi SSH and CDC-ACM serial preserved |
| UI | touch/Back/Home/drawer/QS/notifications/sound accepted by owner |
| Hardware | each blocked feature remains explicitly BLOCKED/OFF until physical proof |

---

## 6. Rollback rules

- P0 source commit: use normal Git revert; never reset the user’s worktree.
- P0 payload: use the stamp-specific `/var/lib/nuxel/live-deploy/rollback-<stamp>/` tree created by `nuxel-live-install.py`.
- P0 NuXtore: restore the prior catalog directory from a scoped backup and restart only the NuXtore/bridge surface.
- P0 version/manifest: restore the prior metadata files; no service impact.
- P1/P2: use the task-specific rollback script or previous slot/backup. Do not roll back a kernel/boot change without an explicit recovery plan.

