# 02 — Change map

## Files changed on-device (deployed)
- `/usr/share/nuxel/nuxel-home/css/launcher.css` (also reachable as
  `/usr/share/nuxel/pwa/nuxel-home/css/launcher.css` via symlink):
  `e3b0c442…` (0 bytes) → `9d56a005…` (12764 bytes), source = repo
  `pwa/nuxel-home/css/launcher.css`. No other deployed file changed.

## Files changed in repository
- `docs/a64-launcher-resurrection/**` (this report + evidence + capture tool).
- `VERSION`: `v0.6.3-beta` → `v0.6.4-beta`.
- (Release) `CHANGELOG.md` entry for v0.6.4-beta.

## Deliberately NOT changed
- `index.html`, `manifest.json`, `sw.js`, `js/apps.js`, `js/bridge.js`,
  `js/status-bar.js` — already A63-correct on-device (`a927dbce…`, `46695729…`,
  `7dc8d755…`, `d68efd0f…`, `bbfc2823…`, `5148a909…`).
- Live-drift files that pre-date A63 and were working:
  `css/style.css` (`5f495948…`), `js/touch-keyboard.js` (`163c8511…`),
  `js/osd.js` (`0866abb0…`), `js/home-settings.js` (`3d667110…`). These differ from
  repo HEAD but define the same CSS variables and were the prior known-good runtime;
  overwriting them would be a broader blast radius than the observed regression.
- Latest SnekByte (`./snekbyte.zip`, launcher registry `org.nuxel.SnekByte`) — untouched.
- Camera/browser, Wi-Fi, USB Live Console, kernel/boot path — untouched.

## Preserved from A63 / 12KMAXIMUM
- Truthful Home battery + SnekByte startup wiring (`apps.js`, `bridge.js`,
  `status-bar.js`, `manifest.json`), app registry dispatch, seven-mode orientation,
  keyboard, rotation, network gate.
