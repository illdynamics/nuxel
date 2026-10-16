# 04 — IMPLEMENTATION: the platform adapter

One binary, one process, one framebuffer owner: `tools/s10plus/nuxel-ui.c`
(freestanding aarch64, raw syscalls, no libc) now renders the **Nuxel Home
launcher** as page 0 and keeps the A23..A27 diagnostic pages as the fallback.

## 1. Everything the launcher shows is generated from the launcher

```
tools/s10plus/a28/gen-launcher.py
  in:  pwa/nuxel-home/js/apps.js                     (app registry, order, docking)
       pwa/nuxel-home/css/style.css                  (:root design tokens, body bg)
       shell/nuxel-home-native/.../app_registry.json (cross-check + native paths)
  out: tools/s10plus/a28/generated/nuxel-launcher.h  (C tables + EFFECTIVE tokens + hashes)
       tools/s10plus/a28/generated/nuxel-launcher.json (report, incl. divergences)

tools/s10plus/a28/make-emoji-atlas.py
  in:  tools/s10plus/a28/assets/fonts/NotoEmoji[wght].ttf (OFL 1.1) + the registry's
       emoji codepoints (from the JSON report)
  out: tools/s10plus/a28/generated/nuxel-emoji-atlas.c  (28px grid / 24px dock)
```

Both generators are **reproducible and checked**: `--check` fails if the file on
disk differs from what the sources produce, and `test-launcher.sh` runs both
checks first, so the phone cannot drift away from the launcher.

Current generated state:

```
LAUNCHER_REGISTRY_OK apps=9 grid=6 dock=3 header=6122 bytes
  media (max-width: 480px) applied: --app-icon-size:56px --grid-padding:12px
  grid: Calendar, Camera, Contacts, Files, Mail, Notes
  dock: Messages, Phone, Settings
  WARNING registry divergence (launcher apps.js is the authority):
    Camera: apps.js=native nuxel-camera:// | app_registry.json=pwa …/camera-gallery/index.html
EMOJI_ATLAS_OK codepoints=9 sizes=[24, 28] glyphs=18 bits=119616 bytes
```

## 2. The launcher page (launcher.css, token for token)

| Element | CSS | Implementation |
|---|---|---|
| page background | `html,body{background-color:#1a1a2e; background-image:url('../assets/nuxel-background.png'); background-size:cover}` | `assets/nuxel-background.png` decoded at runtime (see §3) with `#1a1a2e` as the fallback |
| grid area | `.app-grid{padding:8px var(--grid-padding) 0}` | `y = DSTATUS+8`, `x = --grid-padding` = **12px** (media query) |
| header | `.app-grid-header{padding:12px 4px 20px}`, `.app-grid-title{font-size:28px; background:linear-gradient(135deg,#60a5fa,#122952)}` | 28px glyphs filled with that gradient (`font_draw_grad`) |
| page dots | `.app-grid-indicator .dot{6px}` | `ceil(6/16)=1` active dot, right-aligned in the header |
| app list | `.app-list{repeat(4,1fr); gap:16px 8px}` | 4 columns, cell=(336-3*8)/4=78 design px |
| app tile | `.app-item .app-icon{var(--app-icon-size); radius:16px; background:<color>33; color:<color>}` — **56px** effective | `round_rect_a(..., alpha=0x33)` over the wallpapered canvas + the registry glyph tinted with the app colour |
| app label | `.app-label{font-size:11px; color:var(--text-secondary)}` | 11px, centred, clipped to the cell |
| dock | `.dock{height:80px; background:var(--bg-secondary); border-top:1px solid rgba(255,255,255,.05)}` `.dock-items{gap:20px}` icons 56px, no labels | 3 tiles, 56px, 20px gap, centred, `--bg-secondary` band |
| status bar | 36px, `padding:0 16px`, `rgba(26,26,46,.95)`, time 13px left, battery 22x11 + 11px right | drawn over the wallpaper with alpha 242/13; the 16px inset is `status-bar.css`'s own literal (not the grid token) |
| search | `.search-overlay{top:36px; bottom:0; background:var(--bg-primary)}`, 44px result icons, 15px names, 12px descriptions | overlay + ranked results |

## 3. The wallpaper, decoded on the phone

`style.css` points at `../assets/nuxel-background.png`; the phone image ships it
as `/usr/share/nuxel/nuxel-background.png` (the rootfs builder copies
`assets/nuxel-background.png`). Rather than bloat the binary that must travel
over the CDC-ACM console, the adapter **decodes it at runtime** with a
self-contained `inflate` + PNG unfilter (colour types 0/2/3/4/6, 8-bit,
non-interlaced) and cover-fits it to the panel once with 16.16 fixed-point
bilinear sampling; subsequent frames are a straight word copy.

Measured: the decoded, cover-fitted 1440x3040 output is **identical to an
independent numpy reference, every pixel** (`worst=0 mean=0.0000` over
4,377,600 px), `png=1257938` bytes read from the asset.

Path order: `/usr/share/nuxel/nuxel-background.png`,
`/usr/share/nuxel/nuxel-home/assets/nuxel-background.png`,
`/home/nuxel/nuxel/pwa/nuxel-home/assets/nuxel-background.png`
(and `--wallpaper=PATH` for the offline harness). On success it logs
`WALLPAPER_OK path=… src=941x1672 panel=1440x3040 png=…`; on failure
`WALLPAPER_UNAVAILABLE <reason>` and the PWA's own `background-color` is used.

## 4. Launching applications exactly as the repo does

`launch_app()` reads the registry row and resolves the command:

* `type: pwa` — first `port_listening(8000)` (`/proc/net/tcp{,6}`, state `0A`),
  then the first available of
  `/usr/bin/nuxel-pwa-launcher` (env `NUXEL_APP_ID`/`NUXEL_START_URL`/`NUXEL_DATA_DIR`),
  `chromium-browser --kiosk <url>`, `chromium --kiosk <url>`, `epiphany <url>`,
  `firefox --kiosk <url>` — i.e. the kiosk script's own preference order plus the
  WebKitGTK browser the VM uses.
* `type: native` — `app_registry.json`'s `native_binary` (`/usr/bin/nuxel-*`).

Spawn is `clone(SIGCHLD)` + `execve` (fork semantics: the child gets its own
address space, so the UI's stack is never shared), children are reaped with
`wait4(WNOHANG)` in the main loop, and the outcome is recorded in four places:
the kernel log, `/var/lib/nuxel/ui.log`, `/var/lib/nuxel/ui-apps` (one line per
app: `id started|unavailable reason`), and a toast on the panel. An app that
cannot run is **never** reported as launched:

```
APP_LAUNCH id=org.nuxel.Notes kind=pwa
APP_LAUNCH_RESULT id=org.nuxel.Notes state=unavailable reason=no-pwa-engine-and-server-down
APP_LAUNCH id=nuxel-settings kind=native
APP_LAUNCH_RESULT id=nuxel-settings state=unavailable reason=native-binary-not-installed
```

## 4b. Consistency with the VM, measured (not scored)

`tools/s10plus/a28/verify-utm-consistency.sh` measures the launcher's **computed
styles and bounding boxes inside the running UTM guest** (WebKitGTK 4.1 on the
live Phosh display) and compares them with what the phone compiles in — 74
checks, all PASS (`evidence-utm-consistency.txt`, raw data
`evidence-utm-geometry.json`). Examples:

```
PASS getAllApps() order == the generated registry order
PASS getDockedApps() order == the port's dock order ['Messages', 'Phone', 'Settings']
PASS grid has 4 columns (78px 78px 78px 78px)
PASS dock background is --bg-secondary #0d1f3c
PASS body background-color #1a1a2e (port fallback)
PASS app-grid left padding 12px == the EFFECTIVE --grid-padding (media <=480px)
PASS Calendar icon colour == apps.js #E91E63
PASS Calendar glyph == the registry emoji '📅'
PASS Calendar icon is 56x56 CSS px (port: 56 design px)
PASS Calendar icon background is <colour>@0x33 (launcher.js tint rule)
```

This is the mission's "verify from source and configuration" requirement without
inventing a visual similarity score: the numbers come from the launcher's own DOM.

## 5. Console surface (the fbdev build has no on-screen keyboard)

`/run/nuxel-ui.cmd` accepts, in addition to the A23..A27 commands:
`launch <app-id|app-name>`, `search <text>`, `searchclose`, `apps` (per-app
verdicts), `wall` (wallpaper state), `page=launcher|home|settings|system|logs|power|about`,
`tap X Y`, `orient N`, `screenshot [path] [small]`, `status`, `quit`.

Tapping the launcher's **title** opens the diagnostic pages (the documented
fallback); nothing else on the launcher screen is invented chrome.

## 6. Defects the A28 gates found (and fixed) in the inherited code

1. **Blue was never alpha-blended.** `blend_cov()` (and the new tile blend) looped
   `sh = 0, 8` only — bits 0..15, i.e. red and green; blue was taken from the
   destination. White text on the navy background came out with `b=0x28`. All
   three compositing loops now run `sh = 0, 8, 16`.
2. **The text clip rectangle leaked into composited elements.** `dtext()` sets the
   clip (by design, for `font_draw`), and the new tiles honoured it, so the last
   title on a page silently clipped every later tile. `px_blend()` now follows
   the existing convention (`fill_rect()`/`px()` ignore the clip; only
   `dtext`/`font_draw` respect it).
3. **`wall_dump_ppm()` wrote a 4320-byte row into a 4096-byte buffer** (the
   offline dump path aborted). Row buffer widened and bounds-checked.

Each of these is now impossible to reintroduce silently: the host gate measures
tile colours, glyph ink and hit-testing per app.
