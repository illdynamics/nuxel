# NUXEL A73 / 22000 — Preflight & Rollback

**Date:** 2026-10-25 (session ~18:00–19:30 CEST)
**Host:** macOS `infranux` (Darwin 24.6.0 arm64)
**Transport:** USB CDC-ACM Live Console `/dev/cu.usbmodem101` (18d1:4ee7, NUXEL-S10PLUS-0001)
**Target:** Samsung Galaxy S10+ SM-G975F (beyond2lte), Linux `4.14.253 #15 aarch64`, Fedora 43
**Repo HEAD (start):** `1aec234` on branch `nuxel/a72-21000-internet-unleashed`
**Work branch:** `nuxel/a73-22000-ghostbusters-radio`

## Scope boundary (never touched)
- Kernel/bootloader/DTB/vendor firmware: **NOT touched, NOT flashed.**
- `/opt/nuxel/nuxel-console` (sole recovery console, `init.scope` PIDs 3525/3526): **never
  stopped or restarted** — left running throughout.
- Raw partitions, PIT, modem/EFS/calibration, recovery: untouched.
- `snekbyte.zip` and prior fix branches: untouched.

## What was changed and deployed
| repo source | deployed path | service reload |
|---|---|---|
| `services/nuxel-bridge/src/system_indicators.py` | `/usr/lib/nuxel/nuxel-bridge/system_indicators.py` | `nuxel-http-bridge.service` restart |
| `services/nuxel-bridge/src/bridge.py` | `/usr/lib/nuxel/nuxel-bridge/bridge.py` | `nuxel-bridge.service` restart |
| `services/nuxel-bridge/src/api.py` | `/usr/lib/nuxel/nuxel-bridge/api.py` | `nuxel-http-bridge.service` restart |
| `services/nuxel-bridge/src/capabilities.py` | `/usr/lib/nuxel/nuxel-bridge/capabilities.py` | (imported next bridge start) |
| `pwa/nuxel-home/js/qs.js` | `/usr/share/nuxel/pwa/nuxel-home/js/qs.js` | launcher reload + SW cache v43 |
| `pwa/nuxel-home/sw.js` | `/usr/share/nuxel/pwa/nuxel-home/sw.js` | launcher reload (v43-a73-radio-usb) |
| `pwa/nuxel-home/manifest.json` | `/usr/share/nuxel/pwa/nuxel-home/manifest.json` | launcher reload |
| `pwa/nuxel-home/index.html` | `/usr/share/nuxel/pwa/nuxel-home/index.html` | launcher reload (`qs.js?v=a73`) |
| `tools/s10plus/a45/nuxel-pwa-host.c` | **compiled** → `/usr/lib/nuxel/nuxel-pwa-host` | `nuxel-wayland.service` restart |

The native host was rebuilt **on-device** from the a45 source using the exact a32
recipe (gcc + gtk3/webkit2gtk4.1 dev packages installed via `dnf5`, gpgcheck=1):

```sh
CFLAGS="-O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11"
gcc $CFLAGS $(pkg-config --cflags gtk+-3.0 webkit2gtk-4.1) -o nuxel-pwa-host nuxel-pwa-host.c \
    $(pkg-config --libs gtk+-3.0 webkit2gtk-4.1) -lutil
```

## On-device backup
`/var/lib/nuxel/a73-backup/`
- `bridge/system_indicators.py` (+ `.a73-pre`), `api.py`, `bridge.py`, `capabilities.py`
- `pwa-home/js/qs.js`, `pwa-home/js/lockscreen-indicators.js`
- `nuxel-pwa-host` (pre-rebuild binary)

## Rollback (tested)
Run on the phone (or via the live console) — restores every changed file:

```sh
# from docs/a73/ROLLBACK.sh
sh /path/to/ROLLBACK.sh   # copies /var/lib/nuxel/a73-backup back over the targets
```

Then restore the service set and launcher:

```sh
systemctl restart nuxel-bridge.service nuxel-http-bridge.service
systemctl restart nuxel-wayland.service
```

Toolchain rollback (if the dev packages should be removed — optional, non-destructive):

```sh
dnf5 history undo <transaction-id-for-gcc-webkit-devel>
```

## Safe detach plan (owner action)
The USB Live Console is the **only** host access channel, so a physical unplug
interrupts it. Before the owner performs the disconnect test, an on-device logger
was left running detached so observations survive the link drop:

```sh
# already running (PID in ps), logs to /var/lib/nuxel/a73-usb-unplug.log
/usr/lib/nuxel/a73-logger.sh
```

Owner unplug steps are in `TEST-MATRIX.md` and `FINAL-STATUS.md`.
