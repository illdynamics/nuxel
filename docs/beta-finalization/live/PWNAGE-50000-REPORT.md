# PWNAGE-50000 — owner regression repair (live S10+)

Date: 2026-11-01
Target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora 43 ARM64, kernel 4.14.253
Live path: Wi-Fi SSH over `192.168.178.167` with `~/.ssh/wicked_wqn_id_rsa`

## Verified on the handset

| Area | Result |
|---|---|
| One full top bar | The stale native `nuxel-statusbar` overlay is no longer started (binary moved aside). The DOM bar is the only top bar and shows clock, signal, Wi-Fi, location, Bluetooth, NFC, sound, USB/transfer, remote and battery. |
| Better Wi-Fi glyph | The old DOM bar uses `01-wifi.png` from the quicksettings icon pack. |
| Quick Settings gesture | It opens only for a pull that begins in the top-edge band. Drawer scrolling no longer opens the shade. |
| Three-button dock | New `nuxel-navdock` deployed with timer-driven long-press, one haptic per gesture and tap-slop cancellation. |
| Short Back / hold Back | Short Back routes to in-app Home back; hold Back sends `back-long` (foreground close only). |
| Scrolling in app drawer | Touch/scroll guards raised to 12 px / 24 px; a scroll can no longer become a tile launch. |
| Flashlight | Provider now uses the real `/sys/class/camera/flash/rear_flash` node and writes `2015` (300 mA torch) / `0`. Verified `s2mpb02_store ... torch brightness set (300mA)`. |
| DND | `dnd_provider` + notification suppression deployed; toggle verified through the bridge. |
| Screenshots | `nuxel-pwa-host` now converts the screencap PPM to a real PNG. Recent captures are valid 720x1520 PNGs (PIL decode OK). Zero-byte failed captures are filtered from Gallery and the old zero-byte files were removed. |
| Gallery video | Gallery offers the native player fallback and uses mpv (verified playback of the boot MP4). WebKit/HTML5 codec failures are still reported honestly. |
| VLC | The packaged VLC 3.0.24 aarch64 build cannot load its Qt interface/create a Wayland vout. `nuxel-vlc-fallback` tries VLC briefly then opens the same file in mpv. VLC's missing FFmpeg decoder plugin was also installed so its engine can decode H.264. |
| Native icons | Firefox, VLC, Stremio and GNOME native app icons are served from `/assets/native-app-icons/`. |
| USB file transfer | MTP now enumerates on macOS (`mtp-detect` / `mtp-files`), and Gallery/Pictures/Videos/Downloads are bind-mounted under the explicit `/home/nuxel/Shared` MTP root. 14 objects were listed over USB. Finder does not natively mount MTP; use MTPLX/OpenMTP. |
| Settings pages | Mobile network, Camera and Sensors tabs use the bridge `system.diagnostics` endpoint and show real driver state. Camera now reports `BLOCKED_FIRMWARE` instead of a false sensor-name failure. |
| Idle cost | Software scanout capped at 24 fps via `nuxel-wl-fb.service.d/15-idle-fps.conf` instead of 30 fps. |
| Boot-time reverts | The legacy `stage36000` apply was overwriting the live session file on every boot. The staged session/PWA copies were updated so p50000 survives reboot. |

## Honest blockers

- **NFC**: controller chardev/subsystem exist, but firmware is missing and there is no NFC stack → `BLOCKED_FIRMWARE`.
- **Camera**: FIMC-IS V4L2 nodes and sensor names exist, but no camera firmware blobs are present → `BLOCKED_FIRMWARE`. No frame was claimed.
- **Mobile network**: no CP host interface and no ModemManager Shannon plugin → `NOT_SUPPORTED_ON_DEVICE` on this userspace/kernel pair.
- **Sensors**: SSP sensorhub/devices enumerate, but the hub is down (`ssp_down == true`) and raw values remain zero → `present-unreadable`. Settings shows that truth; no synthetic readings are produced.
- **Fingerprint**: no verified TEE/fprintd provider. Unsupported with PIN fallback.
- **Flatpak**: `CONFIG_USER_NS=y` and `CONFIG_OVERLAY_FS=y` are being built into a patched 4.14 kernel. Flatpak cannot be claimed until that kernel is flashed and `bwrap` + an actual ARM64 Flatpak launch pass.

## Build / flash note

The patched kernel is built in `/root/kbuild` with `CONFIG_USER_NS=y` and
`CONFIG_OVERLAY_FS=y`. The boot partition is `sda14` (55 MiB, `ANDROID!` v1,
kernel addr `0x10008000`, ramdisk addr `0x11000000`, tags `0x10000100`). A
byte-exact backup is kept at `/root/pwnage50000/boot14.orig.img`. Flash only the
same partition with the repacked v1 image, then verify `zcat /proc/config.gz`
reports both options.
