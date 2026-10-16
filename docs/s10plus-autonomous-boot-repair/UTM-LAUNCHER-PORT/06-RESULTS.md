# 06 — RESULTS

## 1. The A28 gate (host, reproducible)

```
$ sh tools/s10plus/a28/test-launcher.sh
== 1. generated launcher tables are up to date ==
LAUNCHER_REGISTRY_CHECK_OK tools/s10plus/a28/generated/nuxel-launcher.h
EMOJI_ATLAS_CHECK_OK tools/s10plus/a28/generated/nuxel-emoji-atlas.c
== 2. evdev request numbers vs the ARM64 kernel UAPI ==
   PASS A28_ABI_PROBE_OK (EVIOCGBIT/EVIOCGABS/EVIOCGPROP + 24-byte input_event)
== 3. host gate: the launcher screen, measured ==
   checks passed: 53
   WALLPAPER_OK path=…/assets/nuxel-background.png src=941x1672 panel=1440x3040 png=1257938
== 4. the wallpaper decoder vs an independent reference ==
   checked 1440x3040 pixels against the reference: worst=0 mean=0.0000
WALLPAPER_DECODE_OK
== 5. the ARM64 binary ==
   PASS nuxel-ui-a28 852640 bytes (budget 1200000) 726b7675a43b13b4…
A28_LAUNCHER_GATE_OK
```

The 53 host checks include, per app in the registry:

* `tile <App> is <colour>@0x33 over the page` — the tile background is the app's
  own `color` at the CSS alpha over the actual (wallpapered) background, compared
  against an independently computed blend (tolerance ±2/255);
* `tile <App> has inked glyph pixels (n)` — the emoji glyph really rasterised
  (Calendar 6613, Camera 6100, Contacts 2127, Files 2988, Mail 3344, Notes 4347 px);
* `tap centre hits <App>'s launch action` — hit-testing at the tile centre
  returns that app's action;
* dock slot → app, dock tile colour, dock glyph ink, dock band = `#0d1f3c`;
* `the Nuxel title is drawn in the header` + `tapping the title opens the
  diagnostic fallback page`;
* the console surface: `page=launcher`, `search mail` (1 hit, Mail among them),
  `searchclose`, a no-match query, `launch org.nuxel.Notes`,
  `launch Settings` — each with an honest `unavailable` verdict and reason;
* `all 7 pages render with 0 layout violations` (no overlap, nothing outside the
  safe area, no status-bar ink in the punch-hole band).

The A27 gate still passes against the same source (it is a subset: layout at four
scales × four fixtures with zero violations, plus the font-atlas reproducibility
and the ioctl-defect check), so no diagnostic behaviour regressed.

## 1b. The UTM consistency gate (measured against the live VM launcher)

```
$ sh tools/s10plus/a28/verify-utm-consistency.sh
== UTM launcher geometry (guest 192.168.64.3, WebKitGTK on the live display) ==
   … 74 PASS, 0 FAIL …
A28_UTM_CONSISTENCY_OK — the S10+ adapter and the UTM launcher agree on the
registry, the order, the tint rule, the icons and every geometry token
```

Full output: `evidence-utm-consistency.txt`; raw DOM measurements:
`evidence-utm-geometry.json`. This gate also found the responsive breakpoint
(`@media (max-width: 480px)`: `--app-icon-size 56px`, `--grid-padding 12px`) that
the base `:root` values do not show, and the port was corrected to the effective
values because the VM and the phone render in the same width band.

## 2. Binary

```
build/out/s10plus/a28/nuxel-ui-a28
  ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
  852,640 bytes   sha256 393619763345979f7aa83b68c1e0a1e320fb6589119258b43b818cc10f1eb84b
  (A27 was 721,496 bytes; +131 KB is the launcher: registry tables, emoji atlas,
   the PNG/inflate decoder and the launch path.  Rebuild with
   `sh tools/s10plus/a28/build-a28.sh --report`; hashes/sizes live in
   build/out/s10plus/a28/a28-report.txt.)
```

Size is a deployment constraint, not a preference: this binary travels over the
CDC-ACM console in base64 lines. The gate fails above 1,200,000 bytes.

## 3. Consistency with UTM (source-level, no similarity scores)

| Launcher property | VM (PWA) | S10+ (this port) | Same source of truth |
|---|---|---|---|
| app count / grid / dock | 9 apps, 6 grid, 3 dock (`vm-verify-pwa.sh`, live display) | 9 / 6 / 3 (compiled from `apps.js`) | `pwa/nuxel-home/js/apps.js` |
| order | `getAllApps()` name sort, dock = sorted docked | identical, asserted in the gate | same |
| colours | `<color>@0x33` tiles, `color` glyphs, `--bg-secondary` dock | identical, measured per tile | `style.css` + `launcher.js` |
| geometry | 36 / 80 / **12** / **56** / 16 / 12 px effective (+ `status-bar` padding 16) | identical, asserted in C (`_Static_assert`) and measured on the VM DOM | `style.css :root` + its `@media (max-width: 480px)` band |
| icons | registry emoji, tinted | registry emoji, tinted (Noto Emoji, OFL) | `apps.js` |
| background | `assets/nuxel-background.png`, cover | the same file, cover, byte-exact decode | `style.css` + `assets/` |
| launch | `pwa:open` iframe / `nuxel-<app>://` | served URL via the repo's own browser candidates / `native_binary` | `apps.js` + `app_registry.json` |

## 4. Physical deployment and physical tests

| Test | State |
|---|---|
| Deploy to the handset over the live console | **NOT RUN — the handset was not on USB during this session** (no `/dev/cu.usbmodem*`; `utmctl list` showed the VM `stopped` at session start, no S10+ gadget enumerated) |
| Finger tap / swipe / release, no ghost taps, correct coordinates | **NOT RUN** (same reason; §03.5 lists exactly what to capture) |
| Launcher visible on the glass, apps opening | **NOT RUN** |

The exact commands to run the moment the phone is reachable are in
[`05-STARTUP.md`](05-STARTUP.md) §4 and [`NEXT-ACTION.md`](NEXT-ACTION.md). No
statement in this directory claims a physical result that was not measured.
