## Fixed

**Default rotation**
- Per-app rotation is now applied **before** a native app launches, not after, avoiding the startup resize race.
- Rotation is also applied when:
  - an app is already running and is re-focused,
  - an app is resumed from Recents/Home,
  - a PWA is opened or resumed.
- Added a foreground watcher so native apps launched outside the Nuxel launcher still respect their App setting.
- Verified:
  - `Caprine` starts/resumes in **landscape**.
  - Home returns to **portrait**.
  - Re-opening Caprine while it is still running returns it to landscape.
  - PWA orientation works too (tested with DevMgmt: portrait at Home → landscape when opened).

**Keyboard**
- Root cause #1: Stevia folded the OSK without disabling text input, so tapping an already-focused field emitted no new focus/enable event.
  - Rebuilt phoc with a hook that re-sends `sm.puri.OSK0.SetVisible(TRUE)` when a touch/button press lands on a surface with an enabled, focused text input.
- Root cause #2: `ydotoold` exposes a uinput keyboard, which Stevia treated as a hardware keyboard and used to suppress the OSK.
  - Persisted `mobi.phosh.osk ignore-hw-keyboards=true` in the session startup and keyboard apply scripts.
- Verified on device:
  - Native GTK app: tap field → keyboard appears.
  - Hide keyboard → tap same already-focused field → keyboard appears again.
  - Nuxel PWA: same behavior confirmed.

## Device state
- Rebooted and verified all services active.
- Unlocked, at Home, portrait.
- Caprine is running in the background and will open in landscape.

## Files changed
Repo:
- `services/nuxel-bridge/src/api.py`
- `pwa/nuxel-home/js/app.js`
- `tools/s10plus/a45/nuxel-session.sh`
- `tools/s10plus/a33/nuxel-keyboard-apply.sh`
- New: `tools/s10plus/a75/` — phoc patch, README, and build/install script

Deployed:
- `/usr/lib/nuxel/nuxel-bridge/api.py`
- `/usr/share/nuxel/pwa/nuxel-home/js/app.js`
- `/usr/lib/nuxel/nuxel-session.sh`
- `/usr/local/bin/nuxel-keyboard-apply.sh`
- `/usr/sbin/phoc` + `/usr/bin/phoc` (custom phoc 0.54.0 build)

Backups:
- `/var/backups/nuxel/phoc-osk-reshow-20261107T173947Z/phoc.prev`
- `/var/backups/nuxel/keyboard-orientation-20261107T173911Z/`

## Honest limitation
Caprine 2.61 bundles Electron 29 / Chromium 122, which only implements the removed `zwp_text_input_v1` protocol. Phoc/wlroots 0.19 exposes `zwp_text_input_v3`. So Caprine’s **rotation is fixed**, but Chromium 122 still cannot raise Stevia inside Caprine. GTK apps and Nuxel PWAs use v3 and are fully working. Fixing Caprine’s keyboard would require a newer Electron/Caprine build with text-input-v3, or a v1 compatibility shim.
tokens used
88,644,371
[codeseeq] stopping owned bridge process (pid=14340)

