# OWNER PHYSICAL ACCEPTANCE — A34

The phone is currently on Home (A34 status bar 0.4.3-a34, A34 display bridge).
Please perform these short tests with a real finger. Do not use a stylus.

## Test A — raw / mapping

Tap the **top-left**, **centre**, and **bottom-right** of the screen, then make
one slow swipe from the middle-left to the middle-right.

Expected: the launcher's `/run/nuxel-home.state` records pointerdown/touchstart
at each location and the swipe produces touchmove records. `nuxel-touch-arm`
writes additional `TOUCH_POINT` records; IRQ 431 increases.

## Test B — the real acceptance (T9)

1. Tap the **Settings** icon (gear) on Home.
2. Wait 3 seconds. The Settings PWA should cover the screen.
3. Tap the small **✕** at the **top right** to return Home.
4. Tap **Settings** again, then **swipe up from the bottom edge** to return Home
   (the existing home gesture; it now closes the app frame).
5. Tap **Terminal** and wait 3 seconds.
6. Report exactly what appeared on the glass after each tap.

Expected: each tap opens the correct app; `✕` and the bottom swipe-up both
return Home. This is the test that decides T9. A screenshot will be taken after
your report.

## Test B2 — notification pull-down

From Home, place a finger on the **top status bar** and drag **down** at least
24 CSS px. The Quick Settings panel should open. This is the gesture that was
missing before A34 (the handler existed, nothing dispatched it).

## Test C — Power

1. Press **Power once**, wait 3 seconds. The AMOLED should go fully dark
   (`bl_power=4`). Do not press again.
2. Press **Power once**, wait 3 seconds. Home should return in one press.

Report if the first press only dims the screen, or if the second press opens
anything (Terminal, camera, app switcher).

## Test D — long-press Power menu

1. Hold **Power** for about 2.5 seconds and release.
2. Use **Volume Up/Down** to move; short-press **Power** to confirm.
3. Choose **Cancel** first. Then test **Restart** only if you want a reboot.

Report whether the menu is visible at all. Recovery / Download Mode must refuse
and must not leave Linux.

## Test E — USB mouse / keyboard (optional, console-safe)

1. Unplug the Fedora USB-C cable.
2. Plug the mouse + A-to-C adapter for ~20 seconds; unplug it.
3. Plug the Keychron in **wired** mode for ~20 seconds; unplug it.
4. Reconnect the Fedora cable.

The console will re-enumerate automatically. dmesg will then show whether the
phone attempted host mode. Do not change any role by hand.

## What counts as success

Only your physical confirmation of Test B (and normal swipe/typing) is T9.
A screenshot, an IRQ count, or a synthetic event is not a substitute.
