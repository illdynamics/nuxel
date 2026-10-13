# g7power/stock-evidence/ — evidence pulled from the physical Moto G7 Power

Collected **2026-10-12** from the handset while it was still booting **stock
Android 10** (`QPO30.52-5`, `motorola/ocean_retail/ocean`, XT1955-4, slot `_b`),
reachable over **network adb** (`adb connect 10.20.30.15:5555`) because the USB
data link was not working.

This is raw, unedited, unrooted-adb output. It is the ground truth that drove the
2026-10-12 corrections (touch driver, A/B layout). `dmesg`, `/proc/cmdline`,
`/proc/bus/input/devices`, `/vendor/firmware*` and `dd /dev/block/*` are
**root-only** on this ROM — the files that record those denials are part of the
evidence.

| File | What it proves |
|---|---|
| `getprop.txt`, `boot-props.txt`, `lock-props.txt`, `cmdline.txt` | Device identity (`ocean`, `moto g(7) power`, XT1955-4, serial `ZY326RGXCM`), build fingerprint, slot `_b`, `verifiedbootstate=green`, `veritymode=enforcing`, `bl_state=2`, `sys.oem_unlock_allowed=1`. `/proc/cmdline` and `dmesg` are `Permission denied`. |
| `i2c-devices.txt`, `i2c-0041-detail.txt` | Touch I²C client exists at **`3-0041`** on `78b7000.i2c` (i2c-3) — matches the mainline DTS. `3-0041`'s `driver` link resolves to **`ILITEK_TDDI`** (vendor driver). Also `3-0038` → `focaltech_ts`, `5-0036` (LM3697 backlight). |
| `interrupts.txt` | IRQ 286 = **`msmgpio 65 Edge`**, owner string **`ilitek`** — matches DTS `interrupts = <65 IRQ_TYPE_EDGE_FALLING>`. |
| `getevent-pl.txt`, `dev-input.txt`, `input-names.txt`, `input-props.txt` | Touch input node `/dev/input/event1`, name **`tchip`**, `INPUT_PROP_DIRECT`, ABS_MT X 0..719 / Y 0..1519, slots 0..9 → the 720×1520 panel with 10 contacts. |
| `by-name.txt`, `partitions.txt` | **A/B device**: `boot_a/boot_b`, `dtbo_a/dtbo_b`, `system_a/b`, `vendor_a/b`, `vbmeta_a/b`, shared `userdata`. `/proc/partitions` is unreadable. |
| `vendor-modules-list.txt` | `/vendor/lib/modules` is not readable for the `shell` user (unrooted) — vendor modules/blobs need root or a stock package. |
| `dumpsys-usb.txt`, `dumpsys-battery.txt` | Port negotiates **DFP/host** (`current_mode=dfp`, `data_role=host`, `power_role=source`) but `device_manager.connected=false` and `USB powered: false` → the phone never presents as a USB peripheral and does not charge. |
| `firmware-sysfs.txt` | `/sys/firmware/devicetree` is present but root-only → cannot read the live DT without root. |

## Why it matters

* The **touch hardware is exactly what the mainline ocean DTS describes** (i2c_3
  @ 0x41, gpio 65 edge). The "no touch" blocker was a Nuxel Kconfig typo, not
  hardware — see `nuxel-g7power-touchscreen.md` and `g7power-go-guide.md` §1.7.
* Stock binds touch with the **vendor `ILITEK_TDDI`** driver, so mainline
  `ili210x` binding is expected-but-unproven until the first Nuxel boot.
* The device is **A/B** (the repo previously documented "A-only").
* Stock `boot`/`dtbo` and the vendor blobs **cannot** be backed up with
  unrooted adb — they need an unlocked bootloader plus a booted TWRP
  (`fastboot boot twrp-ocean.img`) or a stock firmware package.
