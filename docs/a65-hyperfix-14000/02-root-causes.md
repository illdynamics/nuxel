# A65 — Evidence-based root causes

## A65-01 (TLS) — CONFIRMED, FIXED
`rpm -q glib-networking` = "package glib-networking is not installed" on the phone,
while gnutls-3.8.13, ca-certificates, glib2-2.86.5, libsoup3-3.6.6, webkit2gtk4.1-2.52.5
ARE installed. `python3 -c "from gi.repository import Gio; ..."` returned
`GDummyTlsBackend False`. GIO had no TLS module -> WebKitGTK 4.1/libpsoup3 reported
"TLS support is not available". Not DNS, not a bad clock, not an invalid cert.
Fix: installed glib-networking-2.80.1-3.fc43.aarch64 (libgiognutls.so). After:
`GTlsBackendGnutls True`; Soup3 GET https://www.google.nl = HTTP 200 (90756 bytes),
https://example.org = HTTP 200; https://self-signed.badssl.com and
https://expired.badssl.com both rejected `g-tls-error-quark: Unacceptable TLS certificate`.
Also added `glib-networking`/`libproxy` to `images/s10plus/build-phone-rootfs-inside-fedora.sh`
and `tools/s10plus/a33/verify-packages.py` so future images carry it.

## A65-02 (Wi-Fi state) — source already correct, deployed bytes verified
NetworkManager `wlan0` is `state=100 (connected)`, `Connectivity=4`. `bridge.py`
`NetworkManagerStatus.get_status()` maps 100 -> `wifi_state=internet`,
`wifi_stage=online`. The Settings pane (`pwa/nuxel-apps/settings/wifi-settings.js`)
renders `honestStage(wifi_stage)`; on-device bytes match repo SHA-256
(c636ce91...). The "Authenticating and Associating" copy only appears for real
NM states 40/50/60. Conclusion: truthful; earlier symptom was a stale deployment.

## A65-09 (lockscreen 0%) — source already correct, deployed bytes verified
`read_battery_status()` reads `/sys/class/power_supply/battery` by type=Battery and
returns level=None on missing/malformed (never 0). Lockscreen `_updateBattery()` paints
`—` first then real %. Live value = 100 (Full). On-device `lockscreen.js` matches repo
(23fc189a...). Root cause was an earlier placeholder, already replaced.

## A65-11 (Calculator premature evaluate) — CONFIRMED, FIXED
`livePreview()` called `compute(true)` on every keystroke and wrote `state.lastResult`,
so typing `9 + 8` showed `17` before Equals. Fix: `livePreview()` now only re-renders
the expression; `commit()` (Equals) is the only path that updates the result. The
shunting-yard engine still applies precedence (`2+3×4 = 14`) at Equals.

## A65-08/15 (browser chrome) — FIXED
Native browser kept `Gtk.Window(title="Nuxel Browser")` (redundant titlebar) and a
fixed 5-item chrome row. Fix: `set_decorated(False)`; compact relief-none buttons;
address entry `set_width_chars(8)` + `set_hexpand(True)` as the only expanding widget.

## A65-12/13 (cameras) — FIXED (app usability), capture blocked
Both the Camera PWA and `nuxel_camera_native.py` showed the verbose FIMC-IS detail as
default top status and the native app lacked an explicit Close. Fix: concise top status,
collapsible Technical diagnostics, explicit Retry and Close. Real capture remains
`capture_verified=false` (FIMC-IS has no standard V4L2 capture) -> BLOCKED_HARDWARE.

## A65-10 (rotation auto) — BLOCKED_HARDWARE
`iio:device1` = BCM4773 sensor hub. Its `scan_elements/` only exposes
`in_timestamp_*`; there are no `in_accel_*` channels and no `in_accel_scale`. So the
accelerometer is not readable through IIO on this vendor kernel. Manual forced
0/90/180/270 remain available through the orientation policy.

## A65-03 (configurable lock delay) — PARTIAL
Idle/power screen-off already re-locks immediately (button-manager idle timer ->
`screen-off` -> launcher `_lock`). A Home-Settings enum for "lock after screen off"
delay is not yet wired; documented as the remaining gap.
