# NUXEL A72 / 21000 — 01-REPO-LIVE-DELTA (repo HEAD vs deployed phone)

Repo HEAD `fe3ccd0`. Device hashes read live 2026-10-25 via USB console.

| path | repo sha256 | device sha256 | match |
|---|---|---|---|
| pwa/nuxel-home/js/lockscreen.js | 94849e33…c517 | 94849e33…c517 | ✅ |
| pwa/nuxel-home/js/lockscreen-indicators.js | b41df0dd…d441 | b41df0dd…d441 | ✅ |
| pwa/nuxel-home/js/app.js | ed800ef0…ee4 | ed800ef0…ee4 | ✅ |
| pwa/nuxel-home/js/navigation.js | 87098908…4d7 | 87098908…4d7 | ✅ |
| pwa/nuxel-home/js/launcher.js | 2171f661…91b | 2171f661…91b | ✅ |
| pwa/nuxel-home/js/apps.js | d68efd0f…570 | d68efd0f…570 | ✅ |
| pwa/nuxel-home/css/style.css | acfb751e…cb5 | acfb751e…cb5 | ✅ |
| pwa/nuxel-home/css/lockscreen.css | 992be4dc…931 | 992be4dc…931 | ✅ |
| pwa/nuxel-home/css/status-bar.css | b6e469ee…e9e3 | b6e469ee…e9e3 | ✅ |
| pwa/nuxel-home/index.html | eea1f3d4…d39 | eea1f3d4…d39 | ✅ |
| pwa/nuxel-home/manifest.json | 830c5775…911 | 830c5775…911 | ✅ |
| pwa/nuxel-home/sw.js | a478b340…368 | a478b340…368 | ✅ |
| pwa/nuxel-apps/maps/index.html | 53a54b08…6e8 | 53a54b08…6e8 | ✅ |
| pwa/nuxel-apps/maps/js/maps.js | c78003b4…e07 | c78003b4…e07 | ✅ |
| pwa/nuxel-apps/maps/sw.js | 38bcf9fe…ab0b | 38bcf9fe…ab0b | ✅ |
| pwa/nuxel-home/js/status-bar.js | 584c8baf…31f (repo HEAD) | **77f0474f…d77e** | ❌ device AHEAD |
| pwa/nuxel-home/js/home-settings.js | 7c81bfd6…f6b (repo HEAD) | **6b7605f7…db5** | ❌ device AHEAD |

## The two deltas (device is AHEAD of repo — DO NOT overwrite)
1. `status-bar.js` — device carries an extra "A66-02 empty-read-guard" (rejects an
   empty sysfs battery read BEFORE numeric coercion, so boot shows UNKNOWN not 0%).
   Repo HEAD `fe3ccd0` does NOT contain this block. Preserve the device version.
2. `home-settings.js` — device carries a "Lock & display / lock-after-off" settings
   section (config `display-timeout` with `lock_after_off_ms`) not in repo HEAD.

Both were snapshotted to `/var/lib/nuxel/a72-backup-20261025T152149Z/` before any
changes. These device-side newer files are treated as protected baseline; no
deploy may clobber them unless the same content is first committed to the repo.

## Native binaries (phone, unchanged this mission)
- /usr/lib/nuxel/nuxel-pwa-host  (2026-10-25 14:39)
- /usr/lib/nuxel/nuxel-navdock  (2026-10-23 15:22)
- /usr/lib/nuxel/nuxel-button-manager  (2026-10-21 08:38)
- /usr/lib/nuxel/nuxel-wl-fb  (2026-10-23 16:21)
