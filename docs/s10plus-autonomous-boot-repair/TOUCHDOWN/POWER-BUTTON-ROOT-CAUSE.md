# POWER BUTTON ROOT CAUSE — A34

## Evidence from the previous boot (journal, 11:51 local)

```
11:51:23..25  FSM_ACTION source=key action=screen-toggle   (7 toggles in ~3 s)
11:51:28      MENU_OPEN index=0 id=lock-screen
11:51:31      MENU_CLOSE reason=menu-close
11:51:36      FSM_ACTION source=tick action=open-terminal
11:51:37      FSM_ACTION source=tick action=open-terminal
```

Two independent defects are visible:

1. **Duplicate screen toggles.** The previous button-manager revision emitted a
   Power short action on every release without a robust single/double
   arbitration in the owner's rapid sequence. The a34 FSM defers the short
   action for `POWER_DOUBLE_GAP_MS` and clears the deferral once; this is now
   deployed (`/usr/lib/nuxel/nuxel-button-manager` SHA-256
   `21a695181592b30e38c657727638a4532368deff12a69dae3926bc0fa7728fb0`).
2. **Spurious touch `back`.** At 12:13:01Z the button manager dispatched
   `FSM_ACTION source=touch action=back` during a centre tap. Cause: the a33
   touch translator emitted `TOUCH_DOWN` on `ABS_MT_TRACKING_ID` before the
   position axes in the same frame, so the FSM saw `(0,0)` (an edge). A34
   translates on `SYN_REPORT` only, after `POSITION_X/Y`; this is deployed.
3. **Terminal on a timer tick.** `open-terminal` came from a deferred **Bixby**
   short press (`bixby_short=open-terminal`, `defer_bixby_short_for_double=1`),
   not from the Power mapping. A Bixby press that is still in its 400 ms
   double-press deferral when a Power event arrives can surface later as
   `source=tick action=open-terminal`. The current config still maps
   `bixby_short=open-terminal`. A Power-only press sequence has **not** yet
   been captured to prove whether a phantom Bixby event is present. Regardless,
   A34 now cancels a pending deferred Bixby short on any Power press (while Bixby
   is not held), so a deferred `open-terminal` can no longer surface after Power
   activity. The deterministic test `tests/test-fsm-power-bixby.sh` passes:
   A33 emitted `screen-toggle` + `open-terminal`; A34 emits only
   `screen-toggle`.

## Current mapping (`/etc/nuxel/input/buttons.json`)

```
power_short  = screen-toggle
power_long   = power-menu
power_double = camera          (pwa-host currently refuses `camera`; harmless)
bixby_short  = open-terminal
```

`power_double=camera` does **not** open Terminal. `HOST_ACTION_REFUSED camera`
is the only effect; it does not restart Phoc, WebKit or the launcher.

## Display fix already deployed

`nuxel-wl-fb` A34 now writes `bl_power=4` (FB_BLANK_POWERDOWN) on screen-off and
`bl_power=0` + the saved brightness + `FBIOBLANK(UNBLANK)` on screen-on. Measured:

```
OFF: brightness=0 actual_brightness=2 bl_power=4
ON:  brightness=12800 actual_brightness=183 bl_power=0
```

A single FIFO screen-off/screen-on cycle restored the panel; no second press
was needed. The owner's physical Power test is still required to prove the
button path (tests C/D).

## Verdict

**FIXED IN SOFTWARE / OWNER TEST PENDING.** The touch-`back`, duplicate-toggle
and deferred-Bixby-to-Terminal mechanisms are all addressed in A34. Physical
Power acceptance (Test C) is still required.
