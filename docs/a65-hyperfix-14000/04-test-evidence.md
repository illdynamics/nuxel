# A65 — Test evidence

All device commands run over /dev/ttyACM0 USB Live Console with `stty -echo`
(kernel kmsg noise is multiplexed onto the same line; results are marker-grepped).

## A65-01 TLS
- `python3 -c "from gi.repository import Gio; b=Gio.TlsBackend.get_default(); print(type(b).__name__, b.supports_tls())"`
  -> `GTlsBackendGnutls True`.
- Soup3 (WebKitGTK 4.1 network stack):
  - https://www.google.nl -> HTTP 200, 90756 bytes (real HTML).
  - https://example.org -> HTTP 200, 577 bytes.
  - https://self-signed.badssl.com -> REJECTED "Unacceptable TLS certificate (2)".
  - https://expired.badssl.com -> REJECTED "Unacceptable TLS certificate (2)".
- WebKitGTK headless (XDG_RUNTIME_DIR=/run/nuxel-wayland, WAYLAND_DISPLAY=wayland-0):
  - LOAD https://www.google.nl -> COMMITTED https://www.google.com/ -> FINISHED title='Google'.
  - LOAD https://example.org -> FINISHED title='Example Domain'.
  - LOAD https://self-signed.badssl.com -> FAILED g-tls-error-quark (correct).

## A65-02 Wi-Fi truth
- `nmcli`-equivalent via D-Bus: wlan0 state=100, connectivity=4, IP 10.20.30.16/24.
- HTTP bridge `phone/status` -> `network.wifi_state=internet`, `wifi_stage=online`,
  `wifi_connected=true`, devices [wlan0:100, wlan1:30].
- Deployed `wifi-settings.js` SHA == repo (c636ce91…).

## A65-09 battery truth
- `phone/status` -> `battery.level=100`, `charging=false`, `available=true`,
  `status=full`, `source=sysfs:battery`, `capacity_uah=4000000`.
- Deployed `lockscreen.js` SHA == repo (23fc189a…).

## A65-11 Calculator
- Source: `livePreview()` no longer calls `compute`; result updates only in `commit()`.
- `node --check` passes.

## A65-08/15 Browser & A65-12/13 Camera
- `python3 -m py_compile` passes for browser and native camera (laptop and device).
- Deployed hashes match repo for all five edited app files.

## A65-10 orientation
- `orientation get` -> allowed [0,90,180,270], mode auto; sensor available=false
  (BCM4773 exposes no accel IIO channels). `orientation set portrait` -> success.
- Manual forced transforms work; sensor auto = BLOCKED_HARDWARE.

## Sanitized kill receipt (browser restart)
- PID 6641 cmdline `python3 /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py`
  cgroup `0::/system.slice/nuxel-app-browsernative-1792754774800.service`.
- PID 6647 same app cgroup `nuxel-app-browsernative-1792754775033.service`.
- SIGTERM sent to those two app service cgroups only; launcher/compositor/nav untouched.
