# nuxel-s10 — live hardware fixes

Installed files (phone rootfs):

| repo | live |
|---|---|
| `bin/nuxel-audio-route.sh` | `/usr/lib/nuxel/nuxel-audio-route.sh` |
| `bin/nuxel-wifi-up.sh` | `/usr/lib/nuxel/nuxel-wifi-up.sh` |
| `bin/nuxel-charger-mode-recovery.sh` | `/usr/lib/nuxel/nuxel-charger-mode-recovery.sh` |
| `bin/nuxel-device-permissions.sh` | `/usr/lib/nuxel/nuxel-device-permissions.sh` |
| `bin/nuxel-gps-status` | `/usr/local/bin/nuxel-gps-status` |
| `systemd/*.service` | `/etc/systemd/system/` |
| `alsa/99-nuxel-s10-default.conf` | `/etc/alsa/conf.d/99-nuxel-s10-default.conf` |
| `geoclue/geoclue.conf` | `/etc/geoclue/geoclue.conf` (Wi-Fi/IP only) |
| `dbus/99-geoclue-nuxel.conf` | `/etc/dbus-1/system.d/99-geoclue-nuxel.conf` |
| `bin/nuxel-audio-status` | `/usr/local/bin/nuxel-audio-status` |
| `bin/nuxel-apply-pwnage36000.sh` | staged apply (`--files-only` early, `--services` late) |
| `bin/nuxel-verify-pwnage36000.sh` | `/usr/lib/nuxel/stage36000/nuxel-s10/bin/` (read-only verification) |
| `bin/nuxel-device-permissions-early-wrapper.sh` | `/usr/lib/nuxel/nuxel-device-permissions.sh` (early boot wrapper) |
| `wireplumber/99-nuxel-s10.conf` | `/etc/wireplumber/wireplumber.conf.d/99-nuxel-s10.conf` |
| `pipewire/99-nuxel-s10.conf` | `/etc/pipewire/pipewire.conf.d/99-nuxel-s10.conf` |

## Why

* **Audio**: RDMA0 never advances `hw_ptr`; RDMA1 -> SIFS1 -> UAIF1 works at
  44.1 kHz.  The ALSA default points at `hw:0,1`, the static PipeWire sink is
  `alsa_output.hw_0_1`, and the route script stops after the first blocked
  `amixer` open instead of accumulating D-state processes.
* **Wi-Fi**: `nuxel-wifi.service` unblocks the radio, enables every stored
  Wi-Fi profile for autoconnect, and brings up a profile when needed.  This is
  what keeps the WLAN SSH console reachable after a reboot.
* **Charger/LPM**: `sec_ts` refuses to bind on a charger-mode boot.  The
  recovery unit detects the LPM cmdline markers and performs one normal
  `systemctl reboot`, with a 600 s persisted cooldown.
* **udev**: `systemd-udevd` is masked and fails on the 4.14 image, so the udev
  rules were **removed** (`90-nuxel-s10.rules`, `90-nuxel-audio.rules`,
  `90-nuxel-bluetooth.rules`, `99-bluetooth.rules`).  The permissions service
  applies the policy directly at boot.  `udev/90-nuxel-s10.rules` remains in
  the repo only as a reference for a future udev-enabled kernel; the installer
  does not copy it.
* **GPS**: the BCM4773 path is `BLOCKED_FIRMWARE` (BBD/LHD, not NMEA).
  Geoclue is configured for Wi-Fi/IP network location only; it never claims a
  GNSS fix.  `nuxel-gps-status --locate` reports the honest result.

Rollback: reinstall the previous files from
`/var/lib/nuxel/rollback-pwnage36000/`, then `systemctl daemon-reload` and
disable the new units.
