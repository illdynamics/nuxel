# FULL-PWNAGE-72000 — Finish and prove PWNAGE-62000 on the live S10+ (shell, lockscreen, boot and console)

**Mission type:** finish-off / live deployment / physical verification for `full-pwnage-62000.md`.
**Relationship to 62000:** PWNAGE-62000 source work and the 2026-11-03 08:08 UTC userspace deployment exist, and the shell processes are running. This mission does **not** redo the 62000 design. It closes the remaining live drift, deploys the post-deploy source fixes, completes the missing physical acceptance matrix, and replaces historical claims with current-boot evidence.
**Repository:** `/x/nuxel` (Git root), branch `main`, baseline HEAD `0bed35d881ba674a21f67d31501e84f1031992b5`. Re-verify; do not assume.
**Prompt suite:** `/home/wicked/Desktop/nuxel-pwnage/`.
**Target:** `root@10.20.30.16`, key `$HOME/.ssh/wicked_wqn_id_rsa`, strict host-key checking, bounded SSH timeouts.
**Owner request:** finish the remaining PWNAGE-62000 work on the phone. This authorises an atomic **userspace** deployment over Wi-Fi SSH, the service/compositor restarts performed by the repository's own 62000 deploy script, and normal owner-approved reboots over the same SSH route. It does **not** authorise TWRP, kernel/DTB/BOOT/firmware/partition writes, bootloader changes, a factory reset, or changing the USB role.

---

## 0. Current verified state (2026-11-03 ~23:46 CET) — re-verify, do not assume

### 0.1 Source state

- Git root `/x/nuxel`, branch `main`, HEAD `0bed35d881ba674a21f67d31501e84f1031992b5`.
- 154 dirty owner paths are present. Preserve every one; do not reset, clean, stash, commit or push.
- PWNAGE-62000 source gates were green at the end of the 62000 worker:
  - service graph: `problems=0`, verdict `OFFLINE_TESTED`;
  - boot surface contract: PASS;
  - launcher registry test: PASS, `registry_version=12`, 42 app IDs;
  - lockscreen unlock: 66/66;
  - reboot policy: 22/22;
  - preload, shell-chrome, console-session and drawer tests: PASS.
- The host cross-build of `nuxel-statusbar` was blocked only because this Fedora host lacks an aarch64 Cairo/Pango sysroot. The phone has the native build dependencies and the deploy script builds there. Do not call the target build blocked merely because the host cross-build is blocked.
- Post-deploy source changes that are relevant to this mission:
  - `pwa/nuxel-home/manifest.json` now has `nuxel.registry_version=12`, includes `org.nuxel.Clipper` and `org.nuxel.Vault`, and has SHA-256 `f6d0709ed9974cfc804a60e6ac98ed67f6814d2172dd2cf787da0605ea37b575`.
  - `tools/s10plus/a31/nuxel-wayland.service` has the provenance `ExecStart` fix and SHA-256 `7d00d6754fed7a19af5c4b38f883c1973ba6152eefc692b674b7eee47b7d50a9`.
  - `pwa/nuxel-home/js/apps.js` SHA-256 `aa1666288362f5b68dea8553bc5cce03a7581afa0e83838edc322731c3dc2228`.
  - `pwa/nuxel-home/js/app.js` SHA-256 `a4b69270b5c465fad805d468dad8052d863f0c484504ab23881338d957f24538`.
  - `pwa/nuxel-home/sw.js` SHA-256 `85f7513ef3ee25c19136058b493d9af5706cd1fc4fc1ab13db0d52d0f6a56e69`.
  - `tools/s10plus/a45/nuxel-session.sh` SHA-256 `fe61581a46f95b725e90c0f76cd2e2ab4484db0f81cb017c9151bbe2a85ed2e2`.
  - `tools/s10plus/a45/nuxel-shell-chrome.sh` SHA-256 `644b564abcb5fb87a9bc30073722fa1889b45cf377a217f2174108b479ad1360`.

### 0.2 Live phone state (strict Wi-Fi SSH, read-only probe)

- Target identifies as `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820`; `uname -m` is `aarch64`; kernel `4.14.253-gf7194c1d15ed-dirty`; boot ID `e3b5e426-5c2b-4ac8-ad14-70e2cfb27ab4`.
- `nuxel-wayland`, `nuxel-http-bridge`, `nuxel-wl-fb` and `nuxel-bridge` are active.
- `nuxel-shell-chrome.sh`, `nuxel-navdock` and `nuxel-statusbar` are running.
- `/run/nuxel-statusbar.state` currently reports `{"ready":true,"visible":false,"reason":"locked","locked":true,...}`.
- `/run/nuxel/shell-chrome.json` currently reports all supervisor/navdock/statusbar/lock-watch PIDs ready.
- The last recorded 62000 deployment is `/var/lib/nuxel/diagnostics/pwnage62000-deploy.json`, deployed at `2026-11-03T08:08:32Z`, backup `/var/backups/nuxel/p62000-20261103T080758Z`.
- `/run/nuxel-p62000-deploy.json` and `/run/nuxel-p62000-backup-dir` are absent because `/run` was cleared by a later boot. The durable receipt exists; treat the old boot's `/run` receipt as historical.

### 0.3 Confirmed live drift this mission must close

1. **Wrong live Home manifest.**  
   Live `/usr/share/nuxel/pwa/nuxel-home/manifest.json` SHA-256 is `d7a0b744424a6b380fbbfc5918e5a4c351ce4d8951e66dfdc9696ce68305127f`, and its contents are the **Nuxel Clipper** manifest, not the Nuxel Home manifest. The canonical source is `f6d0709e…`. The 62000 deploy script does not currently stage/install `pwa/nuxel-home/manifest.json`. This is a real deployment defect and must be fixed.
2. **Wayland unit drift.**  
   Live `/etc/systemd/system/nuxel-wayland.service` SHA-256 is `7ea793abaf45c0ccb78037c89e5bbbe12b2e96316011edf1cb645e87a4c213d0`; canonical source is `7d00d675…`. The live `ExecStart` already points at `/usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh`, but reconcile the whole unit and its install provenance rather than assuming the remainder is correct.
3. **Deploy-script parity gap.**  
   Add the Home manifest and the canonical wayland unit to the 62000 deployment set, with backup, atomic install, checksum records and post-install assertions. Do not patch only the live phone and leave the script able to regress the same files on the next run.
4. **Missing physical acceptance.**  
   The historical report proved Stremio Flatpak, lock-state and one console-indicator case. It did **not** prove the full native GTK + Flatpak + WebKit lockscreen/top-bar/input-focus matrix, the physical touch matrix, or 10 cold boots. Do not inherit those old labels as current truth.
5. **Boot/shutdown statistics remain incomplete.**  
   Only two cold boots/two reboots were measured historically; the report explicitly calls the numbers measurements, not median/p95. `nuxel-mic-route.service` historically cost about 40.9 s. Re-measure on this boot and after deployment; do not claim 10/10 unless actually performed.
6. **Host statusbar build is not the target acceptance gate.**  
   The target build through `tools/pwnage62000/deploy-pwnage62000.sh` is the authoritative route for this mission. Optionally add a documented aarch64 sysroot note, but do not spend the mission trying to make host x86_64 pkg-config produce an aarch64 binary.

### 0.4 Do not “fix” by faking

- Do not install a fake statusbar, fake layer-shell surface, fake lock state or synthetic input/focus event.
- Do not claim a physical matrix passed from JS/C tests, a state file, a process list, a screenshot of one app, or a single successful boot.
- Do not disable the lockscreen, security lock RPC, lock watcher, SSH, NetworkManager or the recovery path to make a test easier.
- Do not replace the running compositor with an unproven alternative.
- Do not write `/dev/fb0` from any new process; `nuxel-wl-fb` must remain the only framebuffer writer.

---

## 1. Objective and definition of done

Close PWNAGE-62000 as a deployed, physically exercised feature on the S10+:

1. Fix the deploy-script parity gaps and deploy the exact canonical 62000 source to the phone.
2. Prove source-to-live hash parity for every installed 62000 binary, script, PWA asset, unit and drop-in.
3. Complete the lockscreen/top-bar/navdock/input-focus matrix on Home, a native GTK app, a Flatpak app and a WebKit surface.
4. Prove the live-console indicators reflect active transport/session state, not Wi-Fi readiness.
5. Measure startup readiness and shutdown stop behavior on real normal boots/reboots over Wi-Fi SSH.
6. Re-run all relevant host gates and the target build after the changes.
7. Produce a current-boot evidence bundle and an honest per-criterion status.

A feature is `PHYSICALLY_VERIFIED` only when the dated test output, state files and a non-secret screenshot/OCR or equivalent observation from the actual S10+ demonstrate the behavior. A process being alive is not proof of overlay precedence.

---

## 2. Non-negotiable safety and recovery rules

- **Allowed:** atomic userspace deploy, service restarts, compositor/session restart performed by the repository's own deploy script, normal owner-approved reboot via `systemctl reboot`, read-only live probes, screenshots/OCR, and non-destructive input testing with existing installed tools.
- **Prohibited:** TWRP/recovery, heimdall/Odin, flashing BOOT/kernel/DTB/vendor_boot/modem/EFS/PIT, partition table changes, bootloader/OEM/KG/FRP changes, factory reset, forced reboot, SysRq, `kill -9 1`, USB role changes, and any write to credential stores.
- Before any deployment or reboot, record the current boot ID, SSH reachability, `nuxel-wayland`/`nuxel-wl-fb` state, the backup location, and the exact rollback command.
- Keep strict host-key verification. Do not disable it to make SSH work.
- If the compositor restart drops the shell but SSH remains reachable, reconnect and wait for the state files. If SSH is lost, do not escalate to TWRP automatically; stop, record the exact failure and the owner recovery action.
- Do not inspect secrets, keyrings, TOTP seeds, vault contents or biometric data. This mission is about shell chrome, not credentials.
- Do not overwrite prior reports or evidence. Append a new dated section or create a new evidence directory.

---

## 3. Execution order

### Step 0 — baseline and preflight (read-only)

1. Verify Git root, branch, HEAD, `git status --short --branch`, and the 154 pre-existing dirty paths. Save a checkpoint.
2. Verify the SSH key exists and is readable; never print its contents.
3. Record target model, `uname -m`, kernel, boot ID, uptime, active services and the current statusbar/navdock/lock state.
4. Record exact SHA-256 for every live 62000 target and every canonical source counterpart.
5. Record the durable 62000 deploy receipt and backup path.
6. Verify the 62000 deploy script, rollback script, release assets and test commands exist and are executable.

### Step 1 — reconcile and fix source/deploy parity

1. Re-run the 62000 source gates before editing:
   - `python3 tools/beta/verify-service-graph.py` (or the repository's current canonical invocation);
   - `python3 tests/pwnage62000/test_boot_surface_contract.py` or the current boot-surface test;
   - `node tools/s10plus/a45/launcher-registry-test.js` (or the current launcher registry test);
   - `python3 -m pytest -q tests/pwnage62000`;
   - `node tools/s10plus/a45/test-lockscreen-indicators.js`;
   - `node tools/s10plus/a45/test-lockscreen-layout.js`;
   - `node tools/s10plus/a45/test-lockscreen-unlock.js`;
   - `node tools/s10plus/a45/test-drawer-gesture.js` or the current path;
   - `python3 tools/s10plus/a45/test-lockscreen-indicators.py`;
   - `bash tools/beta/tests/test-rollback-reboot.sh`;
   - `python3 -m pytest -q tests/pwnage31000/test_preload_cinema.py tests/pwnage31000/test_preload_packaging.py`.
2. Fix `tools/pwnage62000/deploy-pwnage62000.sh` so it stages and atomically installs:
   - `pwa/nuxel-home/manifest.json` to `/usr/share/nuxel/pwa/nuxel-home/manifest.json` **and** `/usr/share/nuxel/nuxel-home/manifest.json` where that directory exists;
   - `tools/s10plus/a31/nuxel-wayland.service` to `/etc/systemd/system/nuxel-wayland.service`, preserving all existing drop-ins;
   - any other 62000 source file that is currently installed by a different path or not installed at all.
3. Add the new targets to the backup list and to the post-deploy source/live hash assertion.
4. Add explicit content checks, not only hashes:
   - Home manifest `name` is the Nuxel Home name, not `Nuxel Clipper`;
   - `nuxel.registry_version == 12`;
   - the registry contains `org.nuxel.Clipper` and `org.nuxel.Vault`;
   - `NUXEL_REGISTRY_VERSION = 12` in `apps.js`;
   - `ExecStart=/usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh` in the canonical unit;
   - `nuxel-session.sh` and `nuxel-shell-chrome.sh` hashes match source;
   - all five native binaries are AArch64.
5. If you add a new verifier, make it bounded and fail-closed. It must return non-zero when a hash, manifest field, unit value or required file is missing.
6. Re-run the source gates after the deploy-script changes.

### Step 2 — atomic userspace deployment

1. Create a timestamped target-side backup under `/var/backups/nuxel/p62000-<UTC>/` and verify its `SHA256SUMS`.
2. Run the canonical deployment from `/x/nuxel`:
   ```sh
   SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
     tools/pwnage62000/deploy-pwnage62000.sh root@10.20.30.16
   ```
3. The deploy may restart `nuxel-http-bridge`, `nuxel-button-manager`, `nuxel-wayland` and `nuxel-wl-fb`, as the script already does. This is authorised userspace work.
4. Wait for real readiness receipts, not just systemd `active`:
   - `/run/nuxel-wl-fb.state` contains `FRAMES_OK`;
   - `/run/nuxel-navdock.json` exists and reports readiness;
   - `/run/nuxel-statusbar.state` exists and reports the expected lock/visibility reason;
   - `/run/nuxel/shell-chrome.json` exists and reports all expected PIDs;
   - the foreign-toplevel listing works.
5. If a component fails, capture the exact unit log, state file and build error. Roll back with the newly created backup if the shell is broken. Do not reboot into an unknown state to “see if it fixes itself”.

### Step 3 — live parity and state-machine acceptance (no physical interaction yet)

Record exact output for:

1. `sha256sum` of every installed binary, script, PWA manifest/JS/CSS, systemd unit and drop-in; compare with canonical source.
2. `systemctl is-active` for `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-http-bridge`, `nuxel-button-manager`, `nuxel-bridge`.
3. `systemctl show nuxel-wayland.service -p TimeoutStopUSec -p ExecStart -p DropInPaths --value`.
4. `systemctl show nuxel-audio-session.service -p TimeoutStopUSec --value`.
5. `systemctl show nuxel-wl-fb.service -p TimeoutStopUSec --value`.
6. The live Home manifest contents and verified `registry_version=12`.
7. `/run/nuxel-statusbar.state`, `/run/nuxel-navdock.json`, `/run/nuxel/shell-chrome.json`, `/run/nuxel/foreground.state`, `/run/nuxel/lock-enforcement.state`.
8. `nuxel-foreign-toplevel list` while Home is foreground and while each test app is foreground.
9. `system_indicators.get_indicators()` or the canonical bridge status endpoint, with the actual session counts.

Expected logic:

- statusbar hidden on Home;
- statusbar hidden while locked;
- statusbar visible for a non-Home app;
- navdock shown/hidden with the same foreground transition;
- lock state wins over every app frame;
- foreground state changes are reflected without restarting the shell;
- console indicators show active sessions, not merely a configured/ready network interface.

### Step 4 — physical acceptance matrix (owner-assisted where needed)

Run these on the actual S10+ display. Use existing installed tools; do not install a new input stack or replace the compositor. Capture non-secret screenshots plus the corresponding state files and OCR/text observations.

| Case | Required observation |
|---|---|
| Home | statusbar hidden; navdock visible as designed; no duplicate top bar |
| Locked over Home | lockscreen visible; statusbar/navdock do not cover it; app activation is blocked |
| Native GTK app | top bar appears over the app; app content remains interactive; no focus theft |
| Flatpak app (Stremio if installed) | top bar/navdock appear; lockscreen wins when locked; no duplicate bar |
| WebKit/PWA surface | top bar/navdock appear; lockscreen wins; input focus remains correct |
| Lock attempt from foreground app | app cannot draw over the lock; existing lock enforcement state remains fail-closed |
| Unlock | Home returns, lockscreen disappears, statusbar hides on Home, input works |
| Drawer swipe / touch fallback | drawer opens; no stuck overlay; this may be owner-assisted |
| Long-press Back / navigation gesture | behavior matches the existing contract; no stuck bar/dock |
| Console indicators, zero sessions | base penguin only; no false WLAN/serial/USB session icon |
| Console indicators, one Wi-Fi SSH session | WLAN/session indicator reflects the live PTY; not Wi-Fi readiness |
| Console indicators, serial/USB if available | each transport is independently represented; if no gadget exists, mark `NOT_TESTED`/`BLOCKED_EXTERNAL` |

For each case, record app ID, lock state, statusbar state, navdock state, foreground state, relevant screenshot filename and UTC timestamp. A state file alone is not a substitute for the visible test.

### Step 5 — startup and shutdown measurement (normal reboots only)

Only after the deployment is healthy and the owner has approved a normal reboot:

1. Record the old boot ID and the pre-reboot state.
2. Use `systemctl reboot` over Wi-Fi SSH. Never use `reboot -f`, `systemctl reboot --force`, SysRq or `kill -9 1`.
3. Reconnect with bounded retries. Record the new boot ID.
4. Collect `journalctl -b -o short-monotonic` for `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-preload-cinema`, `nuxel-mic-route`, `nuxel-audio-session` and the display bridge.
5. Measure:
   - time to lockscreen visible;
   - time to Home interactive;
   - time to navdock/statusbar readiness;
   - any black-screen interval before the first real frame;
   - stop duration for each relevant unit;
   - whether `nuxel-mic-route` still dominates total userspace boot.
6. Repeat at least three cold boots and three normal reboots if the owner authorises the time. If fewer are possible, report the exact count and mark the 10× statistic `PARTIAL`, not PASS.
7. Verify the shutdown path still leaves Wi-Fi SSH usable until normal teardown and does not require TWRP.

### Step 6 — regression and final live checks

Run the full 62000 host matrix again after deployment, plus the 31000 preload tests and any service-graph/package checks touched by the deploy-script change. Re-check that the deployment did not regress:

- 60000 GPU/session behavior (the compositor wrapper still starts);
- 63000 bridge/keyring files (do not inspect secrets; verify hashes/active services only);
- Home launch, app registry, lock enforcement and console indicators.

### Step 7 — report and handoff

Write a dated evidence bundle under a new path such as `/x/nuxel/evidence/pwnage72000/` (or the repository's established evidence location, without overwriting old evidence). Include:

- baseline and post-deploy boot IDs;
- source/live hash table;
- deploy log and backup path;
- test commands with exact exit codes and pass/fail/skip counts;
- physical matrix table with timestamps and screenshot filenames;
- boot/shutdown timing table with raw journal excerpts;
- remaining limitations and owner actions;
- rollback result or a tested rollback command;
- final status.

---

## 4. Required capability labels

Use these states exactly where applicable: `IMPLEMENTED`, `BUILT`, `HOST_TESTED`, `IMAGE_PACKAGED`, `DEPLOYMENT_PREPARED`, `INSTALLED`, `BOOTED`, `PHYSICALLY_VERIFIED`, `PARTIAL`, `BLOCKED_EXTERNAL`, `OWNER_ACTION_REQUIRED`, `REGRESSION`.

Minimum honest outcome:

- source/deploy parity fixes: `IMPLEMENTED`/`HOST_TESTED`;
- target build: `BUILT`;
- userspace install: `INSTALLED`;
- shell after restart: `BOOTED` only if the new session actually starts;
- lockscreen/top-bar/navdock/input matrix: `PHYSICALLY_VERIFIED` only for cases actually observed;
- 10× boot/reboot statistics: `PARTIAL` unless truly completed;
- any host-only build limitation: `BLOCKED_EXTERNAL` only if it prevents the required target result, not merely the host convenience build.

Do not use `PHYSICALLY_VERIFIED` for a process listing, a state file, a JS test or a historical report.

---

## 5. Deliverables

1. Updated `tools/pwnage62000/deploy-pwnage62000.sh` with manifest/unit parity and fail-closed assertions.
2. Any small source/test fix required by the live drift, with exact reason.
3. Atomic deployment log, backup path and rollback command.
4. Source/live SHA-256 parity evidence.
5. Physical acceptance matrix evidence for Home, lock, native GTK, Flatpak and WebKit.
6. Console-indicator truth table with actual session counts.
7. Startup/shutdown timing evidence from real boots.
8. Regression results for the 62000, 31000 and any touched shared-area tests.
9. Final report with per-criterion status and remaining owner actions.

---

## 6. Final response format

Return:

- **Executive result** — do not overstate.
- **Exact tested hardware/software** — model, kernel, boot ID, Nuxel source HEAD.
- **What changed** — file-by-file, including the deploy-script fix.
- **Live parity** — source vs installed hashes table.
- **Physical results** — matrix with PASS/FAIL/NOT_TESTED and evidence paths.
- **Boot/shutdown results** — counts, timings and limitations.
- **Test results** — commands, exit codes, counts.
- **Remaining blockers / owner actions** — exact and ordered.
- **Rollback** — exact working command and tested/untested state.
- **Final status** — one of `FULLY_FIXED_AND_PHYSICALLY_VERIFIED`, `IMPLEMENTED_PENDING_OWNER_TEST`, `PARTIAL_IMPLEMENTATION`, `BLOCKED_EXTERNAL`, or `REGRESSION`.

If the only missing item is a physical action the agent cannot perform, stop at `OWNER_ACTION_REQUIRED` with the exact action and do not fake it. If the deployment is healthy but the full matrix was not observed, use `PARTIAL`, not `FULLY_FIXED_AND_PHYSICALLY_VERIFIED`.
