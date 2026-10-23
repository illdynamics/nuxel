# A65 Hyperfix 14000 — Baseline

Date: 2026-10-23 (Europe/Amsterdam)
Executor: deepseek-v4-pro-thinking via CodeSeeQ, Fedora laptop, USB Live Console.
Git HEAD at start: d8d392c (A64 penguin launcher resurrection, VERSION v0.6.4-beta).

## Physical device (verified live over USB ACM console)
- Product: `Nuxel S10+ Live Console`, USB idVendor=18d1 idProduct=4ee7, /dev/ttyACM0.
- Kernel: `Linux 4.14.253 #15 SMP PREEMPT aarch64` (legacy Samsung-derived vendor kernel).
- OS: `Fedora Linux 43 (Forty Three)`.
- Session: root console shell (`sh-5.3`); `loginctl list-sessions` = none (minimal init,
  UI started by `nuxel-postboot.sh` + `phoc -E nuxel-session.sh`, not a logind session).

## Live process topology (ps, read-only)
- PID 1 systemd; NetworkManager 6261; wpa_supplicant 6305.
- `phoc` 5351 (--no-xwayland -C /etc/nuxel/phoc-phone.ini -E nuxel-session.sh).
- `nuxel-wl-fb` 5398 (framebuffer bridge), `nuxel-button-manager` 5399,
  `nuxel-navdock` 5408 (native layer-shell triple nav), `nuxel-pwa-host` 5389
  (WebKitGTK launcher/app host; WebKitNetworkProcess 5446, WebKitWebProcess 5449).
- Bridge services: `nuxel-bridge/bridge.py` 6308, `nuxel-bridge/api.py` 6309
  (HTTP bridge on 127.0.0.1:8080), `nuxel-portal/portal.py` 6307.
- Native browser: `nuxel_browser_native.py` (WebKitGTK 4.1 top-level app).

## Output geometry
- `phoc-phone.ini`: `[output:HEADLESS-1] mode=720x1520 scale=2` -> 360x760 logical,
  360 CSS px viewport. Software rendering forced (no DRM/EGL).

## Evidence screenshots referenced by prompt
- `evidence/camera-status-a65.jpeg` and `evidence/camera-spinner-a65.jpeg` were NOT
  present in the repo checkout (`ls evidence/` = No such file or directory); they
  are documented as owner-provided references only. Their described states were
  reproduced from live bridge/process data instead.

## Key live ground truth (before changes)
- TLS: `glib-networking is not installed`; `Gio.TlsBackend.get_default()` =
  `GDummyTlsBackend`, `supports_tls()=False`. This is the direct root cause of
  "TLS support is not available".
- Wi-Fi: NetworkManager `wlan0` state `100 (connected)`, connection
  `Nuxel Snoerbreuk`, IP `10.20.30.16/24`, gateway `10.20.30.1`, Connectivity `4`.
  Bridge reports `wifi_state=internet`, `wifi_stage=online`.
- Battery: `/sys/class/power_supply/battery/capacity = 100`, status `Full`,
  `charge_full=4000000`; bridge reports `level=100`, `charging=false`,
  `available=true`, `source=sysfs:battery`.
- Orientation: bridge `orientation get` -> 7-mode policy present; manual forced
  modes allowed [0,90,180,270]; sensor `available=false`
  (`iio-accel`: "IIO device present but no readable scale";
  `iio-sensor-proxy`: service unknown). IIO `iio:device1` (BCM4773 sensor hub)
  exposes only `in_timestamp_*` scan elements — no accel channels.
- Camera: bridge `camera status` -> `camera_present=true`, `capture_verified=false`,
  `video_node_count=68`, detail: FIMC-IS vendor interface has no standard capture.

## Non-negotiables honored
- No kernel/DTB/partition flashing, no cert-bypass, no fake camera capture, no
  killing of PID 1/compositor/launcher/nav/bridge/console. All kills scoped to the
  native browser app cgroup with a sanitized receipt.
