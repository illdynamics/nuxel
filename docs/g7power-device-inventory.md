# G7 Power Device Inventory Template (Phase 0)
# Fill via ADB session on the physical device BEFORE running any build

- Target: Motorola Moto G7 Power (XT1955), codename `ocean`
- SoC: Qualcomm Snapdragon 632 (SDM632, msm8953 DT family), 4x Kryo 250 Gold
  (A73) + 4x Kryo 250 Silver (A53) @ 1.8 GHz, 14 nm
- Storage: eMMC (32/64 GB), **A/B** (`boot_a/boot_b`, `dtbo_a/dtbo_b`, `system_a/b`, `vendor_a/b`, `vbmeta_a/b`, shared `userdata`; reference unit slot `_b`) — partitions live under
  `/dev/block/bootdevice/by-name/`
- Every `UNKNOWN` / `PLACEHOLDER` value below MUST be replaced with the value
  read from YOUR physical device. Do NOT copy values from another unit, from
  a web page, or from another device model — fabricated values will keep the
  inventory gate failing and may brick the device if they ever get used.

The following four fields gate every G7 Power build/flash operation
(`_check_g7power_inventory()` in `firmware/g7power/install-firmware.sh`,
`kernel/g7power/build-kernel.sh`, `boot/g7power/flash.sh` and
`images/g7power/build.sh`):

- `KERNEL_ADDR`
- `RAMDISK_ADDR`
- `TAGS_ADDR`
- `WIFI_FW_FILENAMES`

While any of them is still `PLACEHOLDER` / `UNKNOWN`, the scripts refuse to
run with exit code 1 and print the Phase 0 instructions from this file.

---

## Phase 0 Collection Commands

Run these from the host with the device booted into stock Android (USB
debugging enabled) or into a stock recovery with `adb` available. All files
are collected on the host and kept with the bring-up notes.

```sh
# Verify device identity
adb shell getprop ro.product.device    # must be: ocean
adb shell getprop ro.product.name      # e.g.: ocean
adb shell getprop ro.product.model     # e.g.: XT1955-2
adb shell getprop ro.hardware          # e.g.: qcom
adb shell getprop ro.bootloader        # save bootloader revision

# SoC / hardware identity
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|qcom|msm|sdm'
adb shell cat /proc/cmdline
adb shell cat /proc/cpuinfo | head -30

# Full dmesg (critical — identifies touch, WiFi, BT, audio, camera)
adb shell dmesg > g7power-dmesg.txt

# Input devices (confirms ILI2117, inverted-x)
adb shell getevent -pl 2>/dev/null > g7power-input-devices.txt

# eMMC partition table
adb shell ls -la /dev/block/bootdevice/by-name/ > g7power-partitions.txt
adb shell cat /proc/partitions >> g7power-partitions.txt

# Vendor firmware listing (critical for firmware/g7power/manifest.yml)
adb shell ls -laR /vendor/firmware/        > g7power-vendor-firmware.txt
adb shell ls -laR /vendor/firmware_mnt/    >> g7power-vendor-firmware.txt
adb shell ls -laR /vendor/lib/modules/     > g7power-vendor-modules.txt
adb shell ls -laR /vendor/etc/firmware/    > g7power-vendor-etc-fw.txt

# WiFi firmware filenames (wcn36xx — NOT ath10k or brcm)
adb shell ls /vendor/firmware/WCNSS*      2>/dev/null
adb shell ls /vendor/firmware/wlan/prima/ 2>/dev/null

# BT firmware (hci_qca)
adb shell ls /vendor/firmware/qca/        2>/dev/null

# Audio card discovery
adb shell cat /proc/asound/cards          2>/dev/null
adb shell ls /sys/class/sound/            2>/dev/null

# Camera sensor identification (dmesg is best; also try v4l2-ctl)
grep -iE 'camera|sensor|ov[0-9]|s5k[0-9]|imx[0-9]|cci' g7power-dmesg.txt | head -20

# Fingerprint sensor
adb shell ls /sys/class/fingerprint/      2>/dev/null
grep -i fingerprint g7power-dmesg.txt | head -10

# Boot image load addresses (extract from stock boot.img)
adb shell "dd if=/dev/block/bootdevice/by-name/boot of=/sdcard/stock-boot.img bs=4096"
adb pull /sdcard/stock-boot.img /tmp/stock-boot.img
python3 tools/read-boot-header-v1.py /tmp/stock-boot.img
```

Notes on the collection:

- `ro.product.device` MUST be `ocean`; every G7 flash script refuses on
  mismatch. `ro.product.model` gives the exact retail variant (e.g.
  `XT1955-2`).
- `/proc/cmdline`, the full dmesg and the `getevent -pl` dump drive the
  driver-status matrix in `docs/g7power-bringup.md` and confirm the Ilitek
  ILI2117 touch controller (inverted-x) on THIS unit.
- The vendor firmware listings feed `firmware/g7power/manifest.yml`. The
  WCN3680B WiFi/BT combo uses `wcn36xx` + `hci_qca` firmware — the WCNSS
  files live under `/vendor/firmware/WCNSS*` and
  `/vendor/firmware/wlan/prima/`, NOT ath10k/brcmfmac files.
- The boot image dump ONLY touches the `boot` partition, which is NOT on the
  protected list. NEVER pull or flash `modemst1`, `modemst2`, `fsg`, `fsc`,
  `ddr`, `persist` or `misc` — they hold per-unit IMEI, radio calibration,
  DDR training and other unit-unique data and are irreplaceable.

### Reading the stock boot.img header

```sh
python3 tools/read-boot-header-v1.py /tmp/stock-boot.img
```

prints `kernel_addr`, `ramdisk_addr`, `tags_addr`, `page_size` (must be
2048), `kernel_size`, `ramdisk_size`, `dt_size`, `os_version`, `name` and the
full `cmdline`. Copy the three load addresses into the fields below and into
`boot/g7power/boot-config.txt`. The same parser backs
`boot/g7power/pack-boot-v1.sh --addresses-from-device`.

---

## Fill these after collection:

> **Pre-filled by the Nuxel prep pass with AUTHORITATIVE upstream values — verify on your unit.**
> Load addresses derived from the pmOS `device-motorola-ocean` deviceinfo (`flash_offset_base=0x80000000`,
> `kernel=0x00008000`, `ramdisk=0x01000000`, `tags=0x00000100`, `pagesize=2048`) and confirmed by the
> TWRP `android_device_motorola_ocean` BoardConfig (BASE 0x80000000, ramdisk offset 0x01000000,
> tags offset 0x100, header v1). WiFi/BT filenames are the upstream WCN3680B/prima set. They are
> NOT fabricated, but you MUST confirm them from YOUR device (`tools/read-boot-header-v1.py` on your
> stock boot.img + `adb shell ls /vendor/firmware`) before flashing. Do not change the field names.

```text
DEVICE_VARIANT: XT1955 (verify exact -x variant: adb shell getprop ro.product.model)
BOOTLOADER_VERSION: UNKNOWN — read from ro.bootloader on your unit
KERNEL_ADDR: 0x80008000
RAMDISK_ADDR: 0x81000000
TAGS_ADDR: 0x80000100
WIFI_FW_FILENAMES: wlan/prima/WCNSS_qcom_cfg.ini, wlan/prima/WCNSS_qcom_wlan_nv.bin, WCNSS_qcom_wlan_nv.bin, wcnss.b00..b09 + wcnss.mdt (WCN3680B, wcn36xx) — VERIFY with: adb shell ls /vendor/firmware/WCNSS* /vendor/firmware/wlan/prima/
BT_FW_FILENAMES: qca/rampatch_*.bin, qca/nvm_*.bin (hci_qca) — VERIFY with: adb shell ls /vendor/firmware/qca/
AUDIO_UCM_CARD: UNKNOWN — collect from aplay -l / /proc/asound/cards
CAMERA_SENSORS: UNKNOWN — identify from dmesg
FINGERPRINT_SENSOR: UNKNOWN — identify from dmesg / /sys/class/fingerprint/
NFC_PRESENT: VERIFY — check dmesg for NFC; ls /dev/nfc*
```

How to fill each field (replace the value after the colon; keep the field
name exactly as written):

| Field | Fill from | Example (this unit only!) |
|---|---|---|
| `DEVICE_VARIANT` | `adb shell getprop ro.product.model` | `XT1955-2` |
| `BOOTLOADER_VERSION` | `adb shell getprop ro.bootloader` | value printed by getprop |
| `KERNEL_ADDR` | `python3 tools/read-boot-header-v1.py /tmp/stock-boot.img` → `kernel_addr` | `0x80008000` (verify from YOUR image) |
| `RAMDISK_ADDR` | same → `ramdisk_addr` | `0x81000000` (verify from YOUR image) |
| `TAGS_ADDR` | same → `tags_addr` | `0x80000100` (verify from YOUR image) |
| `WIFI_FW_FILENAMES` | `adb shell ls /vendor/firmware/WCNSS*` and `/vendor/firmware/wlan/prima/` | e.g. `WCNSS_qcom_wlan_nv.bin` (wcn36xx, not ath10k/brcm) |
| `BT_FW_FILENAMES` | `adb shell ls /vendor/firmware/qca/` | e.g. `rampatch_00130301.bin` / `nvm_tlv_*.bin` (hci_qca) |
| `AUDIO_UCM_CARD` | `aplay -l` / `cat /proc/asound/cards` | WCD9335 card name (cajon-v2) |
| `CAMERA_SENSORS` | `grep -iE 'camera|sensor|ov[0-9]|s5k[0-9]|imx[0-9]|cci' g7power-dmesg.txt` | `UNKNOWN` until collected |
| `FINGERPRINT_SENSOR` | `dmesg` + `ls /sys/class/fingerprint/` | `UNKNOWN` until collected |
| `NFC_PRESENT` | `dmesg` for NFC + `ls /dev/nfc*` | `VERIFY` on the physical unit |

IMPORTANT:

- The four load-address / firmware fields `KERNEL_ADDR`, `RAMDISK_ADDR`,
  `TAGS_ADDR` and `WIFI_FW_FILENAMES` are read by the
  `_check_g7power_inventory()` gate. Leave them at `PLACEHOLDER`/`UNKNOWN`
  and every G7 Power build/flash script exits 1 with the Phase 0 reminder.
- Do NOT invent a plausible value to make the gate pass. The gate exists
  because flashing with wrong load addresses or the wrong WiFi firmware
  filename is a brick risk on msm8953 (lk2nd + ABOOT are picky; recovery is
  EDL 9008 + stock restore).
- Protected partitions (`modemst1`, `modemst2`, `fsg`, `fsc`, `ddr`,
  `persist`, `misc`) are NEVER pulled and NEVER flashed during Phase 0 or
  during any Nuxel build/flash operation — they are per-unit data (IMEI,
  radio calibration, DDR training) with no way to regenerate them.
- After filling, keep this file in the repo: it is the operator record for
  the unit and is consumed by the gate in every G7 Power build/flash script.
- Do not change the field names (the text before the colon). The gate regex
  matches the exact names `KERNEL_ADDR`, `RAMDISK_ADDR`, `TAGS_ADDR` and
  `WIFI_FW_FILENAMES`; renaming them silently disables the safety gate.
