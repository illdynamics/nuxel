# PWNAGE-85000 Patch Manifest

All paths are relative to the repository root. Live hashes are in `live-sha256.txt`; local hashes in `local-sha256.txt`.

| Path | Change | Purpose |
|---|---|---|
| `services/nuxel-bridge/src/flatpak_provider.py` | modify | 1 s transient-unit stop bound; installed-ref cache; per-app renderer policy; no blanket renderer env in base user env |
| `services/nuxel-bridge/src/api.py` | modify | 1 s app-unit stop bound; launch phase timing |
| `services/nuxel-bridge/src/hw_providers.py` | modify | authoritative `panel_state()` from `bl_power`/brightness |
| `services/nuxel-bridge/src/system_indicators.py` | modify | 10 s screen-off / 2 s screen-on indicator projection cache |
| `services/nuxel-session/nuxel-fuse-access.service` | **new** | `/dev/fuse` access for the document portal; user-session dirs; enabled |
| `configs/nuxel/tmpfiles-nuxel-portal-doc.conf` | **new** | boot-time `/run/nuxel-wayland/doc` and `at-spi` dirs |
| `pwa/nuxel-common/theme.css` | modify | motion tokens; reduced/off; display-off idle guard; button press |
| `pwa/nuxel-common/theme.js` | modify | persisted `nuxel.motion` preference and `data-motion` |
| `pwa/nuxel-home/css/style.css` | modify | token-driven panel/nav transitions; display-off idle guard |
| `pwa/nuxel-home/css/launcher.css` | modify | token-driven page slide; restrained app press; reduced/off rules |
| `pwa/nuxel-home/js/app.js` | modify | non-blocking display watcher; launch/close timing context |
| `pwa/nuxel-home/js/launcher.js` | modify | suppressResize guard against re-entrant orientation reflow |
| `pwa/nuxel-home/js/lockscreen-indicators.js` | modify | stop 1 Hz indicator poll on `display_off:true`; re-arm on wake |
| `pwa/nuxel-home/index.html` | modify | `p85000` asset cache-bust |
| `pwa/nuxel-home/sw.js` | modify | `CACHE_VERSION=v85000-pwnage` |
| `pwa/nuxel-apps/settings/index.html` | modify | Motion selector |
| `pwa/nuxel-apps/settings/appearance-settings.js` | modify | Motion preference apply/persist |
| `tests/pwnage85000/test_flatpak_launch_perf.py` | **new** | cache/timeout/renderer-policy tests |
| `tests/pwnage85000/test_motion_contract.py` | **new** | motion bounds/reduced-motion/no-blur tests |
| `tests/pwnage85000/test_indicator_cache.py` | **new** | screen-off indicator cache + client stop test |

## Deployed services

- `nuxel-fuse-access.service` — created, enabled, active.
- `nuxel-http-bridge.service` — restarted to load provider/API/indicator changes.
- `nuxel-bridge.service` — restarted.
- `nuxel-wayland.service` — restarted once during instrumentation (see engineering report §10); active and healthy after restart.

## Not changed

No kernel, bootloader, DTB, initramfs, partition, governor, thermal limit, zram/swap, scheduler, `/dev/fb0` owner, Phoc binary, `nuxel-wl-fb` binary, Flatpak installation, Flatpak app data, portal routing, or Whisper/microphone configuration was replaced.
