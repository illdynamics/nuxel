# PWNAGE-54000 — Nuxel Orientation + Application Repair

Device: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora ARM64, Phoc 0.54,
wlroots 0.19, `HEADLESS-1` output, `nuxel-wl-fb` as the sole `/dev/fb0` writer.

## 1. Root cause

### Orientation
1. **The working rotation path was already `wlr-randr` → Phoc `HEADLESS-1`.**
   The recovered mapping is `0→normal`, `90→270`, `180→180`, `270→90`.
   Portrait uses scale 2 (360x760 logical); landscape uses scale 1
   (1520x720 logical). The mapping is not a guess: raw `/dev/fb0` captures were
   correlated against Phoc `grim` captures for all four poses (0.998–1.000).
2. **The display backend discovery was broken.** `apply.py` used
   `subprocess.run(["command", "-v", "wlr-randr"])`; `command` is a shell
   builtin, so the check always failed and the daemon could report
   `transform_available=false` even when `wlr-randr` was installed. It now uses
   `shutil.which()`.
3. **The UI path was preference-biased.** Quick Settings short-tap toggled
   `auto` ↔ `portrait`. Selecting Auto with no sensor could look successful,
   and a locked landscape mode was easy to lose. The tile now performs a
   predictable 90° Locked rotation on tap and exposes all seven modes on
   long-press. Auto with no live sensor is amber/degraded, never green.
4. **Auto is hardware-blocked, not policy-blocked.** The LSM6DSO sits behind a
   BCM47752 sensor hub. The hub is powered and the accelerometer enable bit can
   be set, but `raw_data` stays `0,0,0` because the Samsung/Broadcom LHD patch
   loader is absent; `initialize_mcu` times out. The daemon now probes the real
   sysfs source, normalizes a non-zero vector to 1 g, and reports the precise
   MCU reason. `manual` is never marked `auto_capable`.
5. **Systemd was historically a oneshot status command.** The current unit is
   `Type=simple`, runs `daemon`, restarts on failure, and owns the continuous
   auto loop. Reboot restored `Locked (LS)` and sequence 151 in the live test.
6. **Touch is one owner.** Phoc 0.54 does not rotate `wlr_touch`; the
   `libnuxel-libinput-path.so` LD_PRELOAD applies exactly one libinput
   calibration matrix from `/run/nuxel-orientation/input.json`. The corner math
   is unit-tested. `nuxel-wl-fb` never rotates touch.
7. **VNC cached the old RFB size.** wayvnc 0.9.1 keeps the transform used for
   RFB ServerInit. The remote-sync helper now calls
   `wayvncctl detach` + `attach wayland-0` + `output-set <discovered-output>` on
   sequence change; this updates portrait 720x1520 ↔ landscape 1520x720 without
   restarting wayvnc or dropping the client (verified: connection stayed open).

### Application/performance root causes
- Native launch waited up to 10 s for a toplevel; the UI now gets a response in
  ~0.22 s and a background thread records the eventual surface.
- `/run/nuxel-home.state` grew without bound (286 KB/hour); pwa-host now rotates
  it at 256 KiB and stops logging every successful status read.
- Files listed a directory with 4+ stat calls per entry and re-sorted with more
  stats; it now uses one `os.scandir` stat per entry.
- The dialer called `mm_modem_create_call()` with `MMSmsProperties` (wrong type).
- Contacts deleted a contact and then read its freed id (use-after-free); the
  hash table keys also dangled. Both are fixed.
- Clock used a generated WebAudio beep; it now plays `/assets/nuxel-alarm.mp3`
  with a beep only as a fallback.
- Calendar `<input type="time">` did not request a numeric OSK; it now uses
  text fields with `inputmode="numeric"` and HH:MM normalization.

## 2. Recovered transform / output evidence

| Mode | Effective | Transform | Logical | fb-vs-grim |
|---|---:|---|---:|---|
| Locked (PT) | 0 | `normal` | 360x760 | direct, 0.998 |
| Locked (LS) | 90 | `270` | 1520x720 | fb rotated 90°, 0.999 |
| Locked (RPT) | 180 | `180` | 360x760 | fb rotated 180°, 1.000 |
| Locked (RLS) | 270 | `90` | 1520x720 | fb rotated 270°, 0.999 |

The active output is discovered at runtime; `DSI-1`/`HEADLESS-1` are not
hardcoded. `nuxel-wl-fb` remains the only `/dev/fb0` writer.

## 3. Files changed

Orientation:
- `configs/nuxel/orientation/orientation.json` — sensor-hub source, output auto,
  historical transform map retained, truthful touch status.
- `services/nuxel-orientation/nuxel-orientationd` — sensor-hub diagnostics,
  `sensor` command, reboot-safe restore, truthful status.
- `services/nuxel-orientation/nuxel_orientation/sensors.py` — real sysfs
  accelerometer source + zero/implausible rejection.
- `services/nuxel-orientation/nuxel_orientation/apply.py` — `shutil.which`,
  live readback and geometry verification (recovered working backend).
- `services/nuxel-orientation/tests/*` — sensor-hub, rollback and touch-matrix
  tests.
- `services/nuxel-remote-desktop/bin/nuxel-orientation-remote-sync` — VNC
  `output-set` transform refresh + per-session XRDP reporting.

UI/performance:
- `pwa/nuxel-home/js/qs.js` — tap = 90° Locked; long-press = seven modes;
  degraded Auto rendering; no optimistic success.
- `pwa/nuxel-home/js/app.js` — Back at app root closes gracefully to Home.
- `pwa/nuxel-home/js/apps.js` — lazy icon decoding, Clipper registration,
  Pengu icon asset.
- `pwa/nuxel-home/css/launcher.css`, `status-bar.css` — content-visibility,
  reduced-motion, degraded Auto badge.
- `pwa/nuxel-home/sw.js` — cache `v82-p54000-apps`.
- `pwa/nuxel-apps/settings/settings.js` — sensor-hub reason, slower dev poll.
- `pwa/nuxel-apps/files/*` — “Copy text” for text files only + faster listing.
- `pwa/nuxel-apps/browser/js/browser.js` — address bar select-all on tap.
- `pwa/nuxel-apps/calendar/*`, `clock/*` — numeric OSK + alarm asset.
- `pwa/nuxel-apps/clipper/*` — new clipboard manager.
- `services/nuxel-bridge/src/api.py` — non-blocking native launch + env cache.
- `services/nuxel-bridge/src/pwa_store.py` — one-stat directory listing.
- `tools/s10plus/a45/nuxel-pwa-host.c` — bounded diagnostics log.
- `shell/nuxel-shell/nuxel-contacts/main.c` — “New contact”, SIM mirror
  import/sync/save, dark mode, UAF fix.
- `shell/nuxel-shell/nuxel-messages/main.c` — dark mode, SIM mirror import/sync.
- `shell/nuxel-shell/nuxel-dialer/main.c` — `MMCallProperties` fix, dark mode.
- `pwa/nuxel-common/app-registry.json`,
  `shell/nuxel-home-native/nuxel_home/app_registry.json` — Clipper + Pengu icon.
- `assets/nuxel-app-penguinterface.png` — 512x512 optimized owner asset.
- `images/s10plus/build-phone-rootfs-inside-fedora.sh` — builds/installs the
  three native apps and validates Clipper in the rootfs.
- `tools/s10plus/a67/deploy-pwnage54000-apps.sh` — safe Wi-Fi SSH deploy/rollback.
- `docs/A49/OWNER-TEST-ORIENTATION.md`,
  `docs/a54-reliability/ORIENTATION-MATRIX.md`,
  `docs/a69/ROTATION-HARDWARE-BOUNDARY.md` — live truth updated.

## 4. Automated tests

- `python3 -m pytest -q services/nuxel-orientation/tests` → **60 passed**
  (policy, aliases, apply/readback, touch matrices, rollback, sensor hub).
- `python3 tests/pwnage54000/test_orientation_ui.py` → **0 failing** (7 exact
  labels in QS/Settings/config, tap does not select Auto).
- `python3 tests/pwnage54000/test_app_contracts.py` → **0 failing** (browser,
  Back, numeric OSK, alarm asset, Files copy-text, Clipper, Contacts SIM,
  dark mode, dialer call properties, launch latency, log cap).
- Static: Python `py_compile` and `node --check` for every changed JS file.

## 5. Live device tests (SM-G975F)

- All seven modes applied through the Bridge; each returned `success=true`,
  correct effective angle, transform, scale and logical geometry.
- Locked PT/LS/RPT/RLS: framebuffer-vs-Phoc correlation proves 0/90/180/270.
- Reboot: saved `Locked (LS)` restored, `display_verified=true`, sequence 151.
- VNC: new connection in landscape reported RFB **1520x720**; after portrait +
  `output-set` it reported **720x1520**. `wayvnc` stayed active.
- XRDP: `xrdp` and `xrdp-sesman` listen on 3389; no RDP client was available
  on this host, so live session resize with Jump Desktop is **NOT verified**.
- Native launch: HTTP `apps/exec` returned in **0.22 s** (was up to 10 s).
- Idle CPU after final reboot: **98% idle**, load average dominated by kernel
  D-state TrustZone workers (not userspace CPU); `nuxel-home.state` stayed
  ~1.9 KB instead of growing without bound.
- Sensor hub: `raw_data=0,0,0`, MCU powered yes, accelerometer enable yes,
  `initialize_mcu` timeout; Auto is reported degraded, not successful.

## 6. Remaining limitations (honest)

1. **Auto (FULL/PT/LS) cannot rotate on this image.** The BCM47752 sensor hub
   needs the owner-supplied Broadcom/Samsung LHD patch loader (or a lawful
   reimplementation of the SSP protocol) before `raw_data` streams. The policy,
   debounce, allowed-angle sets and last-good hold are implemented and tested;
   the hardware source is absent. No manual/diagnostic source is marked Auto.
2. **Physical finger touch test was not performed by the agent.** The matrix
   read-back and corner math are verified; the owner must still touch all
   corners/edges/dock/OSK on the glass.
3. **XRDP / Jump Desktop dynamic resize was not tested with a real client.**
   xorgxrdp 0.10 rejects native output rotation in this image; the helper
   reports that per session and never logs out or kills applications. A
   supported fallback is axis-correct geometry where the backend allows it.
4. **VNC clients without RFB DesktopSize support** keep their window and may
   letterbox; the server still mirrors the real Phoc session and pointer map.
5. Kernel/firmware/boot/partition changes were not made and are out of scope.

## 7. Deploy / rollback

```sh
tools/s10plus/a67/deploy-pwnage54000-apps.sh nuxel@192.168.178.167
```

It backs up to `/var/backups/nuxel/p54000-apps-<ts>`, records that path in
`/run/nuxel-p54000-apps-backup-dir`, compiles natively on the phone, installs only
userspace files, restarts only orientation/Bridge, and prints the exact rollback
commands. It never writes `/dev/fb0`, BOOT, firmware or partitions.
