# A59 — On-device acceptance

All observations below are on the real S10+ display (foreign-toplevel window
state + `nuxel-wl-snapshot` framebuffer receipts + process/state files).

## Performed and verified
1. Network/TLS: wlan0 ACTIVE; `https://www.google.nl` + `https://www.eff.org`
   HTTP/2 200 with verified certificates.
2. Nuxel Browser from the drawer → real top-level WebKitGTK window; state file
   `{"status":"finished","uri":"https://www.google.nl/"}`; dedicated WebKit
   network/web processes; screenshot differs from Home.
3. Penguin Home from the open browser → window minimised (`min=1`) while the
   browser process stayed alive; Home window raised/active (`act=1`).
4. Native custom Nuxel Camera launches (`Nuxel Camera` window), shows honest
   "Camera present / Live capture NOT verified" (FIMC-IS reason), never a mock.
5. Native GNOME Snapshot installed and launches (`Camera` window, app_id
   `snapshot`); camera feed blocked by missing PipeWire/libcamera + Exynos ISP.
6. App drawer: `org.nuxel.Calculator` (PWA) and `org.nuxel.Browser` (native)
   both launch from the registry (launcher diagnostics reach LAUNCHING/ACTIVE,
   no "App not found" after cache invalidation).

## Not performed (honest)
- Firefox visible-window mapping (BLOCKED_WAYLAND under phoc --no-xwayland),
  although its content process loaded the page (NETWORK_VERIFIED).
- Chromium install (dnf absent; time-boxed, not forced with --no-sandbox).
- Ladybird build (upstream pre-alpha, no Fedora aarch64 binary).
- Real Exynos camera frames (no PipeWire/libcamera/media-controller path).

## Reboot persistence
- NOT rebooted without owner approval. Service restart of `nuxel-http-bridge`
  and `nuxel-wayland` was verified to return to active with the new code
  (cache purge + registry version 5 confirmed after restart). A full cold-boot
  repeat remains an owner-approved step (M6) documented in ROLLBACK.md.
