# NUXEL A53 — Baseline & Hardware Inventory (live S10+)

**Date:** 2026-10-22 · **Branch:** `nuxel/A52-penguin-camera` HEAD `7f6446349149491f50724592e9bebd1e7fd98bb2`
**Host:** macOS (Darwin 24.6.0) driving the phone over the authorized USB CDC-ACM Live Console.
**Console:** `/dev/cu.usbmodem201` · VID `0x18d1` PID `0x4ee7` serial `NUXEL-S10PLUS-0001` (framed, SHA-256-verified; `REACHABLE`).

## Device identity (observed, read-only)

| Field | Value |
|---|---|
| Kernel | `Linux fedora 4.14.253 #15 SMP PREEMPT aarch64` |
| Release | `Fedora release 43 (Forty Three)` |
| Arch | `aarch64` |
| Model | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` (beyond2lte, SM-G975F) |
| Console uid | `root` (the Live Console is an unauthenticated physical-USB root shell by design) |
| Root fs | `/dev/sda31` 3.9G total, 2.1G used, **1.7G avail (55% used)**, 262144 inodes (24% used) |

## Package-manager / toolchain reality (the single most important A53 finding)

| Tool | Status |
|---|---|
| `dnf`, `dnf5`, `microdnf`, `PackageKit`/`pkcon`, `packagekitd` | **ALL MISSING** |
| `rpm` | present (`RPM version 6.0.2`) |
| `flatpak` | **MISSING** (binary absent) |
| `gnome-software` | **MISSING** |
| `snapshot` (GNOME Camera) | **MISSING** |
| `pipewire`, `wireplumber`, `pw-cli` | **MISSING** |
| `xdg-desktop-portal`, `xdg-desktop-portal-gtk` | **MISSING** |
| `bwrap` | present (`bubblewrap-0.12.0-1.fc43.aarch64`) — but useless without `CONFIG_USER_NS` |
| `gstreamer1` | present (`1.26.11-1.fc43.aarch64`), `gst-inspect-1.0` present |
| `gtk3`/`gtk4`/`gtk4-launch`/`adwaita-1-demo` | present (GTK4 4.20.4) |
| `monitor-sensor` | present (`iio-sensor-proxy-3.8-1.fc43.aarch64`) — but `iio-sensor-proxy` D-Bus service is NOT provided |
| `polkit` | present (`polkit-126-6.fc43.2.aarch64`) |
| `wlr-randr` | **MISSING** (no compositor output-management transform tool) |
| `v4l2-ctl`, `media-ctl` | **MISSING** |

**Consequence:** `dnf install …` and PackageKit-based GNOME Software installs are impossible on
this image until a package manager is bootstrapped; the only transport is the 115200-baud serial
console (no `usb0` ethernet gadget). See `GNOME-SOFTWARE-RPM-FLATPAK.md`.

## Network (observed)

- Interfaces: only `lo` is UP. `wlan0`/`wlan1` = `DORMANT` (no carrier). No `usb0`. No default route.
- Wi-Fi radio works and scans APs (`nmcli device wifi list` returns real SSIDs), but no PSK is
  stored/entered → **no internet on-device**. Owner PSK entry is an owner-only step (never guessed).
- USB gadget `nuxel` exposes **only** `acm.usb0` (serial console); no ECM/RNDIS ethernet function.
- Two saved Wi-Fi profiles exist (`Nuxel Studio E Guest`, `Nuxel Undetektable`) but are disconnected.

## Graphical session (observed)

| Component | Value |
|---|---|
| Compositor | `phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini -E /usr/lib/nuxel/nuxel-session.sh` (root) |
| Output | `HEADLESS-1` mode `720x1520` scale `2` (1440x3040 physical panel via `nuxel-wl-fb`) |
| Presenter | `nuxel-wl-fb` (wlr-screencopy → `/dev/fb0`; single framebuffer owner) |
| Launcher | `nuxel-pwa-host` (WebKitGTK) → `http://127.0.0.1:8000/pwa/nuxel-home/index.html` |
| Dock | `nuxel-navdock` |
| OSK | `phosh-osk-stevia` (inside its own `dbus-run-session`) |
| Bridge | `nuxel-bridge.py` (user `nuxel-bridge`) + `api.py` (HTTP RPC on 127.0.0.1:8080) |
| Session env | `GDK_BACKEND=wayland`, `WAYLAND_DISPLAY=wayland-0`, `XDG_RUNTIME_DIR=/run/nuxel-wayland`, `LIBGL_ALWAYS_SOFTWARE=1`, `GSK_RENDERER=cairo` |
| Shared session D-Bus | **absent** for the whole session (only Stevia runs under its own `dbus-run-session`) |

## App registry (deployed `/etc/nuxel/app-registry/app_registry.json`)

11 apps. Native entries `nuxel-dialer`, `nuxel-messages`, `nuxel-contacts` reference
`/usr/bin/nuxel-*` binaries that **do not exist** (placeholders with PWA fallbacks). `nuxel-camera`
is `type:native` but `native_binary:null` with `fallback_surface` → Camera Gallery PWA. The only
genuine native GUI app actually installed is the GTK4 demo `adwaita-1-demo`.

## Sensors / camera / flatpak kernels (summary — full evidence in sibling docs)

- Camera: all FIMC-IS nodes enumerate; capture is blocked (`VIDIOC_S_FMT → ENOTTY`). See
  `CAMERA-PIPELINE-BLOCKERS.md`.
- Accelerometer: `accelerometer_sensor`/`gyro_sensor` IIO devices exist but expose **no**
  `in_accel_*_raw` channels and no scale → auto-rotation sensor is blocked. See
  `ORIENTATION-FIVE-MODE-IMPLEMENTATION.md`.
- Flatpak sandbox: `# CONFIG_USER_NS is not set` → `bwrap`/`unshare -U` fail. See
  `FLATPAK-SANDBOX-PORTALS.md`.

## Failures on boot (systemd)

`systemctl --failed` (system and user) both empty at capture time.
