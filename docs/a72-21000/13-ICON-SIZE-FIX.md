# NUXEL A72 / 21000 — LOCKSCREEN ICON EQUAL-SIZE FIX

Owner report (21000 kickoff): the three lockscreen penguins are NOT the same
size — "the charging one is bigger than the other two."

## Root cause (proven, not assumed)

The three indicators render into uniform `68x68` flex cells with
`object-fit: contain` (lockscreen.css). `contain` scales each PNG by its
**canvas** edge and the PNGs have different intrinsic aspect ratios and
different transparent padding:

| asset | canvas | painted alpha (10% threshold) | aspect |
|---|---|---|---|
| nuxel-charging.png | 1254x1254 | 1094x1083 | 1.010 |
| nuxel-connected-pc.png | 1374x1145 | 1319x884 | 1.492 |
| nuxel-live-console-active.png | 1254x1254 | 974x901 | 1.081 |

In the 68px box the painted artwork therefore rendered at:
- charging ~59.3 x 58.7 px
- PC ~65.3 x 43.7 px
- live-console ~52.8 x 48.9 px

The charging penguin was visibly taller than the other two (the exact symptom).

## Fix (minimal, artwork untouched)

`pwa/nuxel-home/css/lockscreen.css` — per-indicator cells widened so the
**contained artwork has the same painted height** as the charging penguin:

```css
.lockscreen-indicator.usb-ind  { width: 91px; height: 76px; }  /* 76/1145*884 = 58.7 */
.lockscreen-indicator.live-ind { width: 82px; height: 82px; }  /* 82/1254*901 = 58.9 */
```

The PNG pixel art, the row `top:184px`, the glow, and the three independent
animations are unchanged. Landscape overrides scaled proportionally.

Cache stamps bumped: `css/lockscreen.css?v=a70.3 -> ?v=a72`,
`sw.js CACHE_VERSION v41-a70-indicator-precision -> v42-a72-icon-size`,
`manifest.json cache_version -> v42-a72-icon-size`.

## Before / after (physical, live S10+)

Live `IND` geometry receipts from `/run/nuxel-home.state`:

Before (uniform 68px cells):
```
active=charging:70,184,68x68|usb:146,184,68x68|live:222,184,68x68
```
After (equal-height cells):
```
active=charging:52,191,68x68|usb:128,187,91x76|live:227,184,82x82
```

Screenshots (360x760, wlr-screencopy -> PPM -> PNG):
- `evidence/icon-size-fix/before-unequal-size-360x760.png` (sha256 9ffc737b…)
- `evidence/icon-size-fix/after-equal-size-360x760.png`  (sha256 380010dc…)

## Deployed hashes (device sha256 readback == repo)

| path | sha256 |
|---|---|
| css/lockscreen.css | 74bf60926bcd256008a2428bdb33eedcf5ea53016fc952725aa1d8e26f08f01d |
| index.html | 9c42cfa0f8b0c3ac0673300812b16495b96ae986249e812684017c65a328717f |
| sw.js | 591f9abf54fad593d87dc5613b57ded2b20825fbd46f6c28ec1798a2673f0f50 |
| manifest.json | 8fcb1fef509fb80c6cae3e6b31e69b65d9e149a4ba65d128aa7b5196ec49e1d8 |

Deployment used the framed USB Live Console; `nuxel-wayland.service` was
restarted once (launcher session only — the CDC-ACM `nuxel-console` lives in
`init.scope` and was never touched) so `purge_launcher_cache()` re-fetched the
new CSS. Wi-Fi (state 100), single-nav (`NAVOWNER native-dock=present`), and
all nuxel services verified active after the restart.

## Regression test

`tools/s10plus/a45/test-lockscreen-layout.js` extended with `a72` equal-
painted-height assertions (all three painted heights within 0.6 px; row fits
360px). ALL PASS. `test-lockscreen-indicators.js` ALL PASS.

## Rollback

```sh
# on device:
cp -a /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.prev  /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css
cp -a /usr/share/nuxel/pwa/nuxel-home/index.html.prev        /usr/share/nuxel/pwa/nuxel-home/index.html
cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.prev             /usr/share/nuxel/pwa/nuxel-home/sw.js
cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json.prev     /usr/share/nuxel/pwa/nuxel-home/manifest.json
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd
# then restart the launcher session to purge WebKit caches:
systemctl restart nuxel-wayland.service
```
