# NUXEL A69 (18000) — DEVICE PREFLIGHT & LIVE STATE AUDIT

Captured 2026-10-24 ~19:40 CEST. Agent environment: macOS host (`infranux`,
Darwin arm64) reaching the phone over the **USB CDC-ACM Live Console**
(`/dev/cu.usbmodem2201`, VID 0x18d1 PID 0x4ee7, serial NUXEL-S10PLUS-0001).

## Live device identity
- Kernel: `Linux fedora 4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64`
- Userspace: `Fedora release 43 (Forty Three)`
- Uptime at capture: ~6h21m; load average 12.62 / 12.17 / 12.04
- adb: empty (`adb devices` shows nothing) — expected; the live console, not adb, is the channel.

## Top processes (ps, %CPU)
- phoc (Wayland compositor) 3.5%, nuxel-wl-fb 1.1%, nuxel-pwa-host 0.9%,
  WebKitWebProcess 2.3%, nuxel-button-manager 0.2%, nuxel-navdock 0.2%,
  NetworkManager, wpa_supplicant, nuxel-metricsd, phosh-osk-stevia.

## Connectivity (BASELINE GAP)
- `nmcli`: wlan0 `disconnected`, wlan1 `disconnected`; **no default route, no DNS**.
- `curl https://www.google.nl` → `Could not resolve host` (no network).
- Saved Wi-Fi profiles (names only, credentials never logged): 4 802-11-wireless profiles.
- This blocks all `dnf` installs and online tile/geolocation tests. **Wi-Fi/DNS/TLS
  baseline (T30) is NOT currently verifiable from this session** and needs owner
  reconnection; no credentials were read or touched.

## Package manager
- `dnf` is **absent** on the phone (`sh: dnf: command not found`). `rpm` present,
  463 packages. Repos in `/etc/yum.repos.d` exist but are unusable without dnf+network.

## Power / battery
- `/sys/class/power_supply/battery` = type `Battery`, present=1, status `Charging`,
  capacity `94..97`, voltage_now ~4.33 V, charge_full/design 4,000,000 uAh, health Good.
- Kernel battery node is healthy and immediate. HTTP bridge `/api/v1/phone/status`
  returns `battery.level` live (94/97). No kernel-side 0% cause.

## Audio (exact chain)
- ALSA cards: `beyond-madera` (index 0), `abox_vdma` (1), `abox_dump` (2).
  Codec `Cirrus Logic CS47L93 (Madera ASoC)`, amps `CS35L40 x2`, SoC ABox.
- `nuxelctl audio status` verdict: **BLOCKED_FIRMWARE** — codec/amp DSP firmware
  absent: cs47l93-dsp{,1,2}.wmfw / .bin and cs35l40-dsp1/2.{wmfw,bin}.
- UCM profile `/usr/share/alsa/ucm2/beyond-madera/HiFi.conf` absent.
- No PipeWire, no WirePlumber, no PulseAudio server, no alsa-utils (aplay/amixer).
- Headset detection present (`madera-extcon` → input event8 `Headset`, keys 114/115/226).

## Rotation / sensors
- BCM4775x sensor hub (`ssp,BCM4773` DT compatible; mcu_name `BCM47752KUB1G`),
  physical accel/gyro `LSM6DSO` (STM) behind the SSP.
- `/sys/class/sensors/accelerometer_sensor/raw_data` reads `0,0,0`; dmesg shows
  `[SSPBBD]: ssp_down == true` and `ssp_send_cmd failed -1` → sensor hub **down**.
- No BCM4775x sensor-hub firmware in `/lib/firmware`; no Samsung `libsensorhub`
  userspace. IIO stubs expose only `in_timestamp_*` scan elements, no raw axes.
- `nuxel-orientationd` reports `auto_capable: false` (manual only).

## GNSS / NFC / BT
- GNSS: no `/dev/gnss*`/`/dev/gps*`; `[SSP] GPS: false` — GNSS rides the same
  down SSP. `geoclue2` installed but only network-IP capable and network is off.
- NFC: DT node `sec-nfc@27` (hsi2c@108E0000); `sec-nfc` I2C driver registered but
  **no bound device**, no `/sys/class/nfc`, no firmware.
- Bluetooth: `rfkill` shows `bcm43xx Bluetooth` **soft=1** (soft-blocked), hard=0.
  No `/dev/hci*`, no BlueZ/btmgmt/bluetoothctl installed.

## Deployed vs repo (live-vs-repo)
- Deployed PWA js/css are hashed in LIVE-VS-REPO.md. `navigation.js` matches repo;
  `lockscreen.js`, `app.js`, `style.css` differ from the local WIP tree (local WIP
  not yet deployed). Native binaries: `/usr/lib/nuxel/{nuxel-pwa-host,nuxel-navdock,
  nuxel-button-manager}` present.
