# NUXEL — PORTING THE UTM LAUNCHER TO THE GALAXY S10+ (cycle A28)

**Directive honoured:** *no new launcher, no redesign, no image analysis.*  The
launcher that runs in the UTM VM was located in source, its app registry, icons,
styling and startup were identified, and that same implementation now runs on
the S10+ through a **minimal platform adapter** whose only reason to exist is
the phone's display stack.

## What "the UTM launcher" actually is (measured, not assumed)

| Fact | Evidence |
|---|---|
| The launcher is **Nuxel Home**, `pwa/nuxel-home/` | `services/nuxel-web.service`: *"Nuxel PWA Static Web Server (**nuxel-home launcher** on :8000)"* |
| It is served on `127.0.0.1:8000` and rendered by a WebKitGTK browser in the Phosh session | guest: `python3 -m http.server 8000 --bind 127.0.0.1` (pid 878); `epiphany` present, `chromium`/`firefox` **absent**; `vm/vm-verify-pwa.sh` renders it in WebKitGTK 4.1 |
| The app model is `pwa/nuxel-home/js/apps.js` | 9 apps, 3 docked; `vm-verify-pwa.sh` observed **"app grid has 6 item(s), dock has 3 item(s)"** on the live VM display — exactly `getAllApps()` (name sort) minus `getDockedApps()` |
| The styling is `pwa/nuxel-home/css/{style,launcher,search,status-bar}.css` | tokens (`--bg-primary #0a1628`, `--dock-height 80`, `--app-icon-size 64` in `:root`, **56 effective** — see the media query below) |
| The icons are the registry's emoji, tinted with each app's colour | `js/launcher.js`: `background: <color>33; color: <color>` |
| The native GTK4 twin (`shell/nuxel-home-native/`) is installed but **does not start in the VM** | guest: `nuxel-home-native.service` *disabled*, `nuxel-home-kiosk.service` *disabled*, `/usr/local/bin/nuxel-home` → `ImportError: attempted relative import with no known parent package` |

Full detail: [`01-DISCOVERY.md`](01-DISCOVERY.md).

### The breakpoint that mattered

`style.css` ends with responsive overrides the launcher really uses:

```css
@media (max-width: 480px) { :root { --app-icon-size: 56px; --grid-padding: 12px } }
@media (min-width: 768px) { :root { --app-icon-size: 72px } }
```

The VM renders the launcher at 720x1440 physical = **360 CSS px**, i.e. inside
the `<=480px` band, and the S10+ panel is 1440x3040 = 4 x (360x760) — the *same*
band. Measuring the live DOM in the VM's WebKitGTK (`tools/s10plus/a28/
verify-utm-consistency.sh`) showed grid icons of **56x56**, not 64x64, and a grid
padding of **12px**. The generator now evaluates the media queries at the phone's
CSS width and emits the **effective** tokens (`L_*`) alongside the un-overridden
`:root` values (`LB_*`), so the phone matches what the VM actually draws.

## Why the port is Option C (minimal platform adapter), with measurements

`docs/.../PHOSH-ASSESSMENT.md` and the A27 status record already establish the
phone's constraint: the Samsung 4.14.253 vendor kernel is built with
`# CONFIG_DRM is not set`, so there is **no `/dev/dri`**, no KMS, no GBM/EGL
output, therefore no wlroots/Phoc/Phosh session; and the Fedora image contains
phonosh/phoc RPMs but **no browser engine**. Option A (run the PWA directly) and
Option B (add a display bridge) are therefore not available on this hardware
today — the analysis, including what Option B would require, is in
[`02-COMPATIBILITY.md`](02-COMPATIBILITY.md).

Option C is what the mission prescribes for exactly this case: **reuse the real
launcher's source, application model, styling definitions and assets, with only
the minimum platform-specific integration.**

## What was built (all generated from the launcher's own files)

```
tools/s10plus/a28/
  gen-launcher.py         apps.js + style.css + app_registry.json -> generated/nuxel-launcher.h
                          (app list, order, docking, colours, emoji codepoints, design tokens)
  make-emoji-atlas.py     the registry's emoji codepoints, rasterised from Noto Emoji (OFL 1.1)
  evdev-abi-probe.c       the touchscreen numbers vs <linux/input.h>, cross-compiled
  test-launcher.c/.sh     the acceptance gate (host-measured launcher screen + ABI + ARM64 gate)
  nuxel-ui.rev / .service the delivery rev and unit the BOOT candidate carries
  compare-wallpaper.py    pixel-for-pixel check of the freestanding PNG decoder

tools/s10plus/nuxel-ui.c  + the launcher page, its wallpaper decoder and its app-launch path
```

The adapter adds **no** colour, icon, app, order or layout of its own: tapping a
tile launches the registry's own command (`type: pwa` -> the served URL through
`nuxel-pwa-launcher`/chromium/firefox/epiphany; `type: native` ->
`app_registry.json`'s `native_binary`), and an app that cannot run reports
**why**, by name, in the UI toast, in `/var/lib/nuxel/ui-apps` and in the log.

## Status

| Item | State |
|---|---|
| The launcher screen, rendered from the launcher's registry/tokens/icons | **PASS** (host gate: 53 checks, [`06-RESULTS.md`](06-RESULTS.md)) |
| The wallpaper asset decoded by the phone's own decoder | **PASS — byte-exact** vs an independent numpy reference over all 4,377,600 px |
| Touchscreen ioctl/ABI correctness | **PASS** (compiled against `<linux/input.h>` for aarch64) + a real-finger capture is still outstanding |
| Default screen after boot, animation handoff, fallback retained | wired (same `nuxel-ui.service`), see [`05-STARTUP.md`](05-STARTUP.md) |
| UTM ↔ S10+ consistency | **PASS — measured from the live launcher DOM** (74 checks: registry, order, docking, glyphs, colours, tint rule, geometry tokens), [`evidence-utm-consistency.txt`](evidence-utm-consistency.txt) |
| Physical deployment + finger on the glass | **NOT DONE — the handset was not on USB during this session** ([`07-LIMITATIONS.md`](07-LIMITATIONS.md)) |
| PWA/native apps actually opening | **BLOCKED by the image, not by the launcher** — the precise reasons are recorded in [`07-LIMITATIONS.md`](07-LIMITATIONS.md) |
