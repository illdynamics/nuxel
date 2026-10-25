# NUXEL A74 / 23000 — Preflight and recovery

**Date:** 2026-10-25 (CEST)
**Host:** macOS `infranux` (Darwin 24.6.0 arm64)
**Transports:**
- Primary: USB CDC-ACM Live Console `/dev/cu.usbmodem101` (18d1:4ee7, NUXEL-S10PLUS-0001)
- Alternate recovery: **SSH over Wi-Fi `root@192.168.178.167:22`** (established this session; survives USB detach)

**Target:** Samsung Galaxy S10+ SM-G975F, Linux `4.14.253 #15 aarch64`, Fedora 43.
**Boot ID at start:** `c630c24d-5261-486c-8217-82dd8765f4ad` (uptime 1046 s at 19:58).

## Scope boundary (never touched)
- Kernel / bootloader / DTB / modem / firmware / partitions: **NOT touched, NOT flashed.**
- Sole recovery console `/opt/nuxel/nuxel-console` (init.scope PIDs 3527/3528): **never stopped.**
- Charging/PC/Live-Console penguin artwork, size, position, animation: **untouched.**
- Wi-Fi/browser, Bluetooth/Location tiles, lockscreen/navigation, Camera, SnekByte: **untouched.**

## Changed and deployed (repo == deployed, sha256)
| repo source | deployed path | sha256 (repo == deployed) | reload |
|---|---|---|---|
| `services/nuxel-bridge/src/system_indicators.py` | `/usr/lib/nuxel/nuxel-bridge/system_indicators.py` | `d68c3631…b4a5a` | `nuxel-http-bridge.service` restart |
| `tools/s10plus/a45/nuxel-pwa-host.c` | **compiled on-device** → `/usr/lib/nuxel/nuxel-pwa-host` | `07f64581…45f2d7` (binary) | `nuxel-wayland.service` restart |
| `docs/a74/a74-logger.sh` | `/usr/lib/nuxel/a74-logger.sh` | `9c4cdfd9…3367dd2` | detached, running (PID 10287) |

The native host was rebuilt **on-device** from the a45 source with
`gcc -O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11` + gtk3/webkit2gtk4.1.

## On-device backup
`/var/lib/nuxel/a74-backup/`
- `bridge/system_indicators.py.pre-a74`
- `bin/nuxel-pwa-host.pre-a74`
- `bin/a73-logger.sh.pre-a74`

## Recovery path if the USB console drops
1. The phone stays on Wi-Fi `192.168.178.167`. From the host:
   `ssh root@192.168.178.167` (key-only, `~/.ssh/id_ed25519`).
2. Re-plug the USB cable to restore the Live Console; the phone re-enumerates
   the gadget and the console re-serves the framed shell automatically.

## On-device diagnostic artifacts
- `/var/lib/nuxel/a74-usb-unplug.log` — bounded detach/reattach logger (A74, no debugfs read).
- `/var/lib/nuxel/a74-logger.stdout` — logger stdout/stderr.
- `/sys/fs/pstore/dmesg-ramoops-0` — preserved previous-panic record (NOT cleared).
