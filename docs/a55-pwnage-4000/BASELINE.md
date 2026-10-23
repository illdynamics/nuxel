# A55 Pwnage 4000 — Baseline

**Date:** 2026-10-22 (Europe/Amsterdam)
**Branch:** `nuxel/A55-pwnage-4000`
**Host:** Darwin 24.6.0 (MacBook), console `/dev/cu.usbmodem201` (VID 0x18D1 / PID 0x4EE7, serial NUXEL-S10PLUS-0001)

## Device (verified live, not from docs)
| Property | Value |
|---|---|
| Model | Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820 |
| Kernel | 4.14.253 (Samsung vendor lineage), `aarch64` |
| OS | Fedora Linux 43 |
| Compositor | `phoc` (headless) + `nuxel-wl-fb` → `/dev/fb0` AMOLED (720×1520) |
| Launcher | WebKitGTK `nuxel-pwa-host` (GTK3 + WebKit2GTK-4.1), serves `/usr/share/nuxel` on 127.0.0.1:8000 |
| Bridge | `nuxel-bridge` + `nuxel-http-bridge` (127.0.0.1:8080) |
| RAM / disk | 7.4 GiB RAM (6.0 free) · 1.7 GiB free on `/` (3.9G) |

## Key package facts (blockers recorded)
- Present: `webkit2gtk4.1` + `webkitgtk6.0` 2.52.5, `gtk3` + `gtk4`, `javascriptcoregtk`, `gstreamer1` (base/bad-free), `python3` + PyGObject (Gtk3/Gtk4/WebKit2-4.1/WebKit-6.0 typelibs), `bwrap`, `xdg-dbus-proxy`, `monitor-sensor`.
- **Absent:** `dnf`, `dnf5`, `microdnf`, `flatpak`, `snapshot`, `firefox`, `chromium`, `pipewire`, `wireplumber`, `libcamera`, `wlr-randr`. Only `rpm` 6.0.2 exists.
- No on-device compiler (`gcc/cc/make` absent; only `python3` + `pkg-config`).

## Wi-Fi (live)
- `wlan0` connected, `192.168.178.167/24`, default route via `192.168.178.1`, IPv6 global.
- HTTPS: `gstatic/generate_204` → 204; `https://www.google.nl` → **200**; DNS resolves; system clock correct; CA bundle present.
- The A51 `/new` AP-path fix remains intact; A54 UI stage-machine fix remains deployed.

## Units (all healthy)
`nuxel-bridge`, `nuxel-http-bridge`, `nuxel-button-manager`, `nuxel-wayland`,
`nuxel-wl-fb`, `nuxel-orientationd`, `nuxel-portal`, `nuxel-touch-arm`, `seatd` —
0 failed units.
