# NUXEL A73 — Repo vs Deployed (post-deploy verification)

All changed files were pushed over the USB Live Console with gzip+base64
chunking and verified by target-side sha256. `local sha256 == deployed sha256`
for every text file below.

## Text files (exact match)
| repo path | deployed path | sha256 | status |
|---|---|---|---|
| `services/nuxel-bridge/src/system_indicators.py` | `/usr/lib/nuxel/nuxel-bridge/system_indicators.py` | `93b2d3d0…` | MATCH |
| `services/nuxel-bridge/src/api.py` | `/usr/lib/nuxel/nuxel-bridge/api.py` | `ab8b4320…` | MATCH |
| `services/nuxel-bridge/src/bridge.py` | `/usr/lib/nuxel/nuxel-bridge/bridge.py` | `b3397a2a…` | MATCH |
| `services/nuxel-bridge/src/capabilities.py` | `/usr/lib/nuxel/nuxel-bridge/capabilities.py` | `4ce6e63d…` | MATCH |
| `pwa/nuxel-home/js/qs.js` | `/usr/share/nuxel/pwa/nuxel-home/js/qs.js` | `064bd03a…` | MATCH |
| `pwa/nuxel-home/sw.js` | `/usr/share/nuxel/pwa/nuxel-home/sw.js` | `8b7affc3…` | MATCH (v43-a73-radio-usb) |
| `pwa/nuxel-home/manifest.json` | `/usr/share/nuxel/pwa/nuxel-home/manifest.json` | `4200e518…` | MATCH |
| `pwa/nuxel-home/index.html` | `/usr/share/nuxel/pwa/nuxel-home/index.html` | `3f1fe724…` | MATCH (`qs.js?v=a73`) |

## Native binary (compiled from source)
| repo source | deployed binary | sha256 | service |
|---|---|---|---|
| `tools/s10plus/a45/nuxel-pwa-host.c` (HEAD) | `/usr/lib/nuxel/nuxel-pwa-host` | `cff15529…` | `nuxel-wayland.service` |

The deployed binary was **rebuilt on-device** from the a45 source with the a32
recipe (gcc 15.3.1, gtk3 3.24.52, webkit2gtk-4.1 2.54.1). It is aarch64,
dynamically linked against `libwebkit2gtk-4.1.so.0` / `libgtk-3.so.0`, and
contains the new physical-detach markers (`NUXEL_SYS_TYPEC`, `NUXEL_DEBUGFS`,
`configured-vetoed-by-physical-detach`, `service_armed`, `transport_connected`).

## Runtime processes (post-deploy)
| process | PID | note |
|---|---|---|
| `/opt/nuxel/nuxel-console /newroot` | 3525, 3526 | **untouched** (init.scope) |
| `/usr/sbin/phoc …` | 13526 | restarted (new native host child) |
| `/usr/lib/nuxel/nuxel-pwa-host` | 13532 | **new binary** |
| `python3 …/nuxel-bridge/bridge.py` | (nuxel-bridge) | restarted |
| `python3 …/nuxel-bridge/api.py` | (root) | restarted |
| `/bin/sh /usr/lib/nuxel/a73-logger.sh` | 14314 | evidence logger (detached) |
| `/usr/libexec/bluetooth/bluetoothd` | 8359 | running, no hci0 |

## Drift resolution
Pre-mission drift (deployed behind HEAD) was resolved: the deployed
`system_indicators.py` (14:37) and `nuxel-pwa-host` (14:39) were older than the
committed `1aec234` fixes and have now been brought up to the a73 branch work.
