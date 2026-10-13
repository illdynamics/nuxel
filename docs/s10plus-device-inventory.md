# S10+ Device Inventory Template (Phase 0)

Fill this file via a TWRP adb session on the physical device BEFORE running
any S10+ build or flash script.

- Target: Samsung Galaxy S10+ (SM-G975F, Exynos 9820), codename `beyond2lte`
- Device is already in TWRP; adb is available (`adb devices` must list it)
- Everything below is a copy of the Phase 0 collection procedure; every
  `UNKNOWN` / `PLACEHOLDER` value below MUST be replaced with the value read
  from YOUR physical device. Do not copy values from another unit, another
  device model, or any web page — fabricated values will be rejected by the
  inventory gate and may brick the device.

The following four fields gate every S10+ build/flash operation
(`_check_s10plus_inventory()` in each S10+ script):
`KERNEL_ADDR`, `RAMDISK_ADDR`, `TAGS_ADDR`, `WIFI_FW_FILENAME`.
While any of them is still `PLACEHOLDER`/`UNKNOWN`, the scripts refuse to run
with exit code 1 and print the Phase 0 instructions below.

---

## Phase 0 Collection Commands

Run these from the host with the S10+ connected in TWRP (USB debugging on).

```sh
# Verify device identity
adb shell getprop ro.product.device    # must be: beyond2lte
adb shell getprop ro.product.name      # e.g.: beyond2ltexx
adb shell getprop ro.product.model     # e.g.: SM-G975F

# SoC / hardware identity
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|exynos'
adb shell cat /proc/cmdline
adb shell cat /proc/cpuinfo | head -30

# Full dmesg (critical for driver discovery)
adb shell dmesg > s10plus-dmesg-$(date +%Y%m%d-%H%M%S).txt

# Input / touch identification
adb shell getevent -pl 2>/dev/null > s10plus-input-devices.txt

# Partition table
adb shell ls -la /dev/block/platform/13d60000.ufs/by-name/
adb shell cat /proc/partitions

# Vendor firmware file listing (critical for firmware/s10plus/manifest.yml)
adb shell ls -laR /vendor/firmware/ > s10plus-vendor-firmware.txt
adb shell ls -laR /vendor/lib/modules/ > s10plus-vendor-modules.txt
adb shell ls -laR /vendor/etc/firmware/ > s10plus-vendor-etc-firmware.txt

# Audio card discovery
adb shell cat /proc/asound/cards
adb shell ls /sys/class/sound/

# WiFi firmware filenames (critical — filename varies by subvariant)
adb shell ls /vendor/firmware/bcm4375*
adb shell ls /vendor/firmware/BCM4375*
adb shell ls /vendor/firmware/brcm*

# Kernel boot addresses (extract from stock boot.img)
adb pull /dev/block/platform/13d60000.ufs/by-name/boot /tmp/stock-boot.img
# Then: python3 tools/read-boot-header-v1.py /tmp/stock-boot.img
```

Notes:

- `ro.product.device` MUST be `beyond2lte` and `ro.product.name` MUST be
  `beyond2ltexx` (or the operator's regional variant such as `beyond2lteeea`
  / `beyond2lte0`). Every flash script refuses on mismatch.
- `/proc/cmdline`, the full dmesg and the `getevent -pl` dumps go into the
  bring-up notes; they drive the driver-status matrix in
  `docs/s10plus-bringup.md`.
- The stock boot.img pull only touches the `boot` partition, which is NOT on
  the protected list. NEVER pull or flash: `efs`, `efsg`, `persist`, `param`,
  `up_param`, `steady`, `keystorage`, `carrier`, `cp_debug`, `misc`.
- Do not run the UFS by-name listing commands on a device that is NOT an
  S10+; the UFS path is Exynos-9820-specific.

### Reading the stock boot.img header

```sh
python3 tools/read-boot-header-v1.py /tmp/stock-boot.img
```

prints `kernel_addr`, `ramdisk_addr`, `tags_addr`, `page_size` (must be
2048), `kernel_size`, `ramdisk_size`, `dt_size`, `os_version`, `name` and the
full `cmdline`. Copy the three load addresses into the fields below and into
`boot/s10plus/boot-config.txt`. The same parser backs
`boot/s10plus/pack-boot-v1.sh --addresses-from-device`.

---

## Fill these fields after collection:

```text
DEVICE_VARIANT:     beyond2ltexx (CONFIRM on unit: adb shell getprop ro.product.name)
BOOTLOADER_VERSION: CONFIRM on unit: adb shell getprop ro.bootloader
ANDROID_BUILD:      CONFIRM on unit: adb shell getprop ro.build.id
KERNEL_ADDR:        0x10008000
RAMDISK_ADDR:      0x11000000
TAGS_ADDR:          0x10000100
SENSOR_HUB:         CONFIRM on unit from dmesg / getevent -pl
CAMERA_FRONT:       CONFIRM on unit from dmesg (fimc-is probes)
CAMERA_REAR:        CONFIRM on unit from dmesg (fimc-is probes)
WIFI_FW_FILENAME:   bcmdhd_sta.bin_b1
BT_HCD_FILENAME:    bcm4375B1_semco.hcd
TOUCH_FW_PATH:      embedded in the downstream sec_ts driver (no /vendor/firmware file)
AUDIO_UCM_CARD:     cs47l93 (MADERA; CONFIRM with aplay -l once booted)
```

How to fill each field (replace the value after the colon; keep the field
name unchanged):

| Field | Fill from | Example (this unit only!) |
|---|---|---|
| `DEVICE_VARIANT` | `adb shell getprop ro.product.name` | `beyond2ltexx` |
| `BOOTLOADER_VERSION` | `adb shell getprop ro.bootloader` | value printed by getprop |
| `ANDROID_BUILD` | `adb shell getprop ro.build.id` | value printed by getprop |
| `KERNEL_ADDR` | `python3 tools/read-boot-header-v1.py /tmp/stock-boot.img` → `kernel_addr` | `0x10008000` (verify from your image) |
| `RAMDISK_ADDR` | same → `ramdisk_addr` | `0x11000000` (verify from your image) |
| `TAGS_ADDR` | same → `tags_addr` | `0x10000100` (verify from your image) |
| `SENSOR_HUB` | `dmesg` lines mentioning sensor hub / `getevent -pl` device names | `UNKNOWN` until collected |
| `CAMERA_FRONT` | `dmesg` sensor/ISP probe lines | `UNKNOWN` until collected |
| `CAMERA_REAR` | `dmesg` sensor/ISP probe lines | `UNKNOWN` until collected |
| `WIFI_FW_FILENAME` | `adb shell ls /vendor/firmware/bcmdhd*` | e.g. `bcmdhd_sta.bin_b1` |
| `BT_HCD_FILENAME` | `adb shell ls /vendor/firmware/bcm4375*` | e.g. `bcm4375B1_semco.hcd` |
| `TOUCH_FW_PATH` | embedded in the sec_ts kernel driver | `(none — built into the driver)` |
| `AUDIO_UCM_CARD` | `aplay -l` in TWRP (or the booted Nuxel system) | e.g. `CS47L93` card name |

IMPORTANT:

- The three load addresses and the WiFi firmware filename are read by the
  `_check_s10plus_inventory()` gate. Leave them `PLACEHOLDER`/`UNKNOWN` and
  every S10+ build/flash script exits 1 with the Phase 0 reminder.
- Do not "invent" a plausible value to make the gate pass; the gate exists
  because flashing with wrong load addresses or the wrong firmware filename
  is a brick risk on this device (S-Boot is picky; there is no
  Android-bootloader-mode rescue path — recovery is TWRP + Download Mode).
- After filling, keep this file in the repo: it is the operator record for
  the unit and is consumed by the gate.

---

## Field provenance (auto-prefilled, 2026-10-11)

The four gate fields (`KERNEL_ADDR`, `RAMDISK_ADDR`, `TAGS_ADDR`,
`WIFI_FW_FILENAME`) plus the BT filename below were **pre-filled from
authoritative upstream sources** so the S10+ build/flash scripts are not
dead-locked, exactly as the G7 Power pass did. They are NOT guesses:

- **Load addresses** — postmarketOS `device/testing/device-samsung-beyond1lte/deviceinfo`
  declares `deviceinfo_flash_offset_base=0x10000000`,
  `flash_offset_kernel=0x00008000`, `flash_offset_ramdisk=0x01000000`,
  `flash_offset_tags=0x00000100`, `flash_pagesize=2048`. Hence
  kernel=`0x10008000`, ramdisk=`0x11000000`, tags=`0x10000100`.
  (The old repo placeholders `0x80008000 / 0x84000000 / 0x80000100` were a
  different, WRONG base and must not be used.)
- **WiFi/BT firmware names** — the pmOS `firmware-samsung-beyond1lte` package and
  the vendor blob repo `Linux4/proprietary_vendor_samsung` (Exynos 9820 /
  beyond2lte) ship Samsung's `bcmdhd` WiFi firmware: `bcmdhd_sta.bin_b1`,
  `bcmdhd_mfg.bin_b1`, `bcmdhd_mon.bin_b1`, `bcmdhd_clm.blob` and an
  `nvram.txt_*`; the Bluetooth `.hcd` is `bcm4375B1_semco.hcd`.

**You must still confirm all of these against YOUR unit's stock `boot.img`
header before the first flash** (`python3 tools/read-boot-header-v1.py
/tmp/stock-boot.img`). If your unit differs, replace the values here — the
gate reads these exact fields.
