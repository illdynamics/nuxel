# TOUCHSCREEN EVDEV EVIDENCE — A34

## Device identity (capability-selected, not eventN-assumed)

```
event1  gpio_keys        EV_KEY  KEY_POWER, KEY_VOLUMEUP, KEY_VOLUMEDOWN, KEY_703 (Bixby)
event2  sec_touchscreen  PROP=DIRECT  ABS_MT_POSITION_X/Y  ABS_MT_SLOT  BTN_TOUCH
event3  sec_touchpad     PROP=... (secondary)
event4  sec_touchproximity
```

`event2`:

* `EVIOCGID`: bus `0x0018` (I2C), vendor `0x0000`, product `0x0000`
* `EVIOCGABS(ABS_MT_SLOT)` = `(0,9)` → 10 contact slots
* `EVIOCGABS(ABS_MT_POSITION_X)` = `(0,4095)`
* `EVIOCGABS(ABS_MT_POSITION_Y)` = `(0,4095)`
* `EVIOCGBIT(EV_ABS)` includes `ABS_MT_TRACKING_ID`
* `BTN_TOUCH` is supported
* node mode `0600 root:root` (phoc runs as root)

## Real physical tap

The correlated tap at `10:13:01Z` produced:

* `sec_ts` IRQ increment,
* `nuxel-touch-arm` `TOUCH_POINT slot=0 n=1..4`,
* WebKit `pointerdown`/`touchstart` at CSS `(155,235)`,
* `app:launch id=org.nuxel.Mail`.

A screenshot taken after the tap (`evidence/a34/mail-open-physical-tap-1213.png`)
shows the Mail PWA, not the launcher: top bar `#0d1f3c` and body `#0a1628`,
92.6% of the glass a single body colour, with a dark circular `✕` at the top
right (the launcher's close button). The action therefore caused a visible
application change without a Power press.

A **second** independent physical tap at `10:23:39Z` (12:23:39 local) hit
`SPAN#app-icon` at CSS `(37,155)` and produced `app:launch id=org.nuxel.Calendar`.
The screenshot `evidence/a34/calendar-open-physical-tap-1223.png` shows the
Calendar PWA (top bar `#0d1f3c`, Calendar accent `#E91E63`), again with no Power
press. The owner also tapped the status bar at `(26,31)` at `10:23:11Z`
(pointerdown/touchstart/touchmove/pointerup/click); that was a tap, not a
vertical pull, so it correctly did not open Quick Settings.

## Not used as proof

`nuxel-uinput-touch-probe.py` creates a virtual uinput device. On this boot it
did **not** reach the compositor (the libinput path shim's hotplug watcher did
not add the short-lived virtual node; no `PATH_ADD` was logged). Synthetic input
is explicitly excluded from T8/T9.

## Verdict

T3 **PASS** (real finger), T8 **PASS for the Mail tap**; T9 pending owner
confirmation of normal use.
