# PWNAGE-50000 — graphics and regression report

Date: 2026-11-01
Device: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, Mali-G76 MP12
OS: Nuxel / Fedora 43 ARM64, kernel `4.14.253-gf7194c1d15ed-dirty`
Transport: Wi-Fi SSH `root@192.168.178.167`, key `~/.ssh/wicked_wqn_id_rsa`

## 1. Compositor / kbase baseline

Verified after the changes:

- `phoc` PID holds three `/dev/mali0` fds and `/dev/udmabuf`.
- kbase debugfs reports a context owned by `phoc`.
- `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-web` active.
- `/run/nuxel-gpu-fallback` absent.
- `nuxel-wl-fb.state`: `FRAMES_OK ... decon_pan_failed=0`.
- `/dev/fb0` present; panel 1440×3040, virtual 1440×6080, stride 5760.

Evidence: `evidence/pwnage-50000/baseline/live-baseline.txt`.

## 2. EGL probes

- Surfaceless: **PASS** — `OpenGL ES 3.2 Mesa 26.3.0-devel`,
  `Mali-G76 MC12 (Panfrost)`, FBO pixel `33cc4dff`.
- Wayland against live Phoc: **BLOCKED** — live Phoc does not advertise
  `zwp_linux_dmabuf_v1`; `eglInitialize` fails at `DRI2: failed to create dri2 screen`.
- Wayland canary against a second headless Phoc with the patched wlroots:
  **WAYLAND_EGL_VERIFIED** — `zwp_linux_dmabuf_v1` v3, real Mali renderer,
  udmabuf fd 10, `swapbuffers=1`, `result=PASS`.

Evidence: `evidence/pwnage-50000/egl/`.

## 2.1 Post-reboot verification

A normal `systemctl reboot` was issued. Wi-Fi SSH returned after ~30 s. After boot:

- `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-web`, `nuxel-http-bridge` active.
- `phoc` holds 3× `/dev/mali0` and `/dev/udmabuf`.
- `/run/nuxel-gpu-fallback` absent.
- `FRAMES_OK ... decon_pan_failed=0`.
- `nuxel-navdock` and `nuxel-osd` running; `nuxel-statusbar` is not.
- No `lpcharge` / charger-mode marker on the rebooted cmdline.
- `/dev/fb0` restored; 1440×3040 panel, 1440×6080 virtual, stride 5760.

## 3. WebKitGTK / GTK

Installed: WebKit2GTK 4.1 2.54.1, GTK3 3.24.52, GTK4 4.20.4, Mesa libEGL 25.3.6.

The live WebKit process still has `WEBKIT_DISABLE_COMPOSITING_MODE=1` and
`LIBGL_ALWAYS_SOFTWARE=1` from the validated software profile. This is deliberate:
the compositor cannot yet accept accelerated WebKit buffers. Graphics Settings
now shows the layer separately as `SOFTWARE_FALLBACK` with the exact blocker.

A graphics profile policy now exists; the accelerator mode is available as a
canary but is not the default. `WEBKIT_FORCE_COMPOSITING_MODE` is never set
globally.

## 4. Regression repairs deployed

- Top bar: DOM bar keeps every indicator slot visible; unavailable radios are
  muted and labelled, not hidden. Uses the `01-wifi.png` glyph.
- Quick Settings: top-edge gesture only; drawer scrolling is no longer a shade
  gesture.
- Navdock: short Back = in-app back; long Back = foreground close; Home = Home.
- Scrolling: tap guard raised to 28 px and click suppression to 650 ms.
- Gallery: image endpoint works; video cards open the native mpv player instead
  of relying on WebKit's missing H.264 decoder.
- Screenshots: PNGs are real 720×1520 images; zero-byte files are filtered.
- VLC: launcher no longer pays a fixed 3 s timeout before mpv; set
  `NUXEL_VLC_TRY=1` to test VLC itself.
- OSD: volume card verified over a fullscreen Firefox window by pixel sampling.
- Flashlight: rear_flash driver reports 300 mA torch set; policy max-on raised
  to 10 minutes. Physical torch still needs owner confirmation.
- Charger/LPM recovery service is enabled and exited successfully on this boot.
- Mobile network, Camera and Sensors Settings tabs use read-only driver
  diagnostics and report honest blockers.

## 5. Performance

Idle bridge pacing already skips unchanged frames (2 fps idle). Removed the
infinite location-pulse animation (now three iterations) and kept the finite
service-worker cache bump. Final CPU numbers must be re-measured after reboot
with no Firefox window open.

## 6. Honest blockers

| Area | Status | Reason |
|---|---|---|
| WebKitGTK accelerated compositing | **BLOCKED** | live Phoc cannot expose linux-dmabuf without crashing |
| DMA-BUF presentation by live Phoc | **BLOCKED** | same compositor crash; canary proves userspace sequence |
| GTK3 GL / GTK4 GL | NOT_TESTED | probes ship, but the live WSI is unavailable |
| Flatpak | BLOCKED_KERNEL | `CONFIG_USER_NS=n`; no ADB/TWRP device attached to flash a new kernel |
| USB file transfer to Finder | BLOCKED_HOST_PROTOCOL | MTP enumerates; macOS Finder does not mount MTP. Use OpenMTP/MTPLX |
| Mobile network | NOT_SUPPORTED_ON_DEVICE | no CP host interface / ModemManager Shannon plugin |
| NFC / camera | BLOCKED_FIRMWARE | controller/driver present, firmware missing |
| Sensors | present-unreadable | SSP hub is down (`ssp_down=true`) |

## 7. Status matrix

| Field | Value |
|---|---|
| SOURCE_VERIFIED | yes |
| DEPLOYMENT_VERIFIED | yes |
| GPU_CONTEXT_VERIFIED | yes (Phoc kbase context + surfaceless probe, pre- and post-reboot) |
| WAYLAND_EGL_VERIFIED | canary only, not live Phoc |
| DMABUF_PRESENTATION_VERIFIED | canary only, not live Phoc |
| WEBKIT_ACCELERATION_VERIFIED | NO — BLOCKED |
| GTK3_GL_VERIFIED | NOT_TESTED |
| GTK4_GL_VERIFIED | NOT_TESTED |
| BRIDGE_PERFORMANCE_VERIFIED | partial (idle pacing measured; new benchmark pending reboot) |
| OWNER_VISIBLE | navdock Back/Home actions observed in its state log; top bar/gallery/OSD need owner visual confirmation |
| BLOCKED | WebKit acceleration, Flatpak, Finder MTP |

## 8. Rollback

Backups created this run:

- `/var/backups/nuxel/p50000-wlroots-*`
- `/var/backups/nuxel/p50000-mesa-*`
- `/var/backups/nuxel/p50000-policy-*`
- `/var/backups/nuxel/p50000-pwa-*`
- `/var/backups/nuxel/p50000-wsi-canary-*`

The live session is back on the pre-canary wlroots and gallium hashes. The Mesa
EGL backup `/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland` was not touched.
