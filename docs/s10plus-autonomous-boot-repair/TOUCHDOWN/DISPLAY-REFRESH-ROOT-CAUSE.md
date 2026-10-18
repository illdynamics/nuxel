# DISPLAY REFRESH ROOT CAUSE — A34

## Current measured presentation

`nuxel-display-frame-trace.sh --seconds 3`:

```
FRAMES_OK total 2283 → 2354 (delta 71, 23.67 fps), failures=0, blit_avg_ms=43
display=on, out=720x1520, scale=2, panel=1440x3040
snapshot fnv64=490ff8c15b3f58de
```

The compositor is producing frames, the bridge is consuming them, and the
snapshot matches the live UI. This rules out a global screencopy stall in the
current state.

## What was actually "frozen"

* After the physical tap at 10:13:01Z, the launcher opened Mail in a
  fullscreen iframe. The Mail build has an empty message list, so 92.6% of the
  glass is `#0a1628`; the screenshot shows the Mail top bar and the launcher's
  close `✕`. The Home grid is behind the iframe.
* The owner's "nothing happens" taps were therefore going into a blank app, not
  into the launcher. This is not a missing touch event.
* Restarting `nuxel-wayland` restored Home and loaded the A34 status bar; a
  fresh snapshot shows the wallpaper and icons (23,548 unique colours).
* The owner then physically tapped Calendar at 12:23:39Z; the Calendar PWA
  rendered (screenshot `evidence/a34/calendar-open-physical-tap-1223.png`).
  A host `action home` (same path as the hardware home action) removed the app
  iframe and the next snapshot was Home again (23,547 unique colours vs 295 for
  the Mail frame). The host action is now listened for on `window` as well as
  `document`, which fixes the previously refused `nuxel:action home`.

## Volume overlay

A host-side `volume-up` action wrote `/usr/share/nuxel/runtime/osd.json` and the
launcher's `osd.js` polled it. A screenshot taken 2 s later contains a bright
OSD box in the expected top-centre region (1,511 bright pixels; none in the
same region before the action). **No Power press was involved.** The stale-OSD
report is not reproducible in the current state.

## Startup wallpaper

The A33 handoff completed `ANIM_MIN_CYCLE_COMPLETED`; a service restart shows
Home automatically. A full reboot has not yet been performed in A34. If the
owner still sees a static wallpaper after a cold boot, the next discriminating
step is to compare `nuxel-wl-fb.state` `FRAMES_OK` progression with the first
`NUXEL_HOME_READY` timestamp and the handoff receipt, not to inject a synthetic
Power key.

## Verdict

**CURRENT STATE: RENDERING AND INPUT ARE ALIVE.** The freeze was an app-surface
UX state, not a stalled bridge. Cold-boot persistence remains to be tested.
