# NUXEL A72 / 21000 — 00-BASELINE (fresh live audit)

Captured 2026-10-25 ~16:00 CEST by this agent, one writer, macOS host `infranux`
(Darwin 24.6.0 arm64). Transport: USB CDC-ACM Live Console `/dev/cu.usbmodem101`
(VID 0x18d1 PID 0x4ee7, serial NUXEL-S10PLUS-0001). No adb (expected).

## Device identity
- Kernel: `Linux 2001-1c00-4d09-8a00-162b-e49d-dc7c-4128 4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64`
- Userspace: `Fedora Linux 43 (Forty Three)`, arch `aarch64`
- Uptime at capture: ~8303 s; load average 14.13 / 13.12 / 12.70 (software-rendered WebKitGTK/Phoc)
- Memory: 7420 MB total, ~854 MB used, ~5926 MB free, 0 swap
- Thermal: zone0 62°C (BIG), zone1/2 53°C, zone3 48°C, zone4 49°C, zone5 36°C, zone6 28°C

## Repo state
- Repo HEAD: `fe3ccd0` (merge PR #9, a69-fixes). Working tree has uncommitted A70/A71 WIP (preserved, not reset).
- Local host: macOS 15.7.9 arm64; `zstd`, `podman` (aarch64 fedora:43 image present), python3.11+zstandard available for offline metadata resolution.

## Connectivity (owner-confirmed baseline — CONFIRMED live)
- `nmcli`: wlan0 state 100 (connected), connection `Nuxel Ziggo5501109`, IP 192.168.178.167/24
- default route: `1.1.1.1 via 192.168.178.1 dev wlan0`
- DNS: resolv.conf via NetworkManager (Ziggo resolvers)
- TLS: `curl -I https://www.fedoraproject.org/` -> `HTTP/2 302` + HSTS (valid chain)
- curl 8.15.0 aarch64 (OpenSSL 3.5.8, nghttp2)

## Package manager
- `rpm` 6.0.2 (rpm-6.0.2-1.fc43), 463 packages installed.
- `dnf` / `dnf5` / `microdnf`: ABSENT. libsolv/librepo/libmodulemd/libdnf5: ABSENT.
- `/etc/yum.repos.d/` present (fedora, updates, updates-testing, cisco-openh264) with `gpgcheck=1`.
- GPG keys: `RPM-GPG-KEY-fedora-43-primary` present under `/etc/pki/rpm-gpg/`.
- Rootfs `/` = /dev/sda31 ext4 rw, 3.9G total, 1.2G avail (68% used).

## Hardware truth (fresh)
- ALSA: `beyond-madera` (0), `abox_vdma` (1), `abox_dump` (2). PCM RDMA0-11 playback / WDMA0-7 capture / DP Audio.
- Audio verdict (`nuxelctl audio status`): `BLOCKED_FIRMWARE` — missing `cs47l93-dsp{,-1,-2}.wmfw/.bin` + `cs35l40-dsp1/2.wmfw/.bin`; UCM `HiFi.conf` absent; no PipeWire/WirePlumber/alsa-utils.
- rfkill: `bcm43xx Bluetooth` soft=1 hard=0; `phy0` + `brcmfmac-wifi` wlan unblocked.
- Sensors: Samsung sensors_class present (accel/gyro/baro/light/prox/HRM…); SSP down (`ssp_down==true`, `ssp_send_cmd - command 0xd1 failed -1`), accel raw `0,0,0`, IIO no readable scale.
- GNSS: no `/dev/gnss*`/`/dev/gps*`; `[SSP] GPS: false`.
- NFC: DT `sec-nfc@27` under `hsi2c@108E0000` (compatible `hrm_max sec-nfc`); `/sys/class/nfc/nfc_support` empty; no bound NCI device.
- Battery: type Battery, present, capacity 100, status Full; supplies also `ac`, `max77705-charger`, `max77705-fuelgauge`, `mfc-charger`, `otg`, `ps`, `usb`, `wireless`.
- `/lib/firmware/`: only `bcmdhd_*` (Wi-Fi), `nvram.txt_CS01_semco_b1`, `regulatory.db*`. No audio DSP / BT HCD / SSP firmware.

## Running services (active)
nuxel-bridge, nuxel-button-manager, nuxel-haptics, nuxel-http-bridge, nuxel-notifications,
nuxel-orientationd (exited), nuxel-portal, nuxel-touch-arm, nuxel-wayland, nuxel-wl-fb, seatd.

## Installed audio/geo/media packages (subset)
alsa-lib, geoclue2(+libs), gstreamer1(+base/bad-free/gtk4 plugins), iio-sensor-proxy,
mpg123-libs, pulseaudio-libs(+glib2). NOT installed: pipewire, wireplumber, bluez,
alsa-utils, vlc, mpv, any music player.

## Repo↔live headline delta
Deployed phone is AHEAD of repo HEAD `fe3ccd0` in two files (do NOT overwrite):
- `pwa/nuxel-home/js/status-bar.js` — phone has an "A66-02 empty-read-guard" not present in repo HEAD.
- `pwa/nuxel-home/js/home-settings.js` — phone has a "Lock & display / lock-after-off" section not in repo HEAD.
All other key PWA JS/CSS/HTML hashes match repo HEAD exactly (see 01-REPO-LIVE-DELTA.md).
