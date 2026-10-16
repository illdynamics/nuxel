# 06 — POWER BUTTON (short press = screen off/on)

**Status: implemented, deployed, verified live through the console (`nuxelctl display
off|on`).  Physical short-press confirmation by the user is pending (see 11).**

## 1. What was measured first (mission 10)

`nuxel-button-manager --probe` walks `/proc/bus/input/devices` and every
`/dev/input/event*` with the real ioctls (`EVIOCGNAME`, `EVIOCGID`, `EVIOCGPROP`,
`EVIOCGBIT(EV_KEY)`, `EVIOCGBIT(EV_ABS)`, `EVIOCGABS`):

```
/dev/input/event1 name=gpio_keys bus=0019 vid=0001 pid=0001
    EVIOCGBIT(EV_KEY) rc=96 keys: 114 115 116 703
```

So POWER = **116**, VOLUMEDOWN = 114, VOLUMEUP = 115, assistant/Bixby = **703**.
Nothing else in this image owns those keys (no logind session, phoc treats them as an
ordinary keyboard and takes no action), so a single manager is the single handler.

## 2. Design — one framebuffer owner is preserved

The display bridge (`nuxel-wl-fb`) is the only `/dev/fb0` owner, so the button manager
never touches the framebuffer.  It writes to the bridge’s control FIFO
`/run/nuxel-wl-fb.cmd`:

```
screen-off|screen-on|screen-toggle|status
```

and the bridge (A32) implements it as:

* `screen-off` — stop presenting frames, save the current brightness, write **0** to
  `/sys/class/backlight/panel/brightness`.  The DECON/DSIM configuration is left
  untouched, so no `decon_release` is triggered, `/dev/fb0` is **not** closed, no
  re-initialisation is needed, and Fedora, the launcher and the USB console all survive.
* `screen-on` — restore the saved brightness, re-assert the panel, resume presenting.
* State is published in `/var/lib/nuxel/display` for the Settings app and the console.

## 3. Live evidence

```
$ nuxelctl display off ; cat /var/lib/nuxel/display
DISPLAY_OFF
brightness=0
saved_brightness=12800
max_brightness=48600
owner=nuxel-wl-fb
$ nuxelctl display on ; cat /var/lib/nuxel/display
DISPLAY_ON
brightness=12800
saved_brightness=12800
max_brightness=48600
owner=nuxel-wl-fb
```

The bridge keeps consuming compositor frames while off (the client stays live) but
writes nothing to scanout — mission 11’s “stop visible frame presentation”.

## 4. Short vs long press

* short (< 2000 ms): configured action, default `screen-toggle`;
* long (≥ 2000 ms): configured action, default `power-menu`, which is
  **logged and refused** — no power menu exists yet, and a long press must never be
  silently interpreted as “shut down”;
* debounce: a press shorter than 30 ms is ignored, autorepeat (`value == 2`) is handled
  separately from the release (`value == 0`), so a held key cannot produce a burst of
  toggles;
* the Samsung hardware combinations (Download/Recovery held at power-on) happen in the
  bootloader before Linux runs and are untouched.

## 5. Blockers, stated honestly

* `FBIOBLANK` was deliberately **not** used: on this driver it is not needed for a
  reversible off/on and it is the path most likely to disturb DECON state.  Brightness 0
  plus no presentation is the supported, recoverable mechanism.
* If the user’s physical short press does not toggle, the remaining suspects are
  (a) the boot-time `sec_key` (Samsung `sec_key_notifier`) consuming KEY_POWER, and
  (b) an autorepeat/`value==2` sequence difference; both are diagnosable with
  `nuxel-button-manager --capture 20` and the manager’s own `/var/lib/nuxel/buttons` log.
