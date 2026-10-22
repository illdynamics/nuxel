# A54 Baseline

**Date:** 2026-10-22 (Europe/Amsterdam)
**Executor:** DeepSeek-v4-pro-thinking, local agent over USB Live Console
**Host:** Darwin 24.6.0 (MacBook), console node `/dev/cu.usbmodem201` matched by
capability (VID 0x18D1 / PID 0x4EE7 / `usbmodem` / serial `NUXEL-S10PLUS-0001`).

## Device under repair (verified live, not from docs)

| Property | Value |
|---|---|
| Model | Samsung Galaxy S10+ SM-G975F (`beyond2lte`) |
| SoC | Exynos 9820 |
| Kernel | 4.14.253 (Samsung vendor lineage) |
| OS | Fedora Linux 43 (Forty Three), `aarch64` |
| Root | `/dev/sda25` (userspace only touched; no partition/flash writes) |
| Bootloader | G975FXXSEFUL1 (read-only observation) |
| Compositor | `phoc` (headless) + `nuxel-wl-fb` screencopy → `/dev/fb0` AMOLED |
| Launcher | WebKitGTK `nuxel-pwa-host` serving `/usr/share/nuxel` on `127.0.0.1:8000` |
| Bridge | `nuxel-bridge` (org.nuxel.Bridge, system bus) + `nuxel-http-bridge` on `127.0.0.1:8080` |

## Source/deployed revision correlation

Repo HEAD at start: `9378d7f` (`nuxel/A52-penguin-camera`, A53 five-mode orientation).
Work performed on branch `nuxel/A54-reliability-hyperfix` (commits `7ffb7ba`, `5876b88`).

Deployed-vs-repo SHA audit (the key finding driving M5):

| File | Deployed | Repo | Verdict |
|---|---|---|---|
| `bridge.py` | `5735b718…` | `9483e125…` | **stale** (missing A52 media store + Camera D-Bus) |
| `api.py` | `5c7f1848…` | (repo has camera RPC) | **stale** (`camera.status` → "Unknown RPC") |
| `media_store.py` | absent | present | **not deployed** |
| `nuxel-orientationd` | `d097529d…` | `d097529d…` | match |
| `status-bar.js` | `b0a98cff…` | `b0a98cff…` | match |
| `qs.js` | `a4587e5f…` | `a4587e5f…` | match |
| `settings.js` | `d65dea16…` | `d65dea16…` | match |
| `wifi-settings.js` | `83bb596e…` | `83bb596e…` | match |

Conclusion: the frontend was current, but the **bridge backend was two revisions
behind** (A51-era), so every PWA-side camera/rotation/battery improvement that
relied on newer bridge methods was silently unavailable.

## Initial live reproduction (read-only, no secrets)

- `nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status`:
  `wlan0:wifi:connected:Nuxel Ziggo5501109`, `wlan1:wifi:disconnected`.
- `ip -br addr`: `wlan0 192.168.178.167/24` + global IPv6; `ip route`: default via
  `192.168.178.1 dev wlan0 proto dhcp metric 600`.
- HTTPS probe: `https://www.gstatic.com/generate_204` → `204` (network layer fully
  live; the reported "Associating DHCP..." was therefore a **UI state machine**
  problem, not a NetworkManager failure).
- `power_supply/battery/capacity` = `100`, `status` = `Full`; bridge reported
  `charging:true` for `Full` (wrong battery glyph) — fixed in A54.
- `nuxel-orientationd status` → `mode=auto`, `sensor.available=false` (no IIO
  scale, no iio-sensor-proxy), `compositor.transform_available=false` (no
  `wlr-randr`).
- `rpm -q snapshot gtk4 libadwaita pipewire wireplumber gstreamer1-plugin-pipewire`:
  snapshot/pipewire/wireplumber not installed; gtk4 + libadwaita present.
- No `dnf`/`microdnf`/`flatpak`; `rpm` 6.0.2 present; `/etc/yum.repos.d/fedora*.repo`
  present; 1.7 GiB free on `/`.
- `/dev/media*` absent; 68 `/dev/video*` nodes enumerated (FIMC-IS vendor nodes).
- `nuxel-wl-snapshot` present at `/usr/local/bin`; composited frame is 720×1520
  (logical 360 CSS px @ DPR 2), Wayland runtime dir `/run/nuxel-wayland`.

Redaction: no PSK, SSID passwords, MACs, or persistent identifiers are recorded.
