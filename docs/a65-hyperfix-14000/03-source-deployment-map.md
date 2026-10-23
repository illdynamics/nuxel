# A65 — Source & deployment map

## Repo edits (this mission)
| File | Change | On-device target (SHA-256 match) |
|---|---|---|
| pwa/nuxel-apps/calculator/js/calculator.js | Equals-gated result (A65-11) | /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js (18a84e93…) |
| pwa/nuxel-apps/camera-gallery/js/camera.js | concise status + retry + diagnostics (A65-12) | …/camera-gallery/js/camera.js (7bc3de12…) |
| pwa/nuxel-apps/camera-gallery/index.html | retry + diagnostics UI | …/camera-gallery/index.html (3b3b2616…) |
| pwa/nuxel-apps/camera-gallery/css/camera.css | diagnostics styles | …/camera-gallery/css/camera.css (60895a6c…) |
| shell/nuxel-browser-native/nuxel_browser_native.py | undecorated + responsive toolbar (A65-08/15) | /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py (0ff27a27…) |
| shell/nuxel-camera-native/nuxel_camera_native.py | concise + retry + close + diagnostics + undecorated (A65-12/13/15) | /usr/lib/nuxel/nuxel-camera-native/nuxel_camera_native.py (39104ce7…) |
| images/s10plus/build-phone-rootfs-inside-fedora.sh | add glib-networking libproxy (A65-01 reproducible) | (image build) |
| tools/s10plus/a33/verify-packages.py | essential webkit group + glib-networking | (image build) |

## Live device package install (A65-01)
- Downloaded on-device: `glib-networking-2.80.1-3.fc43.aarch64.rpm` from
  fedora.mirror.liteserver.nl (Everything/43/Everything/aarch64/os).
- Installed: `rpm -i --nodeps --noscripts --dbpath /tmp/rpmdb-a65`.
- Landed: `/usr/lib64/gio/modules/libgiognutls.so` (+ proxy modules disabled:
  `libgiolibproxy.so.a65-disabled`, `libgiognomeproxy.so.a65-disabled` because
  libproxy.so.1 was not on the device).
- `giomodule.cache` moved to `giomodule.cache.a65-disabled` so GIO scans the module dir.
- Backups: `giomodule.cache.nuxel-a65-bak`, deployed files `*.nuxel-a65-bak`.

## Device state after deploy
- `Gio.TlsBackend.get_default()` = `GTlsBackendGnutls`, supports_tls()=True.
- WebKitGTK headless (same Wayland session): google.nl -> title 'Google',
  example.org -> 'Example Domain'; badssl rejected.
- Browser app instances (org.nuxel.BrowserNative) terminated with receipt, respawn fresh
  on next launch.

## Pre-existing uncommitted work (preserved, not re-authored)
- tools/beta/live/deploy-manifest.json, tools/s10plus/a34/nuxel-wl-fb.c,
  tools/s10plus/a45/nuxel-button-manager.c, tools/s10plus/a45/test-lockscreen-unlock.js,
  pwa/nuxel-home/css/lockscreen.css, pwa/nuxel-home/js/lockscreen.js,
  configs/nuxel/display/, docs/beta-finalization/live/evidence/*, and A63/A64 briefs.
