# A26 — P4: TOUCHSCREEN (boot-mode discrimination + live capture)

## 1. The boot mode is the first thing to establish — and this boot is NORMAL

The A17-era caveat was that `sec_touchscreen` skips initialisation in Samsung
low-power charging mode. Checked on the running A25 boot:

```
$ grep -o 'androidboot.mode=[^ ]*\|lpcharge=[^ ]*\|charging_mode=[^ ]*' /proc/cmdline
charging_mode=0x3030
```

There is **no `androidboot.mode=charger` and no `lpcharge=1`** — only the
charging-mode register value. So this is a **normal (non-LPM) boot**, and the
"no input device exists" conclusion from the A23/A24 charger-mode boots does not
apply. (Confirmed independently by the charger-indicator behaviour:
`max77705_chg_monitor_work: [CHG] MODE(0x5) … otg_on(0)`.)

## 2. The controller enumerated, with multitouch, in this boot

```
N: Name="sec_touchscreen"
S: Sysfs=/devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2
H: Handlers=sec_key_notifier event2
B: PROP=2                      <- INPUT_PROP_DIRECT (a touch surface, not a tablet)
B: EV=2b                       <- EV_SYN | EV_KEY | EV_ABS
B: KEY=4000000000000000 0 0 80 0 420 0 0 8000 0 0
B: ABS=4263800000000003        <- MT axes present
```

Siblings registered on the same I2C device: `sec_touchpad` (event3),
`sec_touchproximity` (event4). `/dev/input/event0 … event10` all exist, mode
`crw-------` (root-only; fine, the console runs as root).

`evtest` is **not installed** on the image, so a raw reader was used instead of
adding a package.

Kernel-side the controller is powered and running — periodic driver telemetry is
present in the log, e.g.
`sec_ts 4-0048: [sec_input] mode:0202 tc:0 noise:0 wet:0 … Cal_flag:Success fail_cnt:0`
and `sec_ts_set_temp temperature:24`.

## 3. Physical-touch capture

A non-destructive raw reader was armed on the touch device for a 900 s window:

```
setsid sh -c "timeout 900 cat /dev/input/event2 > /var/lib/nuxel/touch-raw.bin" &
```

`struct input_event` on this kernel is 24 bytes (`timeval` is 2 x 8 bytes on
arm64), so each event decodes as little-endian
`(sec, usec, u16 type, u16 code, s32 value)`.

**Status at the time of writing: `touch-raw.bin` is 0 bytes — no physical touch
has been recorded yet.** That is an *absence of input*, not an absence of a
device: the node is open, the driver is running, and events will be written the
instant a finger touches the glass.

Deliberately **not** claimed: touch navigation, coordinate scaling, orientation,
tap accuracy, swipe behaviour, ghost touches. Those require the operator's finger
and are listed as the remaining work in §4.

Also deliberately not done: no regulator, power or safety manipulation.

## 4. What remains to close P4

1. Record >=1 tap and >=1 swipe (the capture is already armed).
2. Decode `touch-raw.bin` and derive the real coordinate range from
   `EV_ABS/ABS_MT_POSITION_X/Y` — do **not** assume 0..1440 / 0..3040.
3. Confirm the axis orientation against the UI (the panel is native-portrait
   1440x3040; the controller may report in a rotated frame). The UI already has
   an `orient N` console command and a `TOUCH_ORIENT` variable for exactly this,
   and it derives `INPUT_DEVICE` state at startup — but the running build logged
   `INPUT_DEVICE name='' mt=0 xmax=0 ymax=0` followed by
   `TOUCH_POINTING_DEVICE_NONE`, i.e. **this binary did not find the touch device
   even though it exists**. Root cause candidate: the UI looks up the device by
   name/sysfs at startup and does not retry, and in the A23/A24 charger-mode boots
   there genuinely was none. It needs to enumerate `event2` by capability rather
   than by the empty name string.
4. Feed decoded coordinates into `nuxel-ui`'s existing `tap X Y` FIFO command —
   the hit-testing path is already implemented and proven (`tap` drives
   `hit_test()` → `act_do()`).
5. Keep the console fallback (`tap X Y`, `page=<p>`) as the documented
   alternative until 1–4 are green.
