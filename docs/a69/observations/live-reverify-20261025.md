# A69 (18000) — Live re-verification session

**When:** 2026-10-25 15:24–15:50 CEST
**Host:** macOS (infranux, Darwin arm64) — note: host is macOS, not Fedora; the
phone is the Fedora device.
**Connection:** USB CDC-ACM Live Console `/dev/cu.usbmodem101` (VID 0x18d1
PID 0x4ee7, serial NUXEL-S10PLUS-0001), verified `REACHABLE` with a framed
SHA-256 command (`id; echo NXL-REACH-OK`).
**Repo commit:** `fe3ccd0` (main) — A69 fixes already merged. Working tree also
carries uncommitted A70 lockscreen-indicator WIP (preserved, untouched).

## Live identity (measured)
- Kernel: `Linux 4.14.253 #15 SMP PREEMPT aarch64`
- Userspace: `Fedora release 43 (Forty Three)`
- Uptime at capture: ~1h50m–1h57m; load average 12.3 → 13.6
- Boot: `309f2def-...` (third boot today, started 13:46:48 CET)

## Key facts that changed vs the 2026-10-24 session
1. **Network is UP now.** `wlan0` connected with default route via
   `192.168.178.1`; DNS resolves. `curl https://www.google.nl` → HTTP 301
   (TLS handshake succeeded); `curl https://tile.openstreetmap.org/4/8/5.png`
   → HTTP 200, `image/png`, 25 572 bytes, `access-control-allow-origin: *`.
2. **Maps app**: deployed on device, hashes match repo; a one-tap OSM tile
   preset was added this session and deployed (see FINAL-STATUS §A69-05).
3. All A69 shell fixes (battery / single nav / foreground) remain present and
   byte-identical to the committed source (hashes below).

## Live hash verification (device == repo HEAD)
| File | Device sha256 | Repo sha256 | Match |
|---|---|---|---|
| css/style.css | acfb751e…816cb5 | acfb751e…816cb5 | yes |
| js/app.js | ed800ef0…2db942ee4 | ed800ef0…2db942ee4 | yes |
| js/lockscreen.js | 94849e33…8a391eafc2e4c517 | 94849e33…8a391eafc2e4c517 | yes |
| js/navigation.js | 87098908…3b222039ca4d7 | 87098908…3b222039ca4d7 | yes |
| maps/index.html (pre) | 152d5817…9718a4e | 152d5817…9718a4e | yes |
| maps/js/maps.js (pre) | 4190a630…5bb4589 | 4190a630…5bb4589 | yes |

## Live runtime evidence (from /run/nuxel-home.state, current boot)
- `HOST_CONFIG_GET name=battery-capacity bytes=3` at launcher-ready +0s
- `NUXEL_INPUT BATTERY_HOST_READY level=99 charging=1` at +3s
- `NUXEL_INPUT NAVOWNER native-dock=present` (×7 across reloads)
- `NUXEL_INPUT STATUSBAR_OVERLAP_CHECK cells=2 overlaps=none`
- `HOST_STATUS_INDICATORS ok` (repeated)
- fb-owner: `owner=nuxel-wl-fb stage=LAUNCHER_DISPLAY_OWNER reason=single_owner_takeover`

## Hardware blocker re-confirmation (measured this session)
- **Audio:** ALSA `beyond-madera` (index 0) + `abox_vdma`/`abox_dump`;
  `nuxelctl audio status` = `BLOCKED_FIRMWARE` (cs47l93-dsp{1,2} + cs35l40-dsp
  {1,2} .wmfw/.bin absent); UCM `HiFi.conf` absent; no PipeWire/WirePlumber/
  PulseAudio daemon; no `aplay`/`amixer`.
- **Rotation:** `raw_data` = `0,0,0`; dmesg `[SSP]: ... GPS: false` +
  `[SSPBBD]: ssp_down == true`; orientationd `auto_capable: false`.
- **GNSS:** no `/dev/gnss*`/`gps*`; SSP GPS:false.
- **NFC:** `/sys/class/nfc` only has `nfc_support` (empty read); `sec_nfc
  nfc_support_show:` prints nothing; no bound device/firmware.
- **BT:** `rfkill`: bcm43xx Bluetooth `Soft blocked: yes`, Hard: no; no
  `/dev/hci*`; no `btmgmt`/`hciconfig`/`bluetoothctl`; no BCM BT firmware in
  `/lib/firmware` (only bcmdhd WiFi blobs).
- **VLC/mpv:** not installed; `dnf`/`yum` absent (only `rpm`, 463 pkgs; repos
  present but unusable without dnf). No safe offline install path exists.

## Performance / thermal snapshot (measured, not fabricated)
- `top -bn1`: WebKitWebProcess 92.9% CPU (~247 MB RSS), nuxel-pwa-host 42.9%,
  nuxel-wl-fb 35.7%, phoc 28.6% — software-rendered WebKitGTK/Phoc path, no
  DRM/EGL on this kernel.
- Memory: 7 598 228 kB total, 6 728 308 kB available, 0 swap.
- Thermal: BIG 59°C, MID 51°C, LITTLE 51°C, G3D 46°C, ISP 48°C, battery 26.6°C —
  within normal envelope, no throttling observed.

## What was changed on the phone this session
Only three Maps PWA files (low-risk userspace, no kernel/firmware/boot/package):
- `/usr/share/nuxel/pwa/nuxel-apps/maps/index.html` (added OSM preset button)
- `/usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js` (added opt-in OSM preset handler)
- `/usr/share/nuxel/pwa/nuxel-apps/maps/sw.js` (cache name bumped v1→v2)

Pre-patch copies + hashes backed up to `/var/lib/nuxel/a69-backup-maps/`.
Launcher reload via `action reload-launcher` (non-disruptive). Post-deploy:
services healthy, nav single-owner intact, HTTP endpoint serves new content.
