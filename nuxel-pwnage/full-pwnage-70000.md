# FULL-PWNAGE-70000 — Finish and prove PWNAGE-60000 on the live S10+ (userspace GPU completion)

**Mission type:** finish-off / live deployment / physical verification for `full-pwnage-60000.md`.
**Relationship to 60000:** this mission does not replace or redo the 60000 source work. It closes the remaining 60000 gaps: the tested userspace is not yet consistently installed on the phone, the live fail-closed verifier does not pass, and the production Mali path has not been re-proved after deployment.
**Repository:** `/x/nuxel` (Git root), branch `main`, baseline HEAD `0bed35d881ba674a21f67d31501e84f1031992b5` (re-verify; do not assume).
**Prompt suite:** `/home/wicked/Desktop/nuxel-pwnage/`.
**Owner request:** the owner explicitly asked for the remaining PWNAGE-60000 work to be finished and verified on the phone. That authorises an atomic **userspace** deployment over Wi-Fi SSH and the service restarts required by the repository's own deploy script. It does **not** authorise kernel/DTB/boot/firmware/partition writes, TWRP/heimdall, bootloader changes, or changes to protected partitions.

---

## 0. Current verified state (2026-11-03 ~19:45 CET) — re-verify, do not assume

### 0.1 Source state

- `full-pwnage-60000.md` source work is substantially complete and host-tested:
  - `python3 -m pytest -q tests/pwnage60000` → **31 passed**.
  - `python3 -m pytest -q tests/pwnage53000` → **13 passed**.
  - `python3 -m pytest -q tests/pwnage50000` → **8 passed**.
  - `release/s10plus/gpu/SHA256SUMS` → all 10 entries verify.
- `release/s10plus/gpu/*` was re-synced from canonical sources by the 60000 worker.
- `configs/nuxel/graphics/graphics-profile.json` and the release copy default to `gpu-rendered-shm-presented`.
- The 60000 worker was terminated before it could emit a final report or mutate the phone. Treat the prior `PWNAGE-60000-REPORT.md` as historical evidence, not as current live truth.

### 0.2 Live phone state (strict Wi-Fi SSH, read-only)

- Target: `root@10.20.30.16`, key `~/.ssh/wicked_wqn_id_rsa`, SM-G975F `beyond2lte`.
- Kernel: `4.14.253-gf7194c1d15ed-dirty #5 SMP PREEMPT`.
- Boot ID: `e3b5e426-5c2b-4ac8-ad14-70e2cfb27ab4`.
- `phoc`, `nuxel-wl-fb`, `nuxel-statusbar`, `nuxel-navdock` and `nuxel-bridge` are running.
- `nuxel-statusbar`/`nuxel-navdock` belong to PWNAGE-62000. Do not disturb or remove them.

### 0.3 Confirmed live drift that this mission must close

1. `/usr/lib64/libEGL_mesa.so.0 -> libEGL_mesa.so.0.0.0.nuxel-bak` — the stock backup, **not** the Nuxel kbase Mesa library.
2. `/usr/share/nuxel/gpu-manifest.json` records `nuxel-session.sh` SHA-256 `07668a4e3d8fcce31ef895239977a14696834eae30222c491d0ba8d87df4403f`, while the installed file is `fe61581a46f95b725e90c0f76cd2e2ab4484db0f81cb017c9151bbe2a85ed2e2`.
3. The verifier script is **not installed** in `/usr/lib/nuxel/`; the deploy script runs it from its staging directory.
4. The current running desktop still holds the Nuxel Mesa library and `/dev/mali0` FDs, so the live desktop is GPU-active; that does **not** make the fail-closed image gate pass.

### 0.4 What is genuinely blocked or owner-only (do not try to “fix” by faking it)

- WebKit DMA-BUF / hardware buffer transport: `/dev/dri` is absent; `drmMainDevice()` is null. Do not create a fake `/dev/dri`, do not symlink `/dev/mali0`, do not claim DMA-BUF.
- Zero-copy panel scanout: not available; `nuxel-wl-fb` is still the single CPU-copy presenter.
- USB-C DP Alt Mode / HDMI: no `altmode`/DP VDO state; requires a real adapter/EDID and owner test.
- Miracast / LAN screen share: no end-to-end P2P/RTSP/capture/encode/receiver proof; no Cast UI may be advertised.
- Exynos MFC hardware decode: separate mission (71000); keep the GStreamer guard active.

---

## 1. Objective and definition of done

Finish PWNAGE-60000 on the physical phone:

1. Atomically deploy the tested 60000 userspace graphics set from the repository.
2. Make the live fail-closed GPU verifier pass, including the correct EGL symlink and a current runtime manifest.
3. Prove the normal Home/Settings path runs on Mali with `gpu-rendered-shm-presented`, and that the web process presents via SHM (not DMA-BUF).
4. Prove the automatic `software-safe` fallback still works without a blank screen or manual SSH repair.
5. Re-run matched A/B benchmarks and save raw evidence.
6. Update the PWNAGE-60000 report/TODO honestly; keep all blocked/owner-only capabilities labelled as such.

`FULLY_DONE` is allowed only if items 1–5 pass on the phone and item 6 is complete. If a physical test cannot be performed, mark it `OWNER_ACTION_REQUIRED` or `NOT_TESTED`; do not upgrade it.

---

## 2. Non-negotiable safety boundaries

- **Allowed:** read-only diagnostics; host tests; atomic userspace deployment over Wi-Fi SSH; restart of `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-bridge` as required by the repository deploy script; screenshots/captures that do not disturb the session.
- **Forbidden:** kernel/DTB/BOOT/RECOVERY/firmware/other partition writes; TWRP/heimdall/Download Mode; bootloader/USB-role changes; creating `/dev/dri`; writing or symlinking `/dev/mali0`; adding a second `/dev/fb0` writer; enabling `CONFIG_DRM_EXYNOS`/`CONFIG_DRM_VGEM` as an experiment; removing the GStreamer guard; claiming DMA-BUF or zero-copy without real exported/imported FDs.
- Preserve the owner's dirty tree. Do not revert, reset, clean, stash, commit or push. Do not overwrite prior reports without a dated new section.
- Before any live change: prove Wi-Fi SSH is healthy, save the exact rollback command, and confirm the repository's backup is created.
- A reboot is **not** authorised by this mission unless the owner explicitly authorises a cold-boot test in the active task. If not authorised, perform the live deployment and mark the cold-boot acceptance line `OWNER_ACTION_REQUIRED`.

---

## 3. Execution order

### Step 0 — preflight and baseline

1. Read `docs/beta-finalization/live/PWNAGE-60000-REPORT.md`, `PWNAGE-60000-TODO.md`, `full-pwnage-60000.md`, the graphics profile/helper, the A67 deploy/rollback scripts and the session launcher.
2. Record: `git rev-parse HEAD`, branch, `git status --porcelain | wc -l`, live `uname -r`, boot ID, `systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-bridge`, `/run/nuxel-wl-fb.state`, and `/dev/fb0` writer count.
3. Confirm `/dev/mali0` exists, `/dev/dri` does not, and the live EGL symlink/manifest drift is exactly as described above.
4. Create a timestamped evidence directory under `evidence/pwnage-60000/70000-<UTC>/` and a dated section header for the final report.

### Step 1 — re-verify source and tests

Run and record exact results:

```sh
python3 -m pytest -q tests/pwnage60000
python3 -m pytest -q tests/pwnage53000
python3 -m pytest -q tests/pwnage50000
(cd release/s10plus/gpu && sha256sum -c SHA256SUMS)
```

Also verify `release/s10plus/gpu/*` still matches canonical sources. Fix only concrete defects found by these checks; do not expand scope.

### Step 2 — atomic live deployment

Audit `tools/s10plus/a67/deploy-pwnage60000.sh` before running it. It must:

- stage all files, build the probes on-target, create a hash-verified backup under `/var/backups/nuxel/p60000-<timestamp>/`;
- install atomically, fix the EGL symlinks, install the current `gpu-manifest.json`, and validate the profile **before** restarting the session;
- restart only `nuxel-wayland`, `nuxel-wl-fb` and `nuxel-bridge`;
- verify exactly one `/dev/fb0` writer and `FRAMES_OK`;
- auto-rollback on health failure.

Run it over Wi-Fi SSH:

```sh
tools/s10plus/a67/deploy-pwnage60000.sh root@10.20.30.16
```

If the script's assumptions are stale, make the **minimum** repair to the script, document why, and rerun its own tests. Do not hand-edit live files outside the script's backup/rollback contract.

### Step 3 — live acceptance checks (must all pass)

Run these on the phone and save raw output:

```sh
# 1. fail-closed image gate (run the staged/canonical verifier, not a missing path)
bash /x/nuxel/tools/s10plus/a67/nuxel-gpu-image-verify.sh / \
  --manifest /usr/share/nuxel/gpu-manifest.json

# 2. symlink and manifest truth
readlink /usr/lib64/libEGL_mesa.so.0            # expect libEGL_mesa.so.0.0.0
sha256sum /usr/lib/nuxel/nuxel-session.sh       # expect fe6158...
python3 -c 'import json; d=json.load(open("/usr/share/nuxel/gpu-manifest.json")); print([f["sha256"] for f in d["files"] if f.get("install","").endswith("nuxel-session.sh")])'

# 3. kbase probe with the explicit node
timeout 8 env MESA_KBASE_NODE=/dev/mali0 MESA_LOADER_DRIVER_OVERRIDE=panfrost \
  LIBGL_DRIVERS_PATH=/usr/lib64/dri \
  __EGL_VENDOR_LIBRARY_FILENAMES=/etc/nuxel/egl-kbase.json \
  /usr/lib/nuxel/nuxel-kbase-egl-probe

# 4. desktop/WebKit process evidence
pgrep -a phoc
pgrep -a WebKitWebProcess
for p in $(pgrep -f 'phoc|WebKitWebProcess'); do
  echo "== $p"; grep -c 'libgallium\|libEGL_mesa' /proc/$p/maps 2>/dev/null || true
  ls -l /proc/$p/fd 2>/dev/null | grep -E 'mali0|udmabuf|dmabuf' || true
done

# 5. presenter and profile
cat /run/nuxel-wl-fb.state
/usr/lib/nuxel/nuxel-gpu-status --deep --json
/usr/lib/nuxel/nuxel-gpu-status --json --no-probe
```

Acceptance:

- verifier prints `GPU IMAGE VERIFY: PASS`;
- EGL symlink points at `libEGL_mesa.so.0.0.0`;
- runtime manifest hash equals the installed `fe6158...` session file;
- kbase probe reports Mali-G76 MC12 (Panfrost), not llvmpipe, when `MESA_KBASE_NODE=/dev/mali0` is set;
- phoc/WebKit map the Nuxel Mesa library and hold `/dev/mali0`; no llvmpipe threads in the production path;
- exactly one `/dev/fb0` writer; `FRAMES_OK`;
- profile reports `default_profile=gpu-rendered-shm-presented`, WebKit transport `SHM`, panel path `current-wl-fb`, zero-copy false.

### Step 4 — prove automatic fallback

1. Force a bounded kbase probe failure (for example, temporarily point the probe at a non-existent device or use the repository's documented test switch). Do **not** alter `/dev/mali0`, `/dev/dri` or the framebuffer ownership.
2. Confirm the session selects `software-safe`, the panel still presents, `FRAMES_OK` remains true, and SSH/touch stay alive.
3. Restore the correct configuration and confirm the GPU profile returns.
4. Save before/after state and evidence.

### Step 5 — matched A/B benchmarks

Use the existing benchmark tooling:

```sh
python3 tools/s10plus/a67/bench-pwnage60000.py --help
tools/s10plus/a67/run-pwnage60000-ab.sh
```

Run the documented matched cases at least three times each. Record CPU, frame timing, presenter path, renderer, panel path and transport separately. Do not claim a whole-phone speedup from UI-process CPU numbers. Save raw output under `evidence/pwnage-60000/70000-<UTC>/bench/`.

### Step 6 — cold boot (only if explicitly authorised)

If the owner authorises one cold reboot in the active task:

- use the repository's bounded reboot policy (`tools/beta/reboot-policy.sh`) and the live reachability verifier; do not use an ad-hoc `systemctl reboot`;
- before rebooting, save the exact rollback command and confirm the backup path is readable;
- after boot, verify SSH returns, `FRAMES_OK`, one `/dev/fb0` writer, Home/Settings on Mali, no llvmpipe, and the verifier still passes;
- stop after the first unexplained failure.

If not authorised, mark cold-boot acceptance `OWNER_ACTION_REQUIRED` and do not reboot.

### Step 7 — physical owner tests (diagnostics only)

- Touch, rotation, screen off/on, suspend/resume: exercise only as far as the active session permits; record pass/fail.
- USB-C→HDMI: run read-only `nuxel-typec-diag.sh status --json`, `dmesg`, `nuxel-gpu-status`; no mux/PMIC/PHY/regulator writes. Without a real adapter/EDID, mark `NEEDS_OWNER_TEST`.
- Casting: do not add UI or claim support without real P2P/RTSP/capture/receiver evidence.

### Step 8 — report and handoff

Update `docs/beta-finalization/live/PWNAGE-60000-REPORT.md` with a dated `PWNAGE-70000 live completion` section containing:

- exact commands and exit codes;
- verifier output before/after;
- symlink/manifest before/after;
- process/FD evidence and `FRAMES_OK`;
- fallback test result;
- benchmark tables;
- cold-boot result (or `OWNER_ACTION_REQUIRED`);
- the full capability matrix with honest labels;
- backup path and rollback verification;
- remaining blockers.

Update `PWNAGE-60000-TODO.md` so completed items are checked and blocked items remain explicit.

---

## 4. Required capability labels

Use only these truth levels:

| Capability | Required label after 70000 |
|---|---|
| Phoc Mali rendering | PASS if live maps/FDs/probe pass |
| GTK3 accelerated widgets | PASS/FALLBACK based on real probe |
| GTK4/GSK acceleration | PASS/FALLBACK/UNTESTED |
| Home/Settings WebKit GPU rendering | PASS/FALLBACK/FAIL |
| WebKit SHM presentation | PASS/FAIL |
| WebKit DMA-BUF presentation | BLOCKED (no real DRM main device) |
| Zero-copy scanout | NOT AVAILABLE |
| Framebuffer bridge | PASS/PARTIAL |
| MFC hardware decode | BLOCKED here; 71000 owns it |
| USB-C DP/HDMI | NEEDS_OWNER_TEST/BLOCKED |
| Wireless Miracast | BLOCKED/CANDIDATE |
| LAN/WebRTC screen share | BLOCKED/CANDIDATE |

Do not relabel a blocked capability because a compile or a probe succeeded.

---

## 5. Deliverables

1. Atomic deployment receipt: backup path, installed file hashes, service restart list, health results.
2. Live verifier PASS evidence (or exact failure and rollback proof).
3. Fallback evidence.
4. Fresh A/B measurement files.
5. Updated `PWNAGE-60000-REPORT.md` with a dated 70000 section and a complete capability matrix.
6. Updated `PWNAGE-60000-TODO.md`.
7. Final answer covering: files changed, commands/exit codes, pass/fail/skip counts, live evidence, remaining blockers, rollback path, and owner actions.

## 6. Final response format

Return a concise report with:

- **A. Live state before/after** (kernel, boot ID, profile, EGL symlink, manifest hash, services, `FRAMES_OK`, writer count).
- **B. What was deployed** (files, hashes, backup path).
- **C. Verification results** (verifier, kbase probe, process/FD evidence, fallback).
- **D. Benchmarks** (raw numbers and methodology).
- **E. Cold boot** (PASS or `OWNER_ACTION_REQUIRED`).
- **F. Remaining blockers** (DMA-BUF, zero-copy, HDMI, casting, MFC).
- **G. Rollback** (exact command and tested status).
- **H. Honest overall status**: `FULLY_DONE`, `PARTIAL`, or `BLOCKED_<reason>`.

Do not claim complete because the source tests pass. The live phone state is the deciding evidence.
