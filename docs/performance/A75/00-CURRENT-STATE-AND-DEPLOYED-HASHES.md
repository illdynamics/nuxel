# A75 — Current State and Deployed Hashes

Captured `2026-10-26 16:15 CET` against the running phone over the CDC-ACM
Live Console (`/dev/cu.usbmodem2101`, serial `NUXEL-S10PLUS-0001`). This is the
only recovery channel and was **not** disconnected during this mission.

## Identity
- Device: Samsung Galaxy S10+ `SM-G975F` / `beyond2lte` / Exynos 9820
- OS: Fedora 43 ARM64 userspace (`rpm` shows fc43 aarch64 packages)
- Kernel: `4.14.253` (downstream, unchanged — no flash attempted)
- Compositor: `phoc 0.54.0` (headless) + `nuxel-wl-fb` (single framebuffer writer)
- WebKit: `webkit2gtk4.1 2.54.1`
- NetworkManager 1.54.3 + wifi plugin; wpa_supplicant 2.11; bluez 5.87 (installed)
- Repo: `main` @ `d545289`, clean working tree

## Boot / stability
- boot_id: `9ff44f39-69e4-4444-bb47-24ca923a0d69` (same before and after all work)
- uptime continued throughout; no reboot was performed
- Failed units after work: only `NetworkManager-wait-online.service`
  (expected transient: no link at boot; unrelated to the bridge)

## P0 D-Bus / bridge provider state (before → after)
| Item | Before | After |
|---|---|---|
| nuxel-bridge.service | failed at baseline (crash-loop) | active, NRestarts=0 |
| nuxel-bridge host version | 0.6.1-beta (env pin) | **0.6.5-beta** (matches repo) |
| nuxel-http-bridge host version | 0.4.0-alpha (env pin) | **0.6.5-beta** (matches repo) |
| bridge_version protocol | 1 | 1 (unchanged) |
| Wi-Fi scan timeout bound | absent | `SCAN_REQUEST_TIMEOUT_SECONDS=5` present |
| Shared PWA radio/privacy honesty fallback | absent (old mock-success) | present |

## Deployed file hashes
Machine-readable record: `docs/performance/A75/deployed-hashes.json`.

Deployed after this mission (all match repo bytes):
- `/usr/lib/nuxel/nuxel-bridge/bridge.py` → `6fb99166…6c7f0`
- `/usr/lib/nuxel/nuxel-bridge/api.py` → `64be1b6a…9f25227`
- `/etc/systemd/system/nuxel-bridge.service` → `9e04be9a…1f8ce0`
- `/etc/systemd/system/nuxel-http-bridge.service` → `90e58459…53fd8e`
- `/etc/nuxel/bridge-version.json` → `b17a96a2…c33fca`
- `/usr/share/nuxel/pwa/nuxel-common/bridge-version.json` → `b17a96a2…c33fca`
- `/usr/share/nuxel/pwa/nuxel-common/bridge.js` → `1b409e04…0b75e`

Unchanged (already matched repo):
- `/usr/share/nuxel/nuxel-home/js/qs.js` → `064bd03a…d6a192`
- `/usr/share/nuxel/nuxel-home/js/bridge.js` → `b84f2789…122585`
- `/usr/lib/nuxel/nuxel-bridge/system_indicators.py` → `d68c3631…b4a5a`

## Recovery path
USB CDC-ACM Live Console is the only independent recovery route today (no
verified Wi-Fi/SSH was active before the fix). A rollback helper is at
`docs/performance/A75/rollback-a75-bridge.sh`; each changed file also has a
`.nuxel-rollback` copy preserved on the device by the deploy tool.
