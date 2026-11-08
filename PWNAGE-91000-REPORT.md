# PWNAGE-91000 — execution report

## 1. Overall verdict

**PARTIAL.** The full audit, the safe systemd change, the compositor/GPU review, the PenguInterface spoofer upgrade, the NFC false-negative fix, all seven hardware reports and the GPU report are complete. Hardware bring-up remains blocked by vendor firmware/runtime/TEE material and physical test requirements; no boot-time gain is claimed beyond the verified dependency change. No service was disabled, masked or removed. No flash, partition, EFS/IMEI/NV or TEE write was performed.

## 2. Repository, device and provenance

| Item | Value |
|---|---|
| Repo root | `/Users/wicked/x/nuxel` |
| Branch / HEAD | `feature/v0.7.8-beta-pwnage-88000`, `09bd0b9c670680ab7de758ca44f133815a11b1cd` |
| `VERSION` | `v0.8.0-beta` |
| Pre-existing user changes | preserved; all were present before this mission |
| Device | Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820 |
| Live kernel | `4.14.253-gf7194c1d15ed-dirty` (`#5 SMP PREEMPT`, 2026-11-01) |
| Live OS | Fedora Linux 43 (Forty Three), aarch64 |
| Live systemd | `systemd 258 (258.11-1.fc43)` |
| Access | root SSH over Wi-Fi, `192.168.178.167`, key `~/.ssh/wicked_wqn_id_rsa` |
| Before boot ID | `5ab43e24-41c6-45c9-9f92-50d10ca58a8b` |
| After boot ID | `7c9fdaef-9a9d-4968-a76e-c541dbfcea0b` |

## 3. Boot before/after

| Phase | Before | After | Delta |
|---|---:|---:|---:|
| kernel | 3.430 s | 3.459 s | +0.029 s |
| userspace | 12.713 s | 15.840 s | +3.127 s |
| **total** | **16.143 s** | **19.300 s** | **+3.157 s** |
| multi-user.target | 12.712 s | 13.014 s | +0.302 s |
| launcher-ready | 15.722 s | ≈16.2 s | ≈+0.5 s |

The after boot had a slower Wi-Fi online transition (`NetworkManager-wait-online` 9.139 s vs 5.774 s) and a pre-existing `nuxel-audio-session` ALSA retry. The dependency change is verified but **no material boot-to-UI gain is claimed**.

**Applied change:** `services/nuxel-s10/systemd/avahi-daemon.service.d/10-nuxel-boot-order.conf` removes `Wants=`/`After=network-online.target` from avahi while keeping `After=NetworkManager.service wpa_supplicant.service`, `Restart=on-failure`, `RestartSec=3`. Live verification: `systemctl show avahi-daemon -p Wants` empty; reverse dependency of `network-online.target` is only `dnf-makecache.timer`; mDNS joins all interfaces; avahi remains active.

**Deliberately not changed:** `nuxel-fallback.service` (safety gate, waits for the launcher-ready marker), `dnf-makecache.timer` network-online want (off the ordered path; drop-in `Wants=` is merged not cleared by systemd 258), `nuxel-abox-firmware-reload` (off UI path), audio retry (hardware/route race), WebKit launcher spawn (no safe proof).

## 4. Shutdown before/after

| Sample | Window | Evidence |
|---|---:|---|
| Before boot `5ab43e24` | **1.374 s** (1515.826 → 1517.200 s) | real journal, controlled reboot |
| Earlier boot `0112a081` | **1.563 s** (114.362 → 115.925 s) | real journal |
| After boot `7c9fdaef` | **NOT_CAPTURED** | no shutdown performed after capture |

No stop timeout, unmount stall or network teardown delay was observed. Full timeline in `SYSTEMD-GRAPH.md` §6.

## 5. Service changes

| Change | Type | Verification |
|---|---|---|
| avahi drop-in: off `network-online` critical path | R2 runtime unit | `daemon-reload`, restart, mDNS join, `systemctl show`; controlled reboot |
| `/var/lib/nuxel/spoof` created for persistent spoof profiles | R2 directory/provisioning | `tools/s10plus/a33/nuxel-provision-services.sh`, image builder, live dir `nuxel-bridge:nuxel-bridge 0755` |
| NFC live policy refreshed to repo S3NRN82 policy | R2 config | fixed false “firmware missing”; diag now finds verified 151,852-byte blob |
| PenguInterface spoof panel/API | R2 source + PWA | global/per-app, app selector, persistence, scoped reset, launch injection |

No service was added, removed, disabled, masked or hidden. All 31 running units before the reboot were present after it; `nuxel-audio-session` failed once and auto-recovered (pre-existing).

## 6. Compositor / GPU measurements

| Metric | Value | Tier |
|---|---|---|
| EGL/GLES probe | `Mali-G76 MC12 (Panfrost)`, EGL 1.5, OpenGL ES 3.2 Mesa 26.3.0-devel, 536 ms | `PASS_DEVICE_RUNTIME` |
| Phoc renderer | `WLR_RENDERER=gles2`, kbase EGL vendor file, `MESA_KBASE_NODE=/dev/mali0` | `PASS_DEVICE_RUNTIME` |
| Phoc fds | 3× `/dev/mali0`, 1× `/dev/udmabuf`, 1× `dmabuf_udmabuf` | `PASS_DEVICE_RUNTIME` |
| Phoc idle CPU | ≈1.8 % | `PASS_DEVICE_RUNTIME` |
| `nuxel-wl-fb` idle CPU | ≈0.2 % | `PASS_DEVICE_RUNTIME` |
| Display | 1440×3040, 32 bpp, `U:1440x3040p-0`; target FPS 20 | `PASS_DEVICE_RUNTIME` |
| WebKit/GTK WSI | `gpu-rendered-shm-presented`; no DRM main device | `BLOCKED_HARDWARE` |
| Final panel path | CPU screencopy + copy/scale into `/dev/fb0` | `BLOCKED_HARDWARE` (zero-copy) |

No compositor binary was swapped. The highest-value next step is an isolated WebKit/GTK WSI experiment, not a production change. See `GPU-ACCEL-REPORT.md`.

## 7. Cleanup / removal ledger

| Candidate | Earlier decision / evidence | Current locations | Why not removed | Decision |
|---|---|---|---|---|
| Old single-scope PenguInterface spoof implementation | PWNAGE-88000 app-scoped-only design superseded by owner request | `services/nuxel-bridge/src/api.py`, `pwa/nuxel-apps/penguinterface/*` | replaced entirely, not wrapped | **REPLACED** |
| Stale live `/etc/nuxel/nfc/nfc.json` without `firmware_expected` | repo policy already pins S3NRN82 path/hash | live config only | false “firmware missing” | **REPLACED (live)** |
| Duplicate historical deploy trees under `tools/s10plus/a29..a72`, `nuxel-rescue/` | old missions | repo | not proven dead; some are build/test evidence | **REVIEW_REQUIRED** |
| Inactive `nuxel-session.service`, `nuxel-ui.service` | historical units | installed/live | may be fallback/recovery | **REVIEW_REQUIRED** |
| Old graphics WSI canary | docs say it crashed Phoc | docs/build artifacts | historical evidence | **RETAINED** |
| Android camera HAL / vendor camera libs | explicitly `never_install` | config policy | not present | **RETAINED POLICY** |

No executable/config code was deleted without proof. Historical reports and tests were retained.

## 8. Hardware report summary

| Report | Verdict | First blocker | Recommended path | Confidence | Owner input |
|---|---|---|---|---|---|
| `GPU-ACCEL-REPORT.md` | PARTIAL | WebKit WSI / no DRM main device; CPU fb0 present | isolated WebKit WSI experiment; keep current fallback | high | none for analysis; device test for WSI |
| `REPORT-CAMERA.md` | BLOCKED_FIRMWARE | sensor/ISP setfiles + calibration missing | libcamera FIMC-IS handler + vendor setfiles | high | vendor setfiles/firmware |
| `REPORT-GPS.md` | BLOCKED_FIRMWARE | BBD patch + LHD/GPS runtime missing | native BBD/LHD decoder or isolated vendor runtime | high | patch firmware + outdoor test |
| `REPORT-NFC.md` | BLOCKED_KERNEL | kernel NFC class down; protocol unverified | native `/dev/sec-nfc` transport + NCI | high | physical NDEF tag |
| `REPORT-ROTATION.md` | BLOCKED_VENDOR_RUNTIME | SSP down; raw accel 0,0,0 | native SSP/BBD handshake or isolated runtime | high | physical tilt test |
| `REPORT-FINGERPRINT.md` | BLOCKED_SECURE_PROVIDER | no TEE-backed qbt2000 provider | vendor TEE/TA secure provider | high | TEE/OEM material |
| `REPORT-MOBILE-NETWORKING.md` | NOT_SUPPORTED_ON_DEVICE / BLOCKED_FIRMWARE | no CP transport/ModemManager Shannon plugin | native Shannon CP + plugin/daemon | high | active SIM + CP docs |
| `REPORT-LEDS.md` | PARTIAL | no notification/RGB LED class | bounded torch + AMOLED edge overlay | high | visual torch confirmation |

## 9. PenguInterface spoof result

- Global and per-app scopes are supported. Global is the fallback for every native app launched through the bridge; per-app config wins.
- App IDs are loaded from the canonical registry (`spoof.apps` RPC; 53 entries live) and shown in a select.
- Fields persist in `/var/lib/nuxel/spoof/profile.json` (mirrored to `/run/nuxel/spoof/profile.json`) and are refilled when an app is selected, including after reboot.
- Reset is scoped: per-app reset leaves other apps and global intact; global reset leaves apps intact; an explicit “Reset all” exists.
- Global values appear in the “Current user agent / Current uname / Current /etc/os-release” rows above the form.
- Launch injection writes a per-scope runtime profile and sets `LD_PRELOAD`/`NUXEL_SPOOF_PROFILE` only for non-Flatpak native launches. Proof: `systemd-run` with the generated profile produced `Linux spoof-launch-node 9.9.9-spooftest ...` and `NAME=SpoofTestOS`; un-injected `uname` stayed real.
- The misleading os-release bug in the old implementation (storing text where the library expects a path) was fixed.

## 10. Test matrix

| Test set | Result | Count | Tier |
|---|---|---:|---|
| `tests/pwnage91000` (spoof/contracts) | PASS | 16 | `PASS_HOST` |
| `tests/pwnage90000/test_pwnage90000.py` | PASS | 21 | `PASS_HOST` |
| `tests/pwnage89000` | PASS | 11 | `PASS_HOST` |
| `tests/pwnage65000` (NFC service) | PASS | 17 | `PASS_HOST` |
| Spoof device RPC matrix (global/app/persist/reset) | PASS | 19 checks | `PASS_DEVICE_RUNTIME` |
| Spoof launch env + library proof | PASS | 1 proof | `PASS_DEVICE_RUNTIME` |
| Avahi dependency/mDNS | PASS | live | `PASS_DEVICE_RUNTIME` |
| Controlled reboot + spoof persistence | PASS | live | `PASS_DEVICE_RUNTIME` |
| NFC policy refresh / diagnostic | PASS | live | `PASS_DEVICE_RUNTIME` |
| LED torch control path | PASS (control); physical `NEEDS_OWNER_TEST` | live | `PASS_DEVICE_RUNTIME` |
| Hardware diag selftests | no fixture corpus installed (`0 fixtures`) | 6 tools | `NOT_TESTED` |
| Camera physical frame | not possible | — | `BLOCKED_HARDWARE` |
| GNSS physical fix | not possible | — | `BLOCKED_HARDWARE` |
| NFC physical tag | not performed | — | `BLOCKED_HARDWARE` |
| Fingerprint enrollment | not possible | — | `BLOCKED_HARDWARE` |
| Cellular data/SMS/voice | not possible | — | `BLOCKED_HARDWARE` |

Static/syntax checks: `api.py` AST, `node --check spoof.js`, `sh -n` provisioning, `bash -n` image builder, `systemd-analyze verify` on the changed units, `verify-service-graph.py` (`units=17 problems=0 warnings=5`, warnings pre-existing/VM-only).

## 11. Known regressions, limitations and risks

- **No material boot-time improvement measured.** The avahi dependency was removed from the ordered path, but `nuxel-fallback` (safety gate) and the launcher/WebKit readiness still dominate `multi-user.target` and first UI.
- `nuxel-audio-session` has a pre-existing ALSA `set_hw_params: Invalid argument` retry; it recovers but adds boot churn. Not changed.
- SHA/EGL/WSI: no production dma-buf path; final panel is CPU-copy.
- Flatpak ignores host `LD_PRELOAD`; spoof injection is claimed only for non-Flatpak native launches.
- WebKit/PWA user-agent spoofing is display/effective-identity only; no WebKit UA override was added.
- Hardware reports are research/roadmaps; no driver/firmware/TEE deployment was attempted.
- The after-boot shutdown is `NOT_CAPTURED`.
- The before/after boot samples are not workload/thermal matched.

## 12. Rollback

All backups are on the device:

| Item | Backup |
|---|---|
| Bridge API | `/var/lib/nuxel/pwnage-91000-backup-20261108T091827Z/bridge/api.py` |
| PenguInterface HTML/JS/CSS | `/var/lib/nuxel/pwnage-91000-backup-20261108T091827Z/pengu/` |
| Avahi drop-in | `/var/lib/nuxel/pwnage-91000-backup-20261108T092217Z/avahi/10-nuxel-boot-order.conf` |
| Live NFC policy | `/var/lib/nuxel/pwnage-91000-backup-20261108T093020Z-nfc.json` |

Rollback commands:

```sh
# Bridge + PWA
cp -a /var/lib/nuxel/pwnage-91000-backup-20261108T091827Z/bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py
cp -a /var/lib/nuxel/pwnage-91000-backup-20261108T091827Z/pengu/index.html /usr/share/nuxel/pwa/nuxel-apps/penguinterface/index.html
cp -a /var/lib/nuxel/pwnage-91000-backup-20261108T091827Z/pengu/spoof.js /usr/share/nuxel/pwa/nuxel-apps/penguinterface/js/spoof.js
cp -a /var/lib/nuxel/pwnage-91000-backup-20261108T091827Z/pengu/pengu.css /usr/share/nuxel/pwa/nuxel-apps/penguinterface/css/pengu.css
systemctl restart nuxel-http-bridge.service

# Avahi ordering (restores the previous network-online dependency)
cp -a /var/lib/nuxel/pwnage-91000-backup-20261108T092217Z/avahi/10-nuxel-boot-order.conf \
  /etc/systemd/system/avahi-daemon.service.d/10-nuxel-boot-order.conf
systemctl daemon-reload
systemctl restart avahi-daemon.service

# NFC policy
cp -a /var/lib/nuxel/pwnage-91000-backup-20261108T093020Z-nfc.json /etc/nuxel/nfc/nfc.json
```

Optional: remove `/var/lib/nuxel/spoof` and the runtime files if the owner wants no persisted spoof state.

## 13. Evidence paths

- `diagnostics/pwnage-91000/baseline/` — before boot, shutdown, critical chain.
- `diagnostics/pwnage-91000/after/` — after boot, shutdown window.
- `diagnostics/pwnage-91000/hardware/` — camera/GNSS/NFC/sensors/LED/modem diagnostics and GPU/fingerprint evidence.
- `diagnostics/pwnage-91000/tests/` — hardware selftest output.
- `diagnostics/systemd/boot-5ab43e24-*.svg`, `boot-7c9fdaef-*.svg`.
- `SYSTEMD-GRAPH.md`, `GPU-ACCEL-REPORT.md`, and the seven `REPORT-*.md` files at the repo root.
