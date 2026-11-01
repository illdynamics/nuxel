# PWNAGE-52000 — installed app responsiveness matrix

Date: 2026-11-01
Target viewport: S10+ 1440×3040 panel, Phoc/Wayland logical 720×1520 (360×760 CSS px at scale 2).
Automated layout audit: Chromium 156 headless, mobile emulation, `scrollWidth`/`clientWidth`
and element-right checks. Source: `tests/pwnage52000/test_app_responsive.py` and the
CDP audit transcript below.

## PWA inventory (on-disk registry tree)

| App | Type | Installed | 320×640 | 360×760 | 760×360 landscape | Keyboard | Horizontal page pan | Notes |
|---|---|---|---|---|---|---|---|---|
| Authenticator | PWA | yes | PASS (after header wrap) | PASS | PASS | CSS safe | none | fixed 3 px header overflow at 320 removed |
| Browser | PWA | yes | PASS | PASS | PASS | CSS safe | none | native WebKit host |
| Calculator | PWA | yes | PASS | PASS | PASS | CSS safe | none | 4/5-column pad inside viewport |
| Calendar | PWA | yes | PASS | PASS | PASS | CSS safe | none | 7-column month grid is intentionally dense |
| Camera / Gallery | PWA | yes | PASS | PASS | PASS | CSS safe | none | capture blocked by kernel/firmware, not by layout |
| Cleanup | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Clock | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Console (serial) | PWA | yes | PASS | PASS | PASS | CSS safe | none | log area is an internal scroller |
| Console USB | PWA | yes | PASS | PASS | PASS | CSS safe | none | log area is an internal scroller |
| Console Wi-Fi | PWA | yes | PASS | PASS | PASS | CSS safe | none | log area is an internal scroller |
| DevMgmt | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Downloader | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Files | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Mail | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Maps | PWA | yes | PASS | PASS | PASS | CSS safe | none | no fix claimed without provider |
| Media | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Notes | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| NuxTore | PWA | yes | PASS | PASS | PASS | CSS safe | none | header/seal/toolbar now wrap below 520 px |
| PenguInterface | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Photos | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Recorder | PWA | yes | PASS | PASS | PASS | CSS safe | none | capture path blocked by audio topology |
| Remote scrcpy | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Remote VNC | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Remote XRDP | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Root & Sudo | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Settings | PWA | yes | PASS | PASS | PASS | CSS safe | none | all 18 tabs audited; tab rail scrolls 1568 px inside 320 px |
| SnekByte | PWA | yes | PASS | PASS | PASS | CSS safe | none | game controls use clamp() |
| Terminal | PWA | yes | PASS | PASS | PASS | CSS safe | none | terminal area is an internal scroller |
| Weather | PWA | yes | PASS | PASS | PASS | CSS safe | none | |
| Home / launcher | PWA | yes | PASS | PASS | PASS | CSS safe | none | quick-settings third row hidden until expanded |

All 30 documents carry a viewport meta tag and the shared
`pwa/nuxel-common/responsive.css` contract. The audit found zero
`documentElement.scrollWidth > clientWidth + 1` and zero body overflow at
320×640 and 760×360 after the Authenticator/NuxTore fixes.

## Native / Flatpak inventory

| App | Type | Installed | Layout result | Honest status |
|---|---|---|---|---|
| GNOME Software | native GTK | yes | GTK/libadwaita adaptive; opens via portal | launch is available but first-run page needs network; no layout change required |
| GNOME System Monitor | native GTK | yes | GTK3 adaptive; window can be resized to 360 CSS px | present |
| mpv | native GTK/GL | yes | client area scales; video keeps aspect | present (no video content in this pass) |
| GNOME Loupe | native GTK | package/desktop present | not independently layout-tested | **UNVERIFIED** launch on glass |
| GNOME Papers | native GTK | package/desktop present | not independently layout-tested | **UNVERIFIED** launch on glass |
| File Roller | native GTK | package/desktop present | not independently layout-tested | **UNVERIFIED** launch on glass |
| Firefox (Flatpak) | Flatpak | yes | sandbox does not start: `statx ... No data available` | **BLOCKED_KERNEL** (user namespace / vendor LOD gate; `unshare -U` EPERM) |
| VLC (Flatpak) | Flatpak | yes | same sandbox gate | **BLOCKED_KERNEL** |
| Signal (Flatpak) | Flatpak | yes | same sandbox gate | **BLOCKED_KERNEL** |
| Stremio (Flatpak) | Flatpak | yes | same sandbox gate | **BLOCKED_KERNEL** |

Flatpak apps are NOT marked responsive because the sandbox cannot start on this
kernel. That is a capability result, not a layout pass.

## Keyboard / form checks

- Shared `responsive.css` keeps form controls `max-width:100%` and bounded
  dialogs `max-width: calc(100vw - 24px)`.
- No page sets `touch-action:none` on `body`; vertical pan remains native.
- Login/unlock prompts use `min-height:44px` controls.
- The Settings tab rail is the only intentional horizontal scroller.
