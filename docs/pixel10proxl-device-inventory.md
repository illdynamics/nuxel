# Google Pixel 10 Pro XL Device Inventory (Phase 0)

**Device:** Google Pixel 10 Pro XL · **codename/key:** `mustang` · **dir:** `google-pixel-10-pro-xl`
**Reviewed serial:** `58211FDCQ001LA` · **HW:** `MP1.0` · **SKU:** `G45RY`
**SoC:** Google Tensor G5 (`gs501`) · **Boot:** Google ABL + AVB 2.0 + Titan M3 · **Flash:** `fastboot`/`fastbootd`

Fill this in from YOUR unit in stock Android **before** any unlock, build, or
flash. Every `UNKNOWN` / `PLACEHOLDER` below must be replaced with a value read
from the physical device. Never copy values from another unit, another Pixel
model (especially Pixel 7 `panther`), or the sibling `s10plus`/`g7power`
targets — fabricated values keep the gate failing and can brick the device.

The **hard gates** that must be resolved before a physical flash are:

| Gate | Source field | Blocks |
|---|---|---|
| 1. Active slot + both slots' integrity | `SLOT_SUFFIX`, `fastboot getvar current-slot` | all flashing (wrong-slot risk) |
| 2. Build string / bootloader revision match | `BUILD_ID`, `BUILD_FINGERPRINT`, `RO_BOOTLOADER` | stock recovery (`flash-all.sh`) |
| 3. OEM unlocking allowed (not carrier-locked) | `OEM_UNLOCK_ALLOWED`, `RO_OEM_UNLOCK_SUPPORTED` | `fastboot flashing unlock` |
| 4. Real vendor blob filenames (lockdown: no placeholders) | `VENDOR_FW_LISTING`, `MODEM_FW_LISTING` | `firmware/…/manifest.yml` checksums |
| 5. Private vendor kernel tree obtainable | `VENDOR_TREE_ACCESS` | `kernel/…/build-kernel.sh --vendor` |

Until gates 1–5 are filled and the factory image is SHA-256 verified, the
Nuxel scripts intentionally refuse to flash (see `boot/google-pixel-10-pro-xl/flash.sh`
`check_device` + pre-flight, and `firmware/google-pixel-10-pro-xl/verify-firmware.sh --strict`).

---

## Phase 0 — Collection commands

Run from the host with the phone booted into **stock Android** and USB debugging
enabled. Keep the output files with the bring-up notes.

```sh
mkdir -p ~/mustang-inventory && cd ~/mustang-inventory

# ── Identity + build ────────────────────────────────────────────────────────
adb devices
adb shell getprop ro.product.name          | tee mustang-identity.txt   # must be: mustang
adb shell getprop ro.product.device        | tee -a mustang-identity.txt
adb shell getprop ro.product.model         | tee -a mustang-identity.txt
adb shell getprop ro.build.id              | tee -a mustang-identity.txt   # e.g. BP1A.250405.001
adb shell getprop ro.build.fingerprint     | tee -a mustang-identity.txt
adb shell getprop ro.build.version.release | tee -a mustang-identity.txt
adb shell getprop ro.boot.hardware         | tee -a mustang-identity.txt   # gs501 family
adb shell getprop ro.boot.slot_suffix      | tee -a mustang-identity.txt
adb shell getprop ro.boot.verifiedbootstate| tee -a mustang-identity.txt
adb shell getprop ro.bootloader            | tee -a mustang-identity.txt   # bootloader revision
adb shell cat /proc/cmdline                | tee -a mustang-identity.txt

# ── Unlock eligibility ──────────────────────────────────────────────────────
adb shell getprop ro.oem_unlock_supported  # 1 = unlocking supported
adb shell settings get global oem_unlock_allowed   # 1 = can unlock (0 = carrier-locked/restricted)
# Also check on-device: Settings → About phone → SIM status (must NOT say "Network locked")

# ── Vendor firmware + modules (feeds firmware/google-pixel-10-pro-xl/manifest.yml) ──
adb shell ls -laR /vendor/firmware/            > mustang-vendor-firmware.txt
adb shell ls -laR /vendor/firmware_mnt/image/ >> mustang-vendor-firmware.txt
adb shell ls -laR /vendor/lib/modules/         > mustang-vendor-modules.txt
adb shell ls -laR /vendor/etc/firmware/        > mustang-vendor-etc-fw.txt
# Modem (Exynos 5500) firmware lives in the modem partition; may need root/`adb root`:
adb shell ls -la /vendor/firmware/modem*   2>/dev/null >> mustang-vendor-firmware.txt
adb shell ls -la /vendor/firmware/*exynos* 2>/dev/null >> mustang-vendor-firmware.txt

# ── Hardware IDs for the driver matrix ──────────────────────────────────────
adb shell dmesg > mustang-dmesg.txt          # touch/panel/WiFi/BT/audio/modem IDs
adb shell getevent -pl 2>/dev/null > mustang-input-devices.txt   # confirms S6SY791
adb shell cat /proc/asound/cards 2>/dev/null > mustang-asound.txt
```

```sh
# ── Bootloader view (do this while already unlocked or before flashing) ─────
adb reboot bootloader
fastboot getvar product          # MUST be: mustang
fastboot getvar serial           # MUST be: 58211FDCQ001LA (your unit)
fastboot getvar unlocked         # yes/no
fastboot getvar secure           # yes (Titan M3 active — expected)
fastboot getvar current-slot     # a or b
fastboot getvar slot-count
fastboot getvar all              | tee mustang-fastboot-getvar-all.txt
fastboot reboot
```

---

## Fill these after collection

```
BUILD_ID                = UNKNOWN   # adb shell getprop ro.build.id (e.g. BP1A.250405.001)
BUILD_FINGERPRINT       = UNKNOWN   # adb shell getprop ro.build.fingerprint
RO_BOOTLOADER           = UNKNOWN   # adb shell getprop ro.bootloader (bootloader revision)
RO_BOOT_HARDWARE        = UNKNOWN   # adb shell getprop ro.boot.hardware (expect gs501 family)
SLOT_SUFFIX             = UNKNOWN   # adb shell getprop ro.boot.slot_suffix (e.g. _a)
CURRENT_SLOT            = UNKNOWN   # fastboot getvar current-slot
OEM_UNLOCK_SUPPORTED    = UNKNOWN   # adb shell getprop ro.oem_unlock_supported (1/0)
OEM_UNLOCK_ALLOWED      = UNKNOWN   # adb shell settings get global oem_unlock_allowed (1/0)
CARRIER_LOCKED          = UNKNOWN   # yes/no (Settings → About phone → SIM status)
UNLOCKED                = UNKNOWN   # fastboot getvar unlocked (yes/no)
```

```
# Firmware blob filenames exactly as found on the device (replace the
# manifest placeholders with these; then hashes are computed by
# install-firmware.sh --checksums against the factory image).
WIFI_FW_FILENAMES       = UNKNOWN   # from mustang-vendor-firmware.txt (brcmfmac4390*.bin/.nvm/.clm_blob)
BT_FW_FILENAMES         = UNKNOWN   # BCM4390.hcd path
GPU_FW_FILENAMES        = UNKNOWN   # pvr_*.fw / pvr_drv.so (PowerVR DXT)
DISPLAY_FW_FILENAMES    = UNKNOWN   # amb655x_fw.bin / amb655x_gamma.bin
TOUCH_FW_FILENAMES      = UNKNOWN   # s6sy791_touch_fw.bin
AUDIO_FW_FILENAMES      = UNKNOWN   # cs35l45_*.bin / cs42l43_fw.bin
SENSOR_FW_FILENAMES     = UNKNOWN   # bmi270 / lsm6dsv / tcs3710
NFC_FW_FILENAMES        = UNKNOWN   # sn220_fw.bin
FINGERPRINT_FW_FILENAMES= UNKNOWN   # gf3636_fw.bin
PMIC_CHARGER_FW_FILENAMES = UNKNOWN # max77729/max77826/bq2597x/max1720x
MODEM_FW_FILENAMES      = UNKNOWN   # modem.bin / modem_pr.bin / modem_cal.bin / exynos5500_shm.bin
```

```
# Upstream dependencies
FACTORY_IMAGE_ZIP       = UNKNOWN   # mustang-bp1a.250405.001-factory-<xxxxx>.zip (Google images page)
FACTORY_IMAGE_SHA256    = UNKNOWN   # published checksum; verify with shasum -a 256 BEFORE flashing
VENDOR_TREE_ACCESS      = UNKNOWN   # yes/no: is android-gs-mustang-6.12 obtainable (signed prebuilt or source)?
POWERVR_USERS_MODE      = UNKNOWN   # pvr_drv.so + Mesa/PowerVR branch, or llvmpipe fallback (Phase 6)
SUPER_RESIZE_NEEDED     = UNKNOWN   # does the full Nuxel system.img need super repartitioning?
TITAN_M3_KEYMASTER_NEEDED = UNKNOWN # AVB-only is the default; is Keymaster/StrongBox required?
```

### Load addresses (already sourced — confirm from the stock boot.img)

Mustang uses **boot header v4 / page_size 4096** (already in
`boot/google-pixel-10-pro-xl/boot-config.txt` and `boot/boot.img/mustang-boot-config.txt`):

```
base_address   = 0x10000000
kernel_offset  = 0x00008000   -> kernel_addr  = 0x10008000
ramdisk_offset = 0x01000000   -> ramdisk_addr = 0x11000000
tags_offset    = 0x00000100   -> tags_addr    = 0x10000100
```

Unlike the siblings, mustang's `boot.img` is header v4 and is NOT packed with the
v1 packer: it needs the v4 boot header + `vendor_boot` + mandatory `init_boot`.

---

## Safety rules (read once, internalize)

1. **`fastboot flashing unlock` / `unlock_critical` WIPE the device.** Back up first.
2. **Verify identity before every flash:** `fastboot getvar product` == `mustang`
   (and the expected serial). Nuxel's `flash.sh` refuses on mismatch.
3. **Keep the factory image + its SHA-256.** That zip's `flash-all.sh` is the
   only canonical restore path.
4. **Never relock** (`fastboot flashing lock` / `--relock-custom-key`) until Nuxel
   boots in development mode and the Nuxel AVB key is enrolled.
5. **A/B slots:** never mix slot artifacts; confirm `current-slot`.
6. **`persist` / `metadata`:** do not erase outside an explicit clean install.
