# PWNAGE-52000 — task / evidence tracker

Live target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora 43 ARM64,
Exynos 9820, vendor kbase Mali-G76, Phoc on DPU20 fbdev.
Kernel: `4.14.253-gf7194c1d15ed-dirty #8` (2026-11-01 10:16:28 UTC).
Post-reboot normal boot: `2026-11-01T12:34+01:00`, no `androidboot.mode=charger`.

| # | Task | Status | Evidence |
|---|---|---|---|
| 1 | Baseline: repo, device, services, GPU raw data, app inventory | **PASS** | `evidence/pwnage-52000/baseline/device-baseline.txt` |
| 2 | Settings no sideways page pan, tab rail isolated | **PASS** | 5 portrait widths + 2 landscape; `tests/pwnage52000/test_settings_dom.py` |
| 3 | Duplicate `display-state` IDs removed + uniqueness tests | **PASS** | `screen-state`, `graphics-acceleration-state`, `external-display-state`; no duplicate IDs in Settings or any PWA |
| 4 | All installed PWAs phone-responsive | **PASS (layout)** | 30/30 at 320×640, 360×760, 760×360; `app-responsiveness-matrix.md` |
| 5 | Native GTK/Flatpak inventory | **PASS (inventory) / BLOCKED (Flatpak)** | Flatpak sandbox `unshare -U` EPERM; no Flatpak claimed working |
| 6 | Exact vendor LPM source audit | **PASS** | `PWNAGE-52000-LPM-AUDIT.md` |
| 7 | Exact-source touch LPM patch | **PASS (source)** | `kernel/s10plus/patches/0006-sec-ts-lpm-bind.patch` + `.required` |
| 8 | BOOT/kernel flash + cold charger-boot proof | **BLOCKED_OWNER/TWRP** | `adb devices -l` empty on 2026-11-01; no partition write attempted |
| 9 | Gated LPM userspace fallback | **PASS (source)** | owner locks, ≥120 s uptime, charger + `Charging`, 900 s cooldown, once/boot |
| 10 | Lockscreen hides DOM top bar/nav and native dock | **PASS** | live `NAV_DOCK_START visible=0 lock=unknown`, lock→HIDE, unlock→SHOW; screenshots |
| 11 | Lock/unlock state verified by root provider | **PASS** | host unlock now calls `NuxelSecurityLock.verifyUnlock()`; lock-state false/true transitions |
| 12 | Top-bar icons hidden when OFF/unsupported | **PASS (source + live providers)** | Wi-Fi radio state, BT powered, Location enabled, NFC supported/on |
| 13 | Per-icon visibility document + Screen Settings card | **PASS (source)** | `/etc/nuxel/display/statusbar-icons.json`, `statusbar-icons.js`, 11 toggles |
| 14 | Quick Settings third privacy row | **PASS (layout/provider plumbing)** | row hidden compact, visible expanded; 4 real providers |
| 15 | NFC real provider | **UNSUPPORTED_ON_DEVICE** | `CONFIG_NFC` unset; tile disabled with blocker |
| 16 | Fingerprint auth policy | **UNSUPPORTED_ON_DEVICE** | driver present, no TEE provider; toggle refused honestly |
| 17 | Camera privacy gate | **PASS (policy) / BLOCKED_FIRMWARE (frames)** | block/allow round-trip; camera capture unsupported |
| 18 | Microphone mute | **UNSUPPORTED_NO_CAPTURE_SOURCE** | no PipeWire capture source; tile disabled |
| 19 | GPU utilisation/clock units and shared-memory accounting | **PASS** | live 11652 KiB from kbase `used_pages` × 4096; MHz from Mali clock |
| 20 | `(ACC)`/partial label truth | **PASS** | live verdict `PARTIAL`; Phoc accelerated, WebKit software |
| 21 | Graphics Acceleration block before external connectors | **PASS** | independent 3 s graphics request, 4 s connector request |
| 22 | Bounded Graphics Test | **PASS** | owner-only `graphics.test`, 25 s UI bound, real Wayland probe returns EGL failure |
| 23 | Tests | **PASS (new)** | `pytest -q tests/pwnage52000` 39 passed; p49000 updated 53 passed |
| 24 | Clean ARM64 rootfs build | **NOT RUN — HOST DISK 1.8 GiB** | device-built ARM64 binaries + staged deployment used instead |
| 25 | Deployment + reboot | **PASS** | post-reboot SSH in 48–66 s; seven services active; touch registered; guard NORMAL |

## Honest blockers

1. **Charger-attached cold boot** is not proven on hardware. The exact-source
   kernel patch is prepared, but TWRP was not visible and no BOOT write is allowed
   without the recovery gate. The userspace fallback is only a one-shot reboot.
2. **Flatpak** cannot start on this kernel (`unshare -U` EPERM / `statx` failure).
3. **NFC** is disabled in the running kernel (`CONFIG_NFC` unset).
4. **Fingerprint unlock** has a qbt2000 device but no verified TEE provider.
5. **Microphone capture** has no PipeWire source, so the privacy tile stays
   disabled even though the policy document exists.
6. **WebKitGTK** remains software; only Phoc is kbase-accelerated.
