# REPORT — NUXEL PWNAGE-95000

## Master historical PWNAGE audit · live S10+ deployment verification · Git traceability

**Audit ID:** PWNAGE-95000  
**Repository:** `/Users/wicked/x/nuxel` (`illdynamics/nuxel`)  
**Branch / HEAD:** `main` / `bd798f7f6c18e454921573251e02a7ac52e8da7c`  
**Worktree at audit:** `v0.8.1-beta-4-gbd798f7f-dirty` — 34 modified + 53 untracked paths  
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**SSH:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167`  
**Audit date:** 2026-11-08 (Europe/Amsterdam)  
**Mode:** audit first; no deployment, no reboot, no kernel/boot/firmware/partition write performed.

---

## A. Overall result

**`AUDIT_COMPLETE`**

The historical prompt inventory, source/Git traceability, deployment-script review, live-device inspection, file/hash comparison, runtime checks and remediation inventory are complete. Behaviour that requires a human finger, ear, physical tag, SIM, camera scene or external display remains explicitly unverified rather than assumed.

## B. Device deployment verdict

**`PARTIALLY_DEPLOYED`**

The live S10+ is running the current working-tree userspace for PWNAGE-93000/94000 and the earlier 0.8.1 release surface: 422 of 423 canonical payload targets match byte-for-byte. The current installation is functional and all Nuxel services checked are active, but the historical set contains large hardware-blocked areas, several old tasks have no full specification, and the most recent work is **not committed**. The device is therefore not in a state where every historical requirement can be called `VERIFIED_LIVE`.

## C. Key numbers

| Measure | Result |
|---|---:|
| Historical unique PWNAGE IDs found (excluding 95000) | **82** |
| Unique tasks with a Kickstarter | **77** |
| Unique tasks with a full specification | **60** |
| Complete Kickstarter + full-spec pairs | **54** |
| Kickstarter-only tasks | **22** |
| Full-spec-only tasks | **5** |
| Conflicting/reused ID versions | **1** (`12000`) |
| Current prompt files found | 87 Kickstarter files, 66 full-spec files (duplicates included) |
| Atomic requirement units extracted | **3,220** |
| Requirement units marked `VERIFIED_LIVE` | **151** (3 tasks, task-level inheritance) |
| Requirement units `PARTIALLY_DEPLOYED` | **1,954** (29 tasks) |
| Requirement units `DEPLOYED_UNVERIFIED` | **620** (15 tasks) |
| Requirement units `BLOCKED` | **435** (9 tasks) |
| Requirement units `NOT_IMPLEMENTED` | **53** (3 tasks) |
| Requirement units `SPEC_INCOMPLETE` | **7** (1 conflicting task; 22 kicker-only tasks have no extractable full requirements) |
| Confirmed live regressions | **1** (NuxTore Doom package digest/signature mismatch) |
| Unresolved test/behaviour discrepancies | **3** (2 launcher-registry checks, 1 P93 notification-position check) |

These counts are generated from the historical task inventory. Requirement status is inherited from the strongest task-level evidence, not independently re-tested for every checkbox. The complete per-requirement rows are in `evidence/pwnage-95000/PWNAGE-95000-REQUIREMENTS.csv` and the remediation rows in `evidence/pwnage-95000/PWNAGE-95000-REMEDIATION.csv`.

---

## 1. Executive summary

1. **The S10+ is reachable with the required key and strict host-key verification.** The connected device is the intended Samsung BEYOND2LTE / Exynos 9820 board, Fedora Linux 43 aarch64, kernel `4.14.253-gf7194c1d15ed-dirty`, running as root. The ED25519 host fingerprint is `SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs`, matching the host `known_hosts` entry and the repository’s pinned `nuxel-s10plus` key.
2. **Most current userspace code is genuinely on the phone.** A fresh canonical payload built from the working tree (`79f013bb…`) contains 422 files mapping to 423 targets. **422 targets match the installed bytes; one non-runtime test file differs** (`pwa/nuxel-apps/doom/tests/test-doom.js`).
3. **PWNAGE-93000 and PWNAGE-94000 are deployed but not committed.** Their PWA, bridge, notification, session, native helper, GTK/dconf/Flatpak and Doom changes exist as modified/untracked working-tree files. The live hashes and p94 native binaries match the deployed staging set.
4. **The “built” live payload is stale.** `build/out/s10plus/nuxel-v0.8.1-beta-live-userspace.tar.gz` (11:05, hash `2f18ddf1…`, 421 files) predates the 12:27 p93 and 17:37 p94 deployments. The current source-derived payload is `79f013bb…` with 422 files. A fresh deployment from the stale artifact would lose the recent work.
5. **Canonical deployment-record history stops before p93/p94.** `/var/lib/nuxel/live-deploy` records only six `COMMITTED` stamps ending at `20261108T100546Z`. PWNAGE-93000 uses `.nuxel-rollback-p93-*`; PWNAGE-94000 uses `/root/p94/installed-20261108T173717.list` and `.nuxel-rollback-p94-*`. This is real deployment evidence, but it is outside the canonical manifest/trace path.
6. **Version surfaces disagree.** `/usr/share/nuxel/VERSION` says `v0.7.9-beta`; the PWA manifest, status bar and HTTP bridge say `0.8.1-beta`. No `/etc/nuxel-version` exists. A deployment can therefore appear older than the running code depending on which file is inspected.
7. **The live NuxTore catalog fails integrity verification.** `/usr/share/nuxel/pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py` exits 1 with `INTEGRITY FAILURE`: the Doom 2.0.0 bundle lists old `index.html` and `js/doom.js` digests, while the deployed 94000 versions differ. This is a confirmed package-integrity regression caused by changing Doom files without re-signing/restaging the catalog.
8. **Recent live behaviour is strong but not fully human-verified.** PWNAGE-94000 source checks pass 93/93; its device evidence shows 20/20 Back cycles with `bad: []` and `geometry_failures=0`. Human finger sweeps, human listening, Doom music, and a true landscape desktop cycle remain unverified. PWNAGE-93000’s notification hub, badge/read/archive API and icon resolver are live; its physical gesture acceptance is still pending.
9. **Older work is substantially present but unevenly auditable.** Many 30000–92000 features are committed in release history and still present in the live userspace. Hardware-dependent areas (camera, satellite GNSS, NFC tag I/O, fingerprint, sensor-hub auto-rotation, MFC decode, DP Alt Mode/casting, cellular) remain blocked and must not be called deployed-working.
10. **New prompts appeared during the audit.** Untracked `10000`, `11000`, `12000` and `96000` prompt files were created at 18:06/18:40 on the audit date. They are inventoried, but they cannot be historical deployed work. ID `12000` also collides with the older SnekByte prompts, so the ID is not unambiguous.

---

## 2. Live device findings

### 2.1 Identity and access

| Check | Evidence |
|---|---|
| SSH command | `ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167` |
| Host key verification | Strict verification remained enabled; ED25519 `SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs` matched `~/.ssh/known_hosts` and the repo pin |
| Effective user | `uid=0(root) gid=0(root)` |
| Device model | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` |
| Architecture | `aarch64` |
| Kernel | `4.14.253-gf7194c1d15ed-dirty #5 SMP PREEMPT Sun Nov 1 13:38:15 CET 2026` |
| OS | Fedora Linux 43 (Forty Three) |
| Init | `/usr/lib/systemd/systemd` |
| Boot ID | `38d9b9ef-61de-4aee-ab57-c569d3ab6948` |
| Root filesystem | `/dev/sda31 ext4 rw,relatime,seclabel,errors=remount-ro` |
| Storage | 111 GiB total, 35 GiB used, 72 GiB available (33%) |
| Memory | 7.2 GiB total, ~3.6 GiB used, no swap |

### 2.2 Version and build identity

| Surface | Live value |
|---|---|
| `/usr/share/nuxel/VERSION` | `v0.7.9-beta` — **stale relative to running code** |
| `/etc/nuxel-version` | absent |
| `pwa/nuxel-home/manifest.json` `nuxel.pwa_version` | `0.8.1-beta` |
| `pwa/nuxel-home/js/status-bar.js` | `VERSION = '0.8.1-beta'` |
| `pwa/nuxel-common/bridge-version.json` | `host_version = 0.8.1-beta`, protocol `1` |
| HTTP bridge `/api/v1/health` | `version = 0.8.1-beta`, `bridge_version = 1` |
| Git HEAD | `bd798f7f6c18e454921573251e02a7ac52e8da7c` |
| Worktree | dirty: 34 modified, 53 untracked paths |

### 2.3 Services and runtime

`systemctl --failed` returned no failed units. Active Nuxel/session services included:

`nuxel-bridge`, `nuxel-http-bridge`, `nuxel-web`, `nuxel-notifications`, `nuxel-soundd`, `nuxel-clockd`, `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-button-manager`, `nuxel-orientationd`, `nuxel-geoclue-agent`, `nuxel-haptics`, `nuxel-nfcd`, `nuxel-portal`, `nuxel-touch-arm`, `nuxel-usb-mode-monitor`, `nuxel-watchdog-keep`, `nuxel-audio-session`, `seatd`, and NetworkManager.

Current live process/implementation checks:

- Phoc: `phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini -E /usr/lib/nuxel/nuxel-session.sh`
- PWA host: `/usr/lib/nuxel/nuxel-pwa-host`
- Native chrome: `nuxel-statusbar`, `nuxel-navdock`, `nuxel-osd`, `nuxel-foreign-toplevel`
- Display bridge: exactly one `/dev/fb0` writer, `nuxel-wl-fb`; state `FRAMES_OK`, `decon_pan_failed=0`, panel 1440×3040, CPU framebuffer presenter.
- Graphics: `ACCELERATED_SHM` / `GPU-RENDERED / SHM-PRESENTED`; Mali-G76 via `mali_kbase`, Phoc has 3 `/dev/mali0` FDs, 0 llvmpipe threads. WebKit DMA-BUF/zero-copy remains blocked.
- Notification hub: `org.nuxel.Notifications` owned by PID 5393 on the system bus; `org.freedesktop.Notifications` present on the root compositor session bus.
- Notification RPC: `active=2, unread=2, read=0, archived=5, total=7`; list/history/counts all return `success:true`.
- Sound mode: `normal`, source `/var/lib/nuxel/audio/sound-mode`.
- Icon resolution: `/api/v1/apps/icon/org.gnome.FileRoller` returns HTTP 200, `image/svg+xml`, 13,235 bytes.

### 2.4 Recent deployment evidence on the phone

- Canonical live-deploy records:
  - `rollback-20261108T002014Z`
  - `rollback-20261108T074112Z`
  - `rollback-20261108T094657Z`
  - `rollback-20261108T095232Z`
  - `rollback-20261108T100229Z`
  - `rollback-20261108T100546Z`
- PWNAGE-93000 backups: hundreds of `.nuxel-rollback-p93-*` files, latest in the audit at `20261108T125251`.
- PWNAGE-94000 install manifest: `/root/p94/installed-20261108T173717.list` (46 entries); 45 files carry `.nuxel-rollback-p94-20261108T173717` backups.
- p94 staged source and installed files matched exactly for all checked PWA, bridge, session, Doom and GTK/dconf/Flatpak files.
- p94 native build outputs matched installed binaries exactly:
  - `nuxel-foreign-toplevel`
  - `nuxel-navdock`
  - `nuxel-statusbar`
  - `nuxel-pwa-host`

---

## 3. Deployment infrastructure findings

### 3.1 Canonical live userspace path

`scripts/nuxel-deploy-live.py` is the current authoritative userspace deploy entry point:

1. Builds a hash-manifested payload with `tools/s10plus/a43/package-live.py`.
2. Verifies it with `tools/s10plus/a43/verify-live.py`.
3. Maps repository sources to phone targets.
4. Uploads one staging tarball and the installer.
5. Runs `scripts/nuxel-live-install.py` on the phone.
6. Verifies critical files/services after installation.

`scripts/nuxel-live-install.py` is userspace-only, validates every target against an allowlist, backs up replaced files under `/var/lib/nuxel/live-deploy/rollback-<stamp>/`, installs atomically, checks hashes, reloads systemd, restarts configured services, and rolls back on service-health or firewall-import failure.

Important limits found:

- The canonical payload does **not** install `/usr/share/nuxel/VERSION`, so the stale version file survives deployments.
- The canonical mapping writes PWA files to `/usr/share/nuxel/pwa/...`. The 93000/94000 task scripts also maintain a second `/usr/share/nuxel/nuxel-home/...` tree; canonical deploy alone does not reconcile that second tree.
- The canonical app does not record a commit/build ID or a manifest per deployment. `/var/lib/nuxel/live-deploy` contains backups plus a `COMMITTED` stamp, not provenance.
- The canonical CLI defaults to `--user nuxel`; the required audit connection is root. `--user root` is therefore needed when invoking it for this device.
- No canonical deployment was run during this audit; the payload was built and verified locally, then compared read-only against the device.

### 3.2 Existing scripts by role

| Role | Script(s) | Assessment |
|---|---|---|
| Complete OS build | `images/build.sh`, `Makefile`, kernel/rootfs builders | Build pipeline; not a live-update mechanism |
| Complete OS flash | `scripts/nuxel-adb-flash-pack/*` | Destructive ADB/TWRP BOOT+USERDATA flasher; emergency/legacy, not for this audit |
| Boot image repair | `scripts/fix-boot.sh` | Legacy boot-image mutation; do not run during userspace audit |
| Canonical live userspace deploy | `scripts/nuxel-deploy-live.py`, `scripts/nuxel-live-install.py` | Authoritative userspace path |
| Payload build/verify | `tools/s10plus/a43/package-live.py`, `verify-live.py` | Build + manifest verification |
| Per-task deploy, current | `tools/pwnage93000/*`, `tools/pwnage94000/*` | Deployed p93/p94; have per-task backups but bypass canonical manifest |
| Per-task deploy, historical | `tools/pwnage62000`, `63000`, `80000`, `90000`, `tools/s10plus/a61`, `a64`, `a65`, `a67`, etc. | Historical/subsystem deployments with per-task rollback |
| Legacy serial live deploy | `tools/beta/live/nuxel-live-deploy.py`, `scripts/s10plus-debug-pack/nuxel-live-deploy.sh` | Superseded for routine SSH userspace work by canonical SSH deploy |
| Device discovery | `scripts/nuxel-find-device.sh` | Read-only LAN/serial discovery |
| Diagnostics | `scripts/s10plus-debug-pack/*` | Read-only bootloop/ADB/TWRP/serial diagnostics |
| Remote desktop host | `scripts/nuxel-gui-tunnel.sh` | Pinned-key SSH forwarding for VNC/RDP |
| MTP/scrcpy host | `scripts/nuxel-mtp-openmtp.sh`, `scripts/nuxel-scrcpy.sh` | Host-side helpers; scrcpy correctly refuses native Nuxel |
| Rollback | canonical installer rollback; per-task `rollback-*.sh` | Present but fragmented across mission-specific scripts |
| Reporting | `scripts/generate-nuxel-feature-matrix.py` and matrix data | Feature matrix generation; not deployment proof |

### 3.3 Build and artifact traceability

| Artifact | Timestamp | Hash / size | Finding |
|---|---|---|---|
| `build/out/s10plus/nuxel-v0.8.0-beta-live-userspace.tar.gz` | 2026-11-08 10:46 | `5773ffa6…`, 14,214,356 B | Historical payload |
| `build/out/s10plus/nuxel-v0.8.1-beta-live-userspace.tar.gz` | 2026-11-08 11:05 | `2f18ddf1…`, 14,335,492 B, 421 files | **Stale**: predates p93/p94 |
| Current source-derived payload | audit run | `79f013bb…`, 422 files | Matches live userspace except one test file |
| Current live bridge/Home surface | live | `0.8.1-beta` | Running newer code than `VERSION` |

The release GPU asset copy is also stale: `tests/pwnage60000/test_gpu_manifest.py` reports `release/s10plus/gpu/nuxel-session.sh` mismatch against canonical source (`fb09cf72…` vs release `fe61581a…`).

---

## 4. Historical prompt inventory

### 4.1 Discovery result

- **82 unique historical PWNAGE IDs** excluding the 95000 audit itself.
- **77 unique tasks have a Kickstarter** (87 files because root, `prompts/`, and `nuxel-pwnage/` copies duplicate many prompts).
- **60 unique tasks have a full specification** (66 files due duplicates).
- **54 complete pairs.**
- **22 Kickstarter-only IDs:** `2000, 3000, 4000, 8000, 9000, 14000, 15000, 16000, 17000, 18000, 19000, 20000, 21000, 22000, 23000, 24000, 25000, 26000, 27000, 28000, 29000, 36000`.
- **5 full-spec-only IDs:** `70000, 71000, 72000, 73000, 92000`.
- **1 conflicting ID:** `12000` has old SnekByte kickstarters plus new NEXUS+NEO Phase 2 prompts created during this audit.
- Git history contains no deleted `pwnage-*.md` or `full-pwnage-*.md` paths (`git log --all --diff-filter=D` returned none).

### 4.2 Prompt duplicates and conflicts

Most pair duplicates are identical copies in the root, `prompts/`, and `nuxel-pwnage/` directories, created by repository reorganisations. They were counted once per ID for the audit. The meaningful conflict is ID `12000`:

- `prompts/pwnage-12000.md` and `prompts/pwnage-12000-snekbyte-latest.md` — old SnekByte task.
- `pwnage-12000.md` and `full-pwnage-12000.md` — new untracked NEXUS+NEO Phase 2 task created at 18:06 on the audit date.

### 4.3 Prompts created during the audit

These untracked files were not present when PWNAGE-95000 started and cannot represent historical deployed work:

| ID | Files | Status in this audit |
|---|---|---|
| 10000 | `pwnage-10000.md`, `full-pwnage-10000.md` | `NOT_IMPLEMENTED` |
| 11000 | `pwnage-11000.md`, `full-pwnage-11000.md` | `NOT_IMPLEMENTED` |
| 12000 | new `pwnage-12000.md`, `full-pwnage-12000.md` | conflicting ID / `SPEC_INCOMPLETE` |
| 96000 | `pwnage-96000.md`, `full-pwnage-96000.md` | `NOT_IMPLEMENTED` |

---

## 5. Atomic requirement matrix

### 5.1 Extraction method

The full specifications were parsed for:

- numbered `##` requirement sections;
- explicit checklist acceptance items (`- [ ]` / `- [x]`);
- all `##`/`###` headings only where a prose-only specification had neither numbered sections nor checkboxes.

This produced **3,220 requirement units**. Each unit carries a deterministic ID (`PWNAGE-<id>-REQ-<nnn>`), source file, kind, status, confidence and the task-level evidence note.

The complete rows are machine-readable:

- `evidence/pwnage-95000/PWNAGE-95000-REQUIREMENTS.csv`
- `evidence/pwnage-95000/PWNAGE-95000-INVENTORY.json`
- `evidence/pwnage-95000/PWNAGE-95000-REMEDIATION.csv` (3,069 non-`VERIFIED_LIVE` rows)

**Limitation:** statuses are inherited from the strongest task-level evidence. They do not claim that every checkbox was independently re-run on the live phone. Where physical owner input is required, the task is deliberately left `PARTIALLY_DEPLOYED`/`DEPLOYED_UNVERIFIED`, not `VERIFIED_LIVE`.

### 5.2 Requirement status counts

| Status | Requirement units | Tasks |
|---|---:|---:|
| `VERIFIED_LIVE` | 151 | 3 |
| `PARTIALLY_DEPLOYED` | 1,954 | 29 |
| `DEPLOYED_UNVERIFIED` | 620 | 15 |
| `BLOCKED` | 435 | 9 |
| `NOT_IMPLEMENTED` | 53 | 3 |
| `SPEC_INCOMPLETE` | 7 | 1 conflicting task |
| `REGRESSED` | 0 at task-status level | 1 confirmed package-integrity regression is recorded separately |
| `PROMPT_NOT_FOUND` | 0 | 0 |

The 22 Kickstarter-only historical tasks have no full-spec acceptance criteria and therefore contribute no requirement units; they are still counted as tasks in the matrix.

### 5.3 Per-task counts

The table in §6 is the master per-task matrix: pairing, requirement count, overall status, confidence, and evidence summary. The CSV/JSON artifacts contain the 3,220 individual rows.

---

## 6. Master PWNAGE task matrix

| PWNAGE ID | Pairing | Requirements | Overall status | Confidence | Evidence |
|---|---|---:|---|---|---|
| 2000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 3000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 4000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 8000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 9000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 10000 | PAIR | 8 | `NOT_IMPLEMENTED` | HIGH | New untracked NEXUS+NEO Phase 0 prompts appeared during the audit (mtime 2026-11-08 18:06); no implementation, build, deployment or live evidence exists. |
| 11000 | PAIR | 10 | `NOT_IMPLEMENTED` | HIGH | New untracked NEXUS+NEO Phase 1 prompts appeared during the audit (mtime 2026-11-08 18:06); prerequisite Phase 0 is not implemented. |
| 12000 | CONFLICTING_VERSIONS | 7 | `SPEC_INCOMPLETE` | HIGH | ID collision: old SnekByte kickstarters use 12000, while new untracked NEXUS+NEO Phase 2 prompts also use 12000. No single unambiguous historical requirement set; Phase 2 is not implemented. |
| 14000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 15000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 16000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 17000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 18000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 19000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 20000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 21000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 22000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 23000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 24000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 25000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 26000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 27000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 28000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 29000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 30000 | PAIR | 1 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.1 commit da0426b8; tests/pwnage30000 pass; live app tree/registry present. |
| 31000 | PAIR | 1 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2; tests exist; live preload receipt shows ALREADY_RAN for current boot. Test drift: older preload expectations fail against P90-era code. |
| 32000 | PAIR | 24 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2 commit b4e2f51e; tests/pwnage32000 contracts. |
| 33000 | PAIR | 35 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2 commit b4e2f51e; contacts/messages/dialer tests. One stale Recorder test expectation. |
| 34000 | PAIR | 37 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2 commit b4e2f51e; tests/pwnage34000 pass. |
| 35000 | PAIR | 45 | `DEPLOYED_UNVERIFIED` | MEDIUM | Release v0.7.2 commit b4e2f51e; performance/navigation changes present in current tree. |
| 36000 | KICK_ONLY | 0 | `SPEC_INCOMPLETE` | HIGH | Only a kickstarter exists; no full specification or atomic acceptance criteria are available in the repository or Git history. |
| 37000 | PAIR | 40 | `DEPLOYED_UNVERIFIED` | MEDIUM | Commit 02941a40 and v0.7.3; current tree contains butterscotch profile. Some tests are stale against later P89/P90 audio changes. |
| 38000 | PAIR | 50 | `DEPLOYED_UNVERIFIED` | MEDIUM | Commit 1c2eb21f/v0.7.4; audio path owner-confirmed historically; tests/pwnage38000 pass. |
| 39000 | PAIR | 15 | `PARTIALLY_DEPLOYED` | MEDIUM | Evidence pwnage-39000 records Wi-Fi boot and stabilization; several polish items remained partial. |
| 40000 | PAIR | 19 | `DEPLOYED_UNVERIFIED` | MEDIUM | Speaker root cause and owner-confirmed audio in v0.7.4 history; current tree has tests but three assertions are stale after P89 audio redesign. |
| 41000 | PAIR | 30 | `DEPLOYED_UNVERIFIED` | MEDIUM | Wi-Fi boot/default state work is present; live Wi-Fi SSH is working, but a fresh boot cycle was not repeated in this audit. |
| 42000 | PAIR | 68 | `PARTIALLY_DEPLOYED` | HIGH | Network GeoClue location is live; satellite GNSS remains BLOCKED_FIRMWARE. |
| 43000 | PAIR | 59 | `PARTIALLY_DEPLOYED` | MEDIUM | Boot/lockscreen/UI work landed; hardware audio/USB experiments and owner checks remain partial. |
| 44000 | PAIR | 67 | `DEPLOYED_UNVERIFIED` | MEDIUM | Commit 100c6890; PWNAGE-44000 live report covers drag, power menu, screenshot, gallery, files, status truth. |
| 45000 | PAIR | 140 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-45000 live report; MTP/security/app registry/flashlight paths live; NFC/fingerprint/cellular remain blocked. |
| 46000 | PAIR | 88 | `PARTIALLY_DEPLOYED` | HIGH | Seven orientation modes and manual transforms work; auto-rotation blocked by sensor hub. Some tests intentionally stale after Doom landscape policy. |
| 47000 | PAIR | 57 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-47000/92000 reports: XRDP/VNC physically verified; scrcpy is Android-only; USB network remains blocked. |
| 49000 | PAIR | 135 | `DEPLOYED_UNVERIFIED` | MEDIUM | PWNAGE-49000 source/headless report plus later live deployments; one cache-version test is stale (current p94000 cache-buster). |
| 50000 | PAIR | 91 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-50000 graphics report: Mali/kbase/EGL and SHM WebKit work; DMA-BUF/zero-copy blocked. |
| 51000 | PAIR | 86 | `PARTIALLY_DEPLOYED` | HIGH | Kernel/flatpak/graphics blockers report; several blockers remain kernel/hardware-bound. |
| 52000 | PAIR | 60 | `PARTIALLY_DEPLOYED` | MEDIUM | PWNAGE-52000 ledger marks many items PASS/partial; one Quick Settings test is stale against P94 extended-level model. |
| 53000 | PAIR | 42 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-53000 graphics report: linear dmabuf/Mali path works; WebKit hardware transport remains blocked. |
| 54000 | PAIR | 128 | `PARTIALLY_DEPLOYED` | HIGH | Seven-mode orientation and manual rotation verified; auto sensor path remains blocked. |
| 55000 | PAIR | 108 | `BLOCKED` | HIGH | WebKit/DMA-BUF/DRM/VGEM prerequisite absent; no /dev/dri; zero-copy scanout unavailable. |
| 56000 | PAIR | 72 | `PARTIALLY_DEPLOYED` | HIGH | Flatpak/user-namespace integration is live (Ferdium/Stremio running); full ARM64 app/portal matrix remains partial. |
| 57000 | PAIR | 99 | `BLOCKED` | HIGH | Broadcom SSP sensor hub is down; raw accelerometer values are zero; vendor patch/runtime missing. |
| 58000 | PAIR | 82 | `VERIFIED_LIVE` | HIGH | PWNAGE-58000 deployed and measured across repeated boots; idle-wakeup work wired into rootfs and live services. |
| 60000 | PAIR | 19 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-60000 report: GPU-SHM production profile live; WebKit DMA-BUF, zero-copy, MFC, HDMI/casting blocked. |
| 61000 | PAIR | 47 | `PARTIALLY_DEPLOYED` | HIGH | MFC kernel/userspace/firmware design implemented; no physical decode; host test blocked by missing linux/videodev2.h in audit environment. |
| 62000 | PAIR | 14 | `DEPLOYED_UNVERIFIED` | MEDIUM | PWNAGE-62000/72000 live hash parity and shell health; physical app/touch matrix remains owner-only. |
| 63000 | PAIR | 14 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-63000/73000 live hash parity and host suites; keyring has not been initialized by owner. Current NuXtore catalog integrity fails on changed Doom files. |
| 64000 | PAIR | 15 | `PARTIALLY_DEPLOYED` | HIGH | GNSS provider/diagnostics deployed; satellite fix BLOCKED_FIRMWARE. |
| 65000 | PAIR | 33 | `PARTIALLY_DEPLOYED` | HIGH | NFC daemon deployed and running OFF; kernel NFC class/physical tag read blocked. |
| 66000 | PAIR | 14 | `BLOCKED` | HIGH | QBT2000 sensor/driver present; no verified TEE-backed provider; enrollment correctly refused. |
| 67000 | PAIR | 39 | `BLOCKED` | HIGH | SSP sensor hub down; auto-rotation cannot receive real samples. |
| 68000 | PAIR | 48 | `BLOCKED` | HIGH | MFC hardware decode not physically proven; matching firmware/patched kernel not landed. |
| 69000 | PAIR | 18 | `BLOCKED` | MEDIUM | NuXtream/casting product absent; DP Alt Mode/DRM absent; USB-C audio requires owner hardware and USB-role testing. Diagnostics/config groundwork only. |
| 70000 | FULL_ONLY | 7 | `DEPLOYED_UNVERIFIED` | MEDIUM | PWNAGE-70000 live completion addendum in the 60000 report: atomic userspace deploy and GPU-SHM verifier passed; cold boot/benchmark not repeated. |
| 71000 | FULL_ONLY | 22 | `BLOCKED` | HIGH | MFC patched kernel/firmware/first decode not landed; MFC remains BLOCKED_GUARDED. |
| 72000 | FULL_ONLY | 7 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-72000 final report: source/live hashes match, userspace deployed, shell healthy; physical matrix owner-only. |
| 73000 | FULL_ONLY | 7 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-73000 final report: live 63000 hashes match and host suites pass; keyring/Vault owner acceptance pending. |
| 80000 | PAIR | 115 | `DEPLOYED_UNVERIFIED` | MEDIUM | PWNAGE-80000 report and tests; live app/navigation behavior partially revalidated by later tasks. |
| 81000 | PAIR | 133 | `PARTIALLY_DEPLOYED` | MEDIUM | PWNAGE-81000 workstreams carried into later live images; several owner/performance checks remain. |
| 82000 | PAIR | 132 | `PARTIALLY_DEPLOYED` | MEDIUM | PWNAGE-82000/84000 live reports; one stale Vesktop fallback assertion. |
| 83000 | PAIR | 26 | `BLOCKED` | HIGH | Camera FIMC-IS firmware/setfiles/media graph absent; no captured frame. |
| 84000 | PAIR | 202 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-84000 live report: clock/alarm/mic/downloader fixes deployed; camera/flatpak/Doom owner checks remain. |
| 85000 | PAIR | 55 | `VERIFIED_LIVE` | HIGH | PWNAGE-85000 live report: Flatpak stall root-caused/fixed and measured; whole-device residual idle poll documented. |
| 86000 | PAIR | 61 | `BLOCKED` | HIGH | Camera firmware/ISP/setfiles still missing; no physical frame. |
| 87000 | PAIR | 42 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-87000 hardware-verified alarm/timer audio and scroll fixes; lockscreen visual/owner checks remain. |
| 88000 | PAIR | 67 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-88000 live report: Doom/services/spoof/theme work; Waydroid and some physical items blocked. |
| 89000 | PAIR | 14 | `VERIFIED_LIVE` | HIGH | PWNAGE-89000 report: deployed hashes match; four measured boots, alarm/timer/readiness/SSH checks pass. |
| 90000 | PAIR | 15 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-90000 final report: source/integration/host tests; several physical input checks remain NOT RUN. |
| 91000 | PAIR | 33 | `PARTIALLY_DEPLOYED` | HIGH | PWNAGE-91000 report: safe boot/service changes and hardware audits; hardware completion blocked. |
| 92000 | FULL_ONLY | 52 | `PARTIALLY_DEPLOYED` | HIGH | REPORT-USBNET: direct LAN XRDP/VNC physically verified; USB network/SSH blocked/unvalidated. |
| 93000 | PAIR | 74 | `PARTIALLY_DEPLOYED` | MEDIUM | All four workstreams deployed; 422/423 canonical live targets match; notification hub/API and icon resolution live. Uncommitted; physical finger/gesture acceptance pending; 2 launcher-registry checks fail. |
| 94000 | PAIR | 156 | `PARTIALLY_DEPLOYED` | MEDIUM | Deployed stamp 20261108T173717; 93/93 P94 source checks and 20/20 Back cycles. Uncommitted; Doom music, human audibility, landscape desktop remain incomplete. Live NuXtore Doom bundle digests are stale. |
| 96000 | PAIR | 35 | `NOT_IMPLEMENTED` | HIGH | New untracked PWNAGE-96000 prompt appeared during the audit (mtime 2026-11-08 18:40); no implementation, build, deployment or live evidence exists. |

---

## 7. PWNAGE-93000 and PWNAGE-94000 — recent live detail

### 7.1 PWNAGE-93000

**Verdict:** `PARTIALLY_DEPLOYED` — implemented and deployed; human touch acceptance and commitment remain incomplete.

Live evidence supporting the four workstreams:

| Workstream | Live evidence |
|---|---|
| GTK/Flatpak duplicate icons | `/api/v1/apps/icon/org.gnome.FileRoller` returns `200 image/svg+xml`, 13,235 B; live status-bar/apps files match source |
| Sound-mode icons | Live indicators report `sound_mode.mode=normal`; status-bar JS is the current `0.8.1-beta` file |
| Notification system | `org.nuxel.Notifications` active; RPC counts `active=2, unread=2, read=0, archived=5, total=7`; list/history/counts succeed; durable JSON exists at `/var/lib/nuxel/notifications.json` |
| Single-Back/Home cleanup | PWNAGE-93000 report documents runtime DOM/service checks; P94 evidence adds 20/20 Back cycles with `bad: []` and no geometry failures |

But:

- All core p93 files are **uncommitted** in the working tree.
- The p93 test file now passes 13/14 under the current tree, not 14/14; the failing check expects the older `notifications.hidden = !on` Quick Settings implementation, which PWNAGE-94000 replaced with the level-based model. This is at minimum test drift, and it means the P93 notification-placement contract is no longer independently green.
- `tools/s10plus/a33/tests/launcher-registry-test.js` reports 2 failures: “Home backgrounds the frame and returns to the launcher” and “activation leaves exactly one visible app surface”. The P94 device-cycle evidence is stronger for the close-to-Home path, but this test discrepancy is unresolved.
- Physical finger/gesture acceptance was not performed.

### 7.2 PWNAGE-94000

**Verdict:** `PARTIALLY_DEPLOYED` — deployed and substantially device-verified; not fully complete.

Evidence:

- Deploy stamp `20261108T173717`.
- 93/93 P94 source checks pass when `tests/pwnage94000/test_pwnage94000.py` runs directly.
- 20/20 portrait app-exit cycles in `evidence/pwnage-94000/cycles-final.jsonl` report `bad: []`, final `geometry_failures: 0`.
- p94 staged source matches installed files for PWA, bridge, session, Doom and GTK/dconf/Flatpak files.
- p94 native build outputs match installed `nuxel-foreign-toplevel`, `nuxel-navdock`, `nuxel-statusbar` and `nuxel-pwa-host`.
- Live graphics status reports GPU-rendered/SHM-presented WebKit, Phoc on Mali kbase, one `/dev/fb0` writer, and zero-copy blocked.

Not complete:

- P94 report itself says Doom music/OPL remains disabled because it hangs WebKit; SFX is enabled and hardware-sink PCM was measured, but no human listening test was performed.
- No true landscape desktop cycle was possible because Home is portrait-locked.
- No human finger sweep.
- All P94 source/native changes are uncommitted.
- **Confirmed regression:** the live NuxTore Doom 2.0.0 bundle still records the pre-P94 `index.html` and `doom.js` hashes. `nuxtore-verify.py` exits 1 with `DIGEST_MISMATCH` and `INTEGRITY FAILURE`.

---

## 8. Missing, regressed and incomplete features — prioritized

### Critical (P0) — provenance and package integrity

1. **PWNAGE-93000/94000 exist only in the dirty worktree.**
   - Impact: a clean checkout or rebuild from `HEAD` loses the deployed fixes; the stale 11:05 payload does not contain them.
   - Evidence: 34 modified + 53 untracked paths; `git status` lists all P93/P94 core files; no commits mention 93000/94000; current source-derived payload differs from the on-disk built payload.
   - Current mitigation: live `.nuxel-rollback-p93-*`/`p94-*` backups exist, but they are not a replacement for committed source.

2. **Live NuxTore catalog integrity failure.**
   - Impact: NuxTore/package verification returns `INTEGRITY FAILURE`; installs/updates may be rejected or trust checks may be falsely failed.
   - Evidence: live and repo `org.nuxel.Doom-2.0.0.bundle.json` expect `index.html` `c500c861…` and `doom.js` `44acef38…`; deployed files are `d382047d…` and `eb7e1e3a…`. Live verifier exits 1 with 2 of 22 files mismatched.
   - Root cause: P94 changed Doom files without restaging/re-signing the catalog.

3. **Version/deployment provenance is internally inconsistent.**
   - `/usr/share/nuxel/VERSION` = `v0.7.9-beta`; running PWA/bridge = `0.8.1-beta`.
   - No committed deployment manifest links the live bytes to a Git commit/build ID.
   - Canonical live-deploy records stop at 11:06; p93/p94 are outside that record set.

### High (P1) — recent verification and release inputs

4. **P93 notification-placement test and launcher-registry tests are not green.**
   - P93: 13/14 pass; stale `notifications.hidden` expectation after P94.
   - Launcher registry: 2 failures involving backgrounded frame state and one visible app surface.
   - Impact: reduced confidence in the single-Back/input-overlay contract; could be stale harness logic or a real lifecycle regression. The live P94 cycle evidence supports the close path but does not cover every backgrounded-surface assertion.

5. **Physical acceptance remains open.**
   - Finger sweep, ear listening, Doom touch feel, lock/unlock gestures, and landscape desktop were not performed by a human in this audit.

6. **Release GPU asset copy is stale.**
   - `release/s10plus/gpu/nuxel-session.sh` does not match canonical source; `tests/pwnage60000/test_gpu_manifest.py` fails.

### Medium (P2) — blocked hardware and partial subsystems

7. Camera: `BLOCKED_FIRMWARE` — no sensor setfiles/ISP/calibration, no media graph, no frame.
8. Satellite GNSS: `BLOCKED_FIRMWARE` — BBD patch/vendor runtime absent; network geolocation is not GNSS.
9. NFC: `BLOCKED_KERNEL` / physical tag — daemon is OFF and healthy, kernel NFC class/read path unproven.
10. Fingerprint: `BLOCKED_SECURE_PROVIDER` — no verified TEE-backed provider; enrollment correctly refused.
11. Auto-rotation / sensor hub: `BLOCKED_VENDOR_RUNTIME` — SSP down, zero samples.
12. MFC hardware decode: `BLOCKED` — no matching firmware/patched kernel/physical decode.
13. DP Alt Mode / HDMI / casting: `BLOCKED`/`NOT_IMPLEMENTED` — no DRM connector, no NuXtream product.
14. Cellular: `BLOCKED_FIRMWARE`/host transport — no ModemManager modem object.
15. Flatpak/app ecosystem: live Flatpak apps exist, but the full ARM64/portal/app matrix is partial.

### Low (P3) — housekeeping and future prompts

16. Older test suites contain many stale assumptions after later architectural changes. They should be updated or explicitly retired.
17. `10000`, `11000`, `12000` (new NEXUS+NEO) and `96000` are new/unimplemented prompts, not deployment regressions.
18. `12000` needs a unique ID or versioned filename scheme.

---

## 9. Test and verification status

### 9.1 Recent suites

| Suite | Result |
|---|---|
| `tests/pwnage94000/test_pwnage94000.py` | **93 pass / 0 fail** |
| `tests/pwnage93000` | **13 pass / 1 fail** (stale QS notification-placement assertion) |
| `tests/pwnage90000/test_pwnage90000.py` | RC 0 |
| `tests/pwnage93000/test_icon_policy.js` | pass |
| `tests/pwnage93000 launcher-registry-test.js` equivalent | 2 failures in `tools/s10plus/a33/tests/launcher-registry-test.js` |
| Live P94 cycle evidence | 20/20 cycles, `bad: []`, `geometry_failures: 0` |
| Live NuXtore verification | **FAIL** — `INTEGRITY FAILURE`, Doom digests |

### 9.2 Older host suites run during the audit

Passing suites included `pwnage30000` (21), `pwnage34000` (4), `pwnage38000` (7), `pwnage42000` (13), `pwnage50000` (8), `pwnage53000` (13), `pwnage58000` (10), `pwnage62000` (4), `pwnage64000` (10), `pwnage65000` (17), `pwnage84000` (14), `pwnage85000` (25), `pwnage89000` (11), `pwnage91000` (16).

Failures or non-collectable groups:

| Suite | Result / likely cause |
|---|---|
| `pwnage31000` | 15 fail / 30 pass / 4 skip — preload receipt expectations; live receipt says `ALREADY_RAN`; likely stale after P90 |
| `pwnage33000` | 1 fail — Recorder path expectation |
| `pwnage37000` | 6 fail — audio-unit/A29-A45 drift and motion CSS assumptions after later changes |
| `pwnage40000` | 3 fail — stale P89 audio-unit/25%-cap assertions |
| `pwnage46000` | 2 fail — intentional Doom landscape policy and lockhead-state renaming |
| `pwnage49000` | 1 fail — stale `p91100` cache-buster assertion; current is `p94000` |
| `pwnage52000` | 1 fail — stale expanded-state privacy selector |
| `pwnage60000` | 2 fail — stale release GPU asset and host `/proc` probe |
| `pwnage61000` | 1 fail — host compiler lacks `linux/videodev2.h` |
| `pwnage63000` | 1 fail — live/local NuXtore Doom digest mismatch (**genuine**) |
| `pwnage82000` | 1 fail — stale Vesktop fallback marker assertion |
| `pwnage44000`, `45000`, `54000`, `80000`, `81000` | no pytest-collectable tests; use their shell/Node runners |

The failures above do not by themselves prove the live phone is broken, but they prove the regression battery is not clean. That is why the overall verdict is not `ALL_REQUIREMENTS_VERIFIED_LIVE`.

---

## 10. Evidence index

Primary audit evidence is under `evidence/pwnage-95000/`:

| File | Contents |
|---|---|
| `live-identity-and-state.txt` | Device identity, version surfaces, services, processes, trees |
| `live-file-manifest.txt` | Deployment records, backup inventories, installed SHA-256 manifest, GTK/dconf/Flatpak state |
| `live-p94-state.txt` | P94 install manifest, p93/p94 backup inventory, target mtimes, service state |
| `live-p94-parity.txt` | P94 source/config/native build parity |
| `canonical-payload-parity.json` / `.txt` | 423-target canonical payload comparison |
| `live-api-and-widgets.txt` | HTTP health/API and notification/sound/registry probes |
| `live-notification-rpc.txt` | Notification counts/list/history and hub D-Bus/service evidence |
| `live-catalog-integrity.txt` | Live NuXtore verifier failure |
| `live-nuxtore-doom-mismatch.txt` | Exact Doom digest mismatches |
| `launcher-registry-test.txt` | 2 launcher-registry failures |
| `pwnage93000-pytest.txt` | 1 P93 test failure |
| `tests-p94000.txt` | 93/93 pass |
| `tests-p90000.txt` | P90000 pass |
| `PWNAGE-95000-INVENTORY.json` | Full task + requirement inventory |
| `PWNAGE-95000-REQUIREMENTS.csv` | 3,220 requirement rows |
| `PWNAGE-95000-REMEDIATION.csv` | 3,069 non-verified remediation rows |
| `PWNAGE-95000-TASK-MATRIX.md` | Per-task matrix embedded in this report |

Existing repository evidence used for historical verdicts includes:

- `PWNAGE-93000-REPORT.md`, `PWNAGE-91000-REPORT.md`, `REPORT-PWNAGE-94000.md`
- `docs/pwnage-80000/REPORT.md`
- `docs/pwnage-89000/evidence/20261107T151308Z/ENGINEERING-REPORT.md`
- `docs/pwnage-90000/FINAL-REPORT.md`
- `docs/beta-finalization/live/PWNAGE-*.md`
- `evidence/pwnage-94000/cycles-final.jsonl`
- `evidence/pwnage-60000/70000-*` and `evidence/pwnage73000/*`

---

## 11. Confidence and limitations

- **High confidence:** SSH identity, device model, live service state, file hashes, p94 parity, notification hub operation, stale build artifact, version mismatch, NuXtore catalog failure, and hardware blockers already documented with device evidence.
- **Medium confidence:** historical task-level deployment status where the task predates the current boot and no fresh physical test was possible.
- **Low/unknown:** human-only interactions, physical hardware paths requiring owner participation, and old Kickstarter-only tasks with no full acceptance criteria.
- No secrets, private keys, tokens, biometric data, SIM identifiers or keyring contents were read or printed.
- No bootloader, kernel, recovery, modem, EFS, partition, firmware or filesystem-destructive operation was performed.
- No service was stopped, restarted or modified. No configuration was overwritten. No deployment was executed.

---

## 12. Final response format

### A. Overall result

**`AUDIT_COMPLETE`**

### B. Device deployment verdict

**`PARTIALLY_DEPLOYED`**

### C. Key numbers

- Historical PWNAGE tasks found: **82** unique IDs excluding 95000.
- Kickstarter prompts found: **77** unique tasks (87 files).
- Full specifications found: **60** unique tasks (66 files).
- Atomic requirements extracted: **3,220**.
- Verified live: **151** requirement units / 3 tasks.
- Partially deployed: **1,954** requirement units / 29 tasks.
- Not deployed/not implemented: **53** requirement units / 3 tasks; **23** tasks are `SPEC_INCOMPLETE` (22 Kickstarter-only + 1 conflicting ID).
- Regressed: **1 confirmed live package-integrity regression** (NuxTore Doom), plus 3 unresolved test/behaviour discrepancies.
- Blocked: **435** requirement units / 9 tasks.

### D. Most important findings

1. PWNAGE-93000 and 94000 are deployed on the phone but exist only in the dirty worktree; the on-disk built payload predates them.
2. The live NuxTore catalog fails integrity verification because deployed Doom files no longer match the package digests.
3. Version surfaces disagree (`0.7.9` vs `0.8.1`), and there is no commit/build deployment manifest.
4. Live userspace otherwise matches the current source-derived payload at 422/423 targets.
5. The notification hub, icon resolver, sound-mode provider, GPU-SHM compositor path, VNC/RDP stack and core shell are live.
6. Camera, satellite GNSS, NFC tag I/O, fingerprint, sensor-hub auto-rotation, MFC decode, DP/casting and cellular remain blocked.
7. Human finger/ear/landscape acceptance is still outstanding.

### E. Artifacts

- `REPORT-PWNAGE-95000.md` (this report)
- `REMEDIATION-PWNAGE-95000.md`
- `evidence/pwnage-95000/PWNAGE-95000-INVENTORY.json`
- `evidence/pwnage-95000/PWNAGE-95000-REQUIREMENTS.csv`
- `evidence/pwnage-95000/PWNAGE-95000-REMEDIATION.csv`
- `evidence/pwnage-95000/PWNAGE-95000-TASK-MATRIX.md`

### F. Next step

Do **not** blind-redeploy. First, in order:

1. Review and commit the PWNAGE-93000/94000 working-tree changes, including `tools/pwnage93000`/`94000`, `tests/pwnage93000`/`94000`, `pwa/nuxel-home/js/topbar-machine.js`, GTK/dconf/Flatpak configs, and the modified PWA/bridge/session/native sources.
2. Re-sign/restage the NuXtore Doom bundle and deploy the corrected catalog; verify `nuxtore-verify.py` exits 0 on the phone.
3. Generate a fresh canonical payload from the committed tree; record commit, build ID, payload SHA-256 and component hashes in a deployment manifest.
4. Correct `/usr/share/nuxel/VERSION` and the deployment receipt so all version surfaces agree.
5. Resolve the launcher-registry/P93 test discrepancies, then run the owner physical acceptance matrix for touch, Back/Home/drawer, sound, Doom, lockscreen and landscape.
6. Only after those steps, address the hardware-blocked workstreams (camera, GNSS, NFC, fingerprint, sensor hub, MFC, DP/casting, cellular) in a controlled, reversible batch.

