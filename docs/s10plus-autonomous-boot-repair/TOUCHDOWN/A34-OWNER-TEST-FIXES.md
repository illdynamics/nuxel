# A34 owner-test fixes — "the swipes and buttons did nothing"

Date: 2026-10-17 (CEST)
Device: S10+ (`fedora`, 4.14.253, aarch64), live console `/dev/ttyACM0`
Deployed UI revision: `A34-touchdown-cancel`

## What the raw logs actually showed

The owner's tests were not ignored by the kernel or by WebKit.  The evidence was
present in the files the console can read:

| Evidence | What it proved |
|---|---|
| `/run/nuxel-home.state` 13:21:39 and 13:39:22 | Real touches reached WebKit and produced `pointerdown/touchstart/pointerup/click` on `id=close` (the terminal's Close button). |
| `/run/nuxel-home.state` 13:21:32–13:22:01 | A fullscreen **native terminal window** was opened (`TERMINAL_WINDOW_OPEN`), then Close was clicked twice. No `TERMINAL_WINDOW_CLOSED` followed. |
| `/var/log/nuxel/buttons.log` 13:21:42–13:22:01 | Physical Power/Volume did work: `screen-toggle`, `VOLUME_STEP`, `MENU_OPEN index=0 id=cancel`, `MENU_SELECT id=cancel`. |
| `/usr/share/nuxel/runtime/osd.json` at open | The power menu published `entries` + `index`, but `osd.js` ignored both, so the glass only got a tiny empty box that auto-hid after 1.8 s. |
| `buttons.log` 10:13:01, 12:13:01 | A plain tap emitted `action=back`. That is the signature of `TOUCH_DOWN` being sent at `ABS_MT_TRACKING_ID`, before the frame's `ABS_MT_POSITION_X/Y` arrived, i.e. with the previous frame's coords `(0,0)`. |

Net effect: the terminal became an unclosable fullscreen top-level surface.  Every
later swipe/tap (Settings, the status-bar pull, QS) landed on the terminal, and
the power menu/volume OSD rendered in the launcher **behind** that surface.  The
hardware buttons were firing; the owner could not see their result.

## Root causes and fixes

1. **MT parser used stale coordinates for DOWN.**
   `ABS_MT_TRACKING_ID` arrives before `ABS_MT_POSITION_X/Y`; the old manager
   emitted DOWN immediately with `(0,0)`.  The new `nuxel-mt.h` emits
   DOWN/MOVE/UP only at `SYN_REPORT`, after the frame's coordinates are known.
   This removes the spurious edge-back action and makes the bottom-zone swipe
   (`home`) possible.

2. **`term.close` killed the PTY but not the window.**
   `nuxel-pwa-host` now has `term_close_window()`, used by `term.close`,
   `close-terminal`, and the logical `home` action.  Returning Home closes the
   native terminal surface instead of leaving it in front of Home.

3. **The terminal page never loaded `host-bridge.js`.**
   It is a top-level WebKit view, not an iframe, so `window.NuxelHost` was
   `undefined`: Close and every on-screen key silently did nothing.  The terminal
   page now loads `host-bridge.js` and `osd.js`.  `HOSTBRIDGE_READY
   available=true inIframe=false` is logged when it loads.

4. **The launcher's Terminal tile created two surfaces.**
   It opened an iframe *and* the native terminal.  With the host available the
   tile now calls `NuxelHost.action('open-terminal')` and opens only the real
   window.

5. **The same-origin app Close hook did not exist.**
   Settings/Cleanup/DevMgmt/Nuxtore/Root Control call
   `window.parent.NuxelLauncherClose()`; it was defined nowhere.  `app.js` now
   defines it and each app falls back to removing its own frame.

6. **Quick Settings had a listener but no dispatcher.**
   `status-bar.js` now emits `gesture:qs` after a real >=24 CSS px vertical pull,
   uses pointer capture so the gesture survives leaving the 36 px bar, and the
   CSS sets `touch-action:none` on the bar.

7. **The power menu published entries that nothing rendered.**
   `osd.js` now renders the persistent menu card, follows `index` from Volume
   Up/Down, keeps it visible until `menu-close`, and sends taps through the same
   `menu-select <n>` control verb the hardware path uses.  Cancel is entry 0.
   The terminal page loads the same OSD, so the menu and volume OSD are visible
   even while the terminal is the top surface.

## Verification performed on the device

* `nuxelctl action open-terminal` → `TERMINAL_WINDOW_OPEN`; `nuxelctl action home`
  → `TERMINAL_WINDOW_CLOSED` + `HOST_ACTION home -> launcher page`, and the
  snapshot returned to the exact Home frame.
* `nuxelctl action close-terminal` → `TERMINAL_WINDOW_CLOSED` +
  `TERMINAL_EXIT`.
* Terminal open + `menu-open` → `osd.json` contains all 11 entries; snapshot
  shows the menu card over the terminal; `menu-select 0` → `MENU_SELECT
  id=cancel`, menu closes.
* `nuxelctl action screen-toggle` → `bl_power` 0 → 4 → 0 and brightness
  12800 → 0 → 12800.
* Offline tests: `test-button-fsm.py` 0 failing; `run-touch-tests.sh --quick`
  ALL PASS (including the new `test-touch-mt.c`); launcher registry/parity
  PASS; P3 suite ALL PASS.
* Deployed file SHA-256 values match the repository for every changed asset and
  both binaries.

## Remaining owner test (physical only)

The kernel and WebKit layers are now correlated.  The only thing an offline test
cannot prove is the finger itself:

1. From Home, tap **Settings**, then the ✕ → Home.
2. Tap **Settings**, then swipe up from the bottom edge → Home.
3. Pull down from the status bar → Quick Settings.
4. Tap **Terminal**, type a character, tap **Close** → Home.
5. Power once → dark; Power once → Home.  Hold Power ~2.5 s → menu; Volume
   moves the highlight; short Power selects Cancel.

If any step still produces no change, the new evidence markers are
`MENU_OPEN/MENU_NAV/MENU_SELECT`, `TERMINAL_WINDOW_OPEN/CLOSED`,
`HOSTBRIDGE_READY`, `FSM_ACTION source=touch action=home`, and
`NUXEL_INPUT EVT pointerdown ...` in the same files used above.
