# LIVE DEPLOYMENTS — A34

All deployments used `scripts/s10plus-debug-pack/nuxel-live-deploy.sh` over the
CDC-ACM console, with SHA-256 verification and atomic install.

| Time (local) | Path | SHA-256 | Action |
|---|---|---|---|
| 12:15 | `/usr/lib/nuxel/nuxel-button-manager` | `6bdc6642…34bc5e6d` | A34 SYN_REPORT touch fix; service active |
| 12:17 | `/usr/local/bin/nuxel-wl-snapshot` | `71c54100…78f1c81` | new diagnostic |
| 12:20 | `/usr/share/nuxel/pwa/nuxel-home/js/status-bar.js` | `0e3252a4…ec8337d` | QS pull-down gesture |
| 12:20 | `/usr/share/nuxel/pwa/nuxel-home/manifest.json` | `05f0708a…cfdfe4d` | version triple |
| 12:20 | `/usr/share/nuxel/pwa/nuxel-home/sw.js` | `bccbea28…93ea484f` | cache v6-a34 |
| 12:21 | — | — | `systemctl restart nuxel-wayland`; Mail iframe closed, Home reloaded, `STATUSBAR_READY version=0.4.2-a34` |
| 12:26 | `/usr/lib/nuxel/nuxel-wl-fb` | `ebe7e245…0006b6d1` | bl_power=4 display-off; service active |
| 12:26 | `/usr/local/bin/nuxel-usb-input-audit.sh` | `8c0bc1fd…a55550f9` | diagnostic |
| 12:26 | `/usr/local/bin/nuxel-display-frame-trace.sh` | `8865be29…f654699a` | diagnostic |
| 12:26 | `/usr/local/bin/nuxel-button-trace.sh` | `7d8201b8…25086900` | diagnostic |
| 12:29 | `/usr/lib/nuxel/nuxel-button-manager` | `dd027b96…9f7465fc` | Bixby deferral cancelled by Power; service active |
| 12:32 | `/usr/share/nuxel/pwa/nuxel-home/js/app.js` | `dc7d8fcc…281e690` | home closes app iframe; window `nuxel:action` listener |
| 12:32 | `status-bar.js` / `manifest.json` / `sw.js` | `d90b55be…e4ff4a` / `1ce22c52…a77c4` / `6058e74f…ba3f26` | version 0.4.3-a34, cache v7-a34 |
| 12:32 | — | — | `systemctl restart nuxel-wayland`; `STATUSBAR_READY version=0.4.3-a34` |
| 12:34 | `/usr/lib/nuxel/nuxel-button-manager` | `21a69518…7728fb0` | edge-back translated to host `home`; service active |
| 12:36 | `/usr/lib/nuxel/nuxel-button-manager` | `8ce4b41f…06008dbc` | Cancel added first; superseded by the 12:38 build |
| 12:36 | `/etc/nuxel/input/button-fsm.json` | `46a90ab9…171348aa` | menu spec matches 11-entry C table |
| 12:38 | `/usr/lib/nuxel/nuxel-button-manager` | `f5f9c6f8…2bdfe0ab9` | `menu-close` handled explicitly; service active |
| 13:44 | `/usr/local/bin/nuxel-wl-snapshot` | `71c54100…78f1c81` | re-installed after the raw audit found it absent; snapshot verified (`SNAPSHOT_OK ... 720x1520`) |
| 13:45 | `/etc/systemd/system/nuxel-{web,bridge,notifications,button-manager}.service` | verified per file | `StartLimit*` moved to `[Unit]`; `systemctl daemon-reload`; bounds now reported (1–2 min / 5–15) |
| 13:46 | `/usr/lib/nuxel/nuxel-bridge/{api.py,bridge.py}` | `3632ae12…` / `d6979acb…` | RPC map: `phone.status`, `notifications.list`, `permissions.list`, `sms.list`, `call.end`; notification send uses the system-bus hub; services restarted |

Rollback copies remain on the device (`.prev`, `.prev-a32` where applicable).
The live console stayed usable throughout. No reboot occurred during A34.
