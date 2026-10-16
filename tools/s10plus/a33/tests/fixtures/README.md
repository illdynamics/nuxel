# Synthetic sysfs/uevent fixtures for the libinput-path capability selector

These trees stand in for `/dev/input` + `/sys/class/input` on the S10+ so the
device-selection and hotplug decisions of `tools/s10plus/a33/nuxel-libinput-path.c`
can be exercised **offline**, with no phone, no devboard and no `/dev/input`.

Layout per device (mirrors real sysfs; `absinfo` is the fixture's stand-in for the
`EVIOCGABS` ioctl, because evdev does not expose ABS ranges through sysfs):

```
<fixture>/sys/class/input/eventN/device/name                  # quoted, as sysfs prints it
<fixture>/sys/class/input/eventN/device/properties            # hex bitmap, INPUT_PROP_*
<fixture>/sys/class/input/eventN/device/capabilities/abs      # hex bitmap, ABS_*
<fixture>/sys/class/input/eventN/device/capabilities/key      # hex bitmap, KEY_*
<fixture>/sys/class/input/eventN/device/absinfo               # "<axis> <min> <max> <fuzz> <flat>"
<fixture>/sys/class/input/eventN/uevent                       # what the udev DB entry would carry
```

Bitmap word order in these files is the `/proc/bus/input/devices` convention
**first word = highest bits**, the same convention already used by
`tools/s10plus/a32/tests/input-bitmap-decode.py`. The on-device code path never
reads sysfs for capabilities: it uses `EVIOCGPROP` / `EVIOCGBIT` / `EVIOCGABS`
/ `EVIOCGNAME` on the node itself.

The fixture values are the **real measured lines** for this handset:

* `event2` = `sec_touchscreen` — `PROP=2` (`INPUT_PROP_DIRECT`),
  `ABS=4263800000000003`, `KEY=4000000000000000 0 0 80 0 420 0 0 8000 0 0`
  (A26 acceptance record: `sec_ts` on i2c `4-0048`, node
  `/devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2`).
* `event0` = `gpio_keys` — the real KEY bitmap with VOLUMEDOWN/VOLUMEUP/POWER/
  Bixby (114/115/116/703), `PROP=0` (no `INPUT_PROP_DIRECT`).

`eventN` names inside the fixture are the *data under test*; nothing in the
source of the shim or the tracer contains a node number.

| fixture | what it proves |
|---|---|
| `empty/` | no panel at all (charger-mode boot) -> `ZERO_DEVICES`, exit 0, no crash |
| `sec-ts-only/` | `gpio_keys` rejected with a reason, `sec_touchscreen` accepted |
| `numeric-order/` | numeric sort: event2 before event10 (never lexical) |
| `degenerate-range/` | `INPUT_PROP_DIRECT` + ABS_MT but a degenerate range -> rejected |
| `hotplug/` | add / remove / re-add bookkeeping of the tracked device table |
