# configs/g7power/libinput/ — G7 Power touch configuration

Device-keyed libinput configuration for the Motorola Moto G7 Power (ocean,
XT1955, SDM632 / msm8953). Everything under this directory is G7
Power-specific; nothing here applies to any other Nuxel target.

## Touch controller (verified hardware facts)

| Role       | Part                                   | Notes                          |
|------------|----------------------------------------|--------------------------------|
| Controller | **Ilitek ILI2117**                     | mainline `CONFIG_TOUCHSCREEN_ILI210X` |
| Bus        | i2c_3 @ 0x41                           | IRQ tlmm 65                    |
| Mapping    | **inverted-x**                         | Per ocean DTS                   |

## File

* `99-nuxel-ocean-touch.conf.disabled` — X11 InputClass for the ILI2117
  touchscreen (`MatchProduct "ILI210x Touchscreen"`), **disabled** for the
  first bring-up (rename to `99-nuxel-ocean-touch.conf` to enable).

  Why it is disabled: the ocean DTS already declares `touchscreen-inverted-x`
  on `touchscreen@41`, and mainline `ili210x.c` reports coordinates through
  the generic touchscreen-property helpers, so the kernel already applies the
  X inversion. A `TransformationMatrix` here would invert X a **second** time
  (mirrored touch). The old version of this file carried
  `Option "TransformationMatrix" "-1 0 1 0 1 0 0 0 1"` and matched the
  non-existent product name `ILI2117*`, so it never actually ran — do not
  "restore" it.

  Also note this file is consumed exclusively by the **xf86-input-libinput
  X11 driver** from `/etc/X11/xorg.conf.d/`. **libinput under a Wayland
  compositor (Phosh/wlroots — the real G7 Power runtime) does not read
  xorg.conf.d InputClass stanzas.** If the kernel's DT inversion later proves
  insufficient under Phosh, the fix is the `LIBINPUT_CALIBRATION_MATRIX` udev
  property (or a libinput quirk), not this file.

## Verify on device (Phase 0)

* The **inverted-x mapping must be verified on the physical device** and
  adjusted if touch appears mirrored.
* **Some G7 Power units boot without touch at all** — confirm the input
  device enumerates first:
  `evtest /dev/input/event*` or `getevent -pl` (look for the ILI210x event
  node; kernel input name "ILI210x Touchscreen" — verify on device).
* Exact calibration values are UNKNOWN until measured with
  `libinput debug-events` on the real device; the commented-out
  `CalibrationMatrix` line is the placeholder to fill. No values are
  invented.

See phones/g7power/g7power-requirements.md and docs/g7power-device-inventory.md.
