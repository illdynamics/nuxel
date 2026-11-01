# PWNAGE-50000 — task / evidence tracker

Live target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora 43 ARM64,
kernel 4.14.253-gf7194c1d15ed-dirty, Wi-Fi SSH `root@192.168.178.167`.

| # | Task | Source | Deployed | Evidence | Status |
|---|---|---|---|---|---|
| 1 | Preserve Phoc kbase compositor | existing + kbase wrapper | yes | `evidence/pwnage-50000/baseline/` | **PASS** |
| 2 | Graphics profile policy (single validated source) | `configs/nuxel/graphics/graphics-profile.json`, `tools/s10plus/a45/nuxel-graphics-profile` | yes | `tests/pwnage50000/` | **SOURCE_VERIFIED / DEPLOYMENT_VERIFIED** |
| 3 | Remove unconditional software forcing from session/native launcher | `tools/s10plus/a45/nuxel-session.sh`, `services/nuxel-bridge/src/api.py` | yes | `tests/pwnage50000/test_no_global_software.py` | **PASS (software default retained explicitly)** |
| 4 | kbase surfaceless EGL probe | `tools/s10plus/a67/nuxel-kbase-egl-probe.c` | yes | `evidence/pwnage-50000/egl/probes.json` | **GPU_CONTEXT_VERIFIED** |
| 5 | Wayland EGL probe against live Phoc | `tools/s10plus/a67/nuxel-wayland-egl-probe.c` | yes | `evidence/pwnage-50000/egl/probes.json` | **BLOCKED (live Phoc has no linux-dmabuf)** |
| 6 | Wayland EGL + udmabuf canary on second compositor | `tools/s10plus/a67/nuxel-wsi-canary.sh`, Mesa/Wlroots patches | staged | `evidence/pwnage-50000/egl/wsi-canary-success.txt` | **WAYLAND_EGL_VERIFIED (canary only)** |
| 7 | Live Phoc with linux-dmabuf | patched wlroots | canary reverted | coredumps 17951/19302/29214 | **BLOCKED (compositor crash)** |
| 8 | WebKitGTK accelerated compositing on live Home | profile `software` | safe fallback | `evidence/pwnage-50000/webkit/` | **BLOCKED (same linux-dmabuf blocker)** |
| 9 | GTK3 / GTK4 independent diagnostics | probe sources in `tools/s10plus/a67/` | source + builder | `tests/pwnage50000/` | **NOT_TESTED on live** |
| 10 | Graphics Settings layered panel | `pwa/nuxel-apps/settings/graphics-diagnostics.js` | yes | `evidence/pwnage-50000/webkit/graphics-diagnostics.json` | **OWNER_VISIBLE (pending physical check)** |
| 11 | Gallery image/video playback | `pwa/nuxel-apps/photos/js/photos.js` | yes | media endpoint 200 + native-player path | **SOURCE_VERIFIED** |
| 12 | Top bar all-icon cluster + better Wi-Fi glyph | `pwa/nuxel-home/js/status-bar.js`, `css/status-bar.css` | yes | PWA files in `/usr/share/nuxel` | **SOURCE_VERIFIED / DEPLOYMENT_VERIFIED** |
| 13 | Top-edge-only QS gesture | `pwa/nuxel-home/js/gestures.js`, `status-bar.js` | yes | source + tests | **PASS** |
| 14 | Navdock back/back-long/home buttons | `tools/s10plus/a45/nuxel-navdock.c`, `nuxel-pwa-host.c` | live process running | `/run/nuxel-navdock.state` shows Back/Home actions | **OWNER_VISIBLE (Back/Home observed)** |
| 15 | OSD over native apps | `tools/s10plus/a45/nuxel-osd.c` | live | pixel check over Firefox for volume and power-menu cards | **OWNER_VISIBLE (both cards)** |
| 16 | Flashlight | `services/nuxel-bridge/src/flashlight_provider.py` | live | `s2mpb02_store ... 300mA`, state ON | **OWNER_VISIBLE pending physical torch check** |
| 17 | DND | `dnd_provider` + notifications | live | provider config | **SOURCE_VERIFIED** |
| 18 | Idle CPU / performance | finite location pulse, idle FPS pacing, profile | yes | `/run/nuxel-wl-fb.state` | **PARTIAL** |
| 19 | USB file transfer | MTP | live | MTP enumerates; Finder does not speak MTP | **BLOCKED_HOST_PROTOCOL (use OpenMTP/MTPLX)** |
| 20 | Flatpak | requires `CONFIG_USER_NS=y` | no | `zcat /proc/config.gz` | **BLOCKED_KERNEL (no ADB/TWRP device attached)** |
| 21 | Mobile network / camera / sensors Settings | bridge `system.diagnostics` | live | PWA Settings tabs | **DEPLOYMENT_VERIFIED** |

## Remaining work / blocker

`linux-dmabuf` is the single missing production component. A second headless Phoc with the patched
wlroots advertises it and the full Wayland EGL + udmabuf export/import + swap-buffers path passes
(`gl_renderer=Mali-G76 MC12 (Panfrost)`). Enabling the same global in the live kbase Phoc causes a
SIGSEGV/SIGBUS, so the default session remains on the proven surfaceless compositor with software
WebKit. Do not mark WebKit accelerated until the live compositor crash is fixed and the real Home
PWA is observed on the AMOLED.
