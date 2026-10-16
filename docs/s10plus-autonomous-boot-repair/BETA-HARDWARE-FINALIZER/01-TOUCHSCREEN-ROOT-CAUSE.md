# 01 — TOUCHSCREEN ROOT CAUSE

**Status: root cause identified, fixed by a normal (non-charger-mode) boot, verified on
hardware up to the compositor.  Physical finger confirmation is pending (see 11).**

## The finding

The touchscreen did not “partially work”: **no touch input device existed at all**.

```
$ cat /proc/bus/input/devices | grep -i touch      # BEFORE
(no result)
$ dmesg | grep sec_ts
[    1.674224] [sec_input] sec_ts_init: Do not load driver due to : lpm 1
[    2.257441] tsp_io: disabling
[    2.257552] tsp_avdd: disabling
$ dmesg | grep -i is_lpm_check
[    0.000000] sec_bat_is_lpm_check: Low power charging mode: 1
```

`drivers/input/touchscreen/sec_ts/y771/sec_ts.c` returns `-ENODEV` from its initcall
before `i2c_add_driver()` when the boot-time flag `lpcharge` is 1, and
`drivers/samsung/misc/sec_batt.c` sets that flag from the kernel command line:

```c
static int sec_bat_is_lpm_check(char *str) {
        if (strncmp(str, "charger", 7) == 0) lpcharge = 1;
        pr_info("%s: Low power charging mode: %d\n", __func__, lpcharge);
        return lpcharge;
}
__setup("androidboot.mode=", sec_bat_is_lpm_check);
```

The handset was booted by the bootloader in **charger (LPM) mode** —
`androidboot.mode=charger` was present in `/proc/cmdline`, exactly as recorded in
`DEVICE-OBSERVATIONS.md` for A16/A29b.  That single boot flag explains the whole
-ENODEV, because the same gate exists in the fingerprint (`qbt2000`) and Wacom drivers.

## Why no userspace patch could have fixed it

* `CONFIG_KEXEC is not set` → the kernel cannot be re-entered with a new cmdline.
* `CONFIG_TOUCHSCREEN_SEC_TS_Y771=y` and `/lib/modules/4.14.253` does not exist →
  nothing can be re-loaded; the initcall had already returned.
* `sec_ts_start_device()`’s “already POWER_ON” short-circuit was therefore never
  reached: the driver had no device and no IRQ to arm.  (This is why the A29b
  `nuxel-touch-arm` helper, which drives stop→start through sysfs, exits 2 in this
  state: `/sys/class/sec/tsp/` does not exist because the driver was never added.)

## The fix

A **normal** boot (reboot with the cable attached, i.e. an explicit `reboot` rather
than an LPM auto-boot on charger insertion).  After `systemctl reboot`:

```
$ tr ' ' '\n' < /proc/cmdline | grep androidboot.mode      # androidboot.mode is GONE
$ dmesg | grep sec_ts
[    1.633010] [sec_input] sec_ts_init
[    1.654761] input: sec_touchscreen as /devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2
[    5.962929] sec_ts 4-0048: [sec_input] ic_status_show: ... lpm:0, ... no_charger:0, wired_charger:1
$ grep -A5 sec_touchscreen /proc/bus/input/devices
N: Name="sec_touchscreen"
H: Handlers=sec_key_notifier event2
B: PROP=2                      <-- INPUT_PROP_DIRECT, i.e. a real direct touchscreen
```

`nuxel-touch-arm.service`, which had been failing (exit 2) in charger mode, now
reports **active** without any change to the helper.

## Consequences recorded for the future

1. **A charger-mode boot is not a testable state.**  Any report about touch/input from
   an `androidboot.mode=charger` boot measures nothing.  The console command
   `tr ' ' '\n' < /proc/cmdline | grep androidboot.mode` is the one-line check.
2. The bootloader chooses LPM when the device powers up from off with the charger
   present; an explicit reboot (or a power-key boot) does not.  No BOOT partition
   change is needed, and none was made.
3. Do **not** “fix” this in userspace by poking regulators or by blanking the panel:
   the driver is simply absent until the next non-LPM boot.
