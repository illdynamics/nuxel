# Nuxel — Motorola Moto G7 Power Flash Quickstart
## Device: Motorola Moto G7 Power (XT1955, Snapdragon 632 / SDM632)
## Codename: `ocean` | Nuxel v0.2.0

---

## Flashable ready state

**❌ NOT READY TO FLASH** (`g7power` / `ocean`, Nuxel v0.2.0 — deep-analyze
2026-08-29). lk2nd, mainline kernel, firmware blobs and boot/rootfs images
are all still unbuilt, and Phase 0 device inventory has not been collected.
The gate table below documents every remaining step.

> ⚠️ **HONEST STATUS — READ THIS FIRST**
>
> The G7 Power Nuxel port is **in bring-up**. As of v0.2.0 this is **NOT a
> flashable OS**. This guide documents the complete, correct procedure for when
> the build is ready. All placeholder values are explicitly marked.
>
> The G7 Power actually has the **best mainline Linux support of all three Nuxel
> targets** — the GPU (Adreno 506 / freedreno), display (MSM DRM), touch
> (ILI2117), and backlight (LM3697) are all upstream mainline. WiFi/BT need
> firmware blobs but the drivers are fully mainline. This is the most reachable
> hardware target in the set.

---

## Flash Readiness Gate

| Gate | Status | Notes |
|---|---|---|
| Phase 0 device inventory | ⛔ **REQUIRED FIRST** | Collect dmesg, getevent, firmware listing, stock boot.img addresses |
| Bootloader unlocked | ⛔ **REQUIRED** | `fastboot oem unlock <code>` from Motorola portal — wipes device |
| Stock backup complete | ⛔ **REQUIRED** | dtbo + boot + modem partitions backed up before any flash |
| lk2nd built (msm8953) | ⛔ **NOT YET BUILT** | Clone msm8916-mainline/lk2nd, build msm8953 target |
| Nuxel kernel built (msm8953-mainline) | ⛔ **NOT YET BUILT** | Clone msm8953-mainline/linux, build + DTB |
| Firmware blobs extracted | ⛔ **NOT EXTRACTED** | Must pull from device /vendor/firmware via ADB |
| Flashable boot image (v1) | ⛔ **NOT YET BUILT** | Depends on kernel build |
| Flashable rootfs | ⛔ **NOT YET BUILT** | Depends on kernel + firmware |
| Physical flash to G7 Power | ⛔ **BLOCKED** | All above gates must pass first |

---

## Why the G7 Power is Different from the Other Two Targets

| | Pixel 10 Pro XL (mustang) | Galaxy S10+ (s10plus) | **G7 Power (g7power)** |
|---|---|---|---|
| Flash tool | `fastboot` (Google ABL) | TWRP + heimdall (no fastboot) | **`fastboot` + lk2nd** |
| Boot image | Header **v4** + vendor_boot + init_boot | Header **v1** (page 2048) | **Header v1** (page 2048) |
| Partition model | A/B dynamic super | A-only UFS | **A-only eMMC** |
| GPU driver | PowerVR (vendor only) | Mali Panfrost (mainline) | **freedreno (mainline ✅)** |
| Kernel path | GKI 6.12 (private vendor tree) | linux-postmarketos-exynos9820 | **msm8953-mainline/linux ✅** |
| Mainline readiness | ❌ Very low | 🚧 Medium | **✅ High** |
| Chainloader | None (Google ABL works) | U-Boot (chiffathefox) | **lk2nd (msm8916-mainline)** |
| Unbrick path | `fastboot` always works | Download Mode + heimdall | **EDL (Qualcomm 9008)** |

---

## Device Identity Reference

| Field | Value |
|---|---|
| Device | Motorola Moto G7 Power |
| Model | XT1955 (variant suffix: -2, -4, -7 etc. — check yours) |
| Codename | `ocean` |
| SoC | Qualcomm Snapdragon 632 (SDM632), 14 nm |
| CPU | 4× Kryo 250 Gold (Cortex-A73) + 4× Kryo 250 Silver (Cortex-A53) @ 1.8 GHz |
| GPU | Qualcomm Adreno 506 → **freedreno** (fully mainline) |
| RAM | 3 GB or 4 GB LPDDR3 (variant) |
| Storage | 32/64 GB eMMC + microSD; path: `/dev/block/bootdevice/by-name/` |
| Display | 6.2″ IPS LCD, **1520×720**, 19:9; Backlight: TI LM3697 @ I2C i2c_5 0x36 |
| Touch | Ilitek **ILI2117** @ I2C i2c_3 0x41, IRQ tlmm 65, **inverted-x** |
| Touch driver | `ili210x` (mainline `CONFIG_TOUCHSCREEN_ILI210X`) |
| WiFi | Qualcomm **WCN3680B** (802.11 b/g/n, 2.4 GHz only) |
| WiFi driver | `wcn36xx` + `CONFIG_QCOM_WCNSS_PIL` (**NOT ath10k, NOT brcmfmac**) |
| Bluetooth | BT 4.2 (WCN3680B integrated); driver: `hci_qca` |
| Modem | Snapdragon X9 LTE (integrated, Cat 7, no 5G); Phase 1: WiFi only |
| Audio | Qualcomm **WCD9335** (cajon-v2) ASoC codec |
| Sensors | Bosch **BMI160** (accel+gyro), MEMSIC **MMC3630KJ** (mag), AMS **TMD2725** (prox+ALS) |
| NFC | None (most variants — verify on device) |
| Battery | 5000 mAh, 15W TurboPower (QC 3.0) |
| Boot model | **A-only** (no A/B slots) |
| Boot image | **Legacy Android boot image header v1** (page 2048) |
| Shipped kernel | Qualcomm 4.9 downstream |
| Flash method | **`fastboot`** (stock ABOOT + lk2nd) + **EDL 9008** (unbrick) |
| Unlock method | `fastboot oem unlock <code>` (code from Motorola portal) |

---

## The G7 Power Boot Chain

This is essential to understand before touching anything:

```
Qualcomm Boot ROM (PBL — Primary Bootloader in SoC ROM)
    │
    ▼
Stock Motorola ABOOT (eMMC boot partition)
    │  Initializes DDR, eMMC, display framebuffer
    │  ✗ CANNOT: accept mainline DTBs or cmdline correctly
    │  ✓ CAN: boot a legacy v1 boot.img; present fastboot mode
    │
    │  ──── PHASE 1 FLASH (via stock ABOOT fastboot) ────
    │  1. fastboot flash dtbo dtbo.img    ← MANDATORY FIRST
    │  2. fastboot flash boot lk2nd.img   ← installs lk2nd
    │
    ▼ (on next reboot — lk2nd is now in the boot partition)
lk2nd (msm8916-mainline/lk2nd, msm8953 target)
    │  Qualcomm mainline secondary bootloader
    │  Accepts correct mainline DTBs + cmdline
    │  Presents its own fastboot interface
    │
    │  ──── PHASE 2 FLASH (via lk2nd fastboot) ────
    │  3. fastboot flash boot nuxel-ocean-boot.img
    │  4. fastboot flash userdata nuxel-ocean-rootfs.img
    │
    ▼
linux-postmarketos-qcom-msm8953
    │  (msm8953-mainline/linux — close to upstream mainline)
    │  nuxel.device=g7power on cmdline
    │
    ▼
Nuxel initramfs → probes /dev/block/bootdevice/by-name/userdata
    │
    ▼
Nuxel rootfs → Phosh + GTK4 + PWA apps
```

### The dtbo-first rule (critical — never skip this)

On msm8953, stock ABOOT reads the `dtbo` partition before handing off to
the boot image. If `dtbo` is corrupted or absent, ABOOT can hang before
lk2nd even gets a chance to run — resulting in a soft brick that requires
EDL to recover. **Always flash a known-good `dtbo` before writing lk2nd.**

### The two fastboot modes

There are two distinct fastboot modes. Knowing which one you're in matters:

| Mode | How to enter | What it can flash | Identifies as |
|---|---|---|---|
| **Stock ABOOT fastboot** | Power off → hold Vol Down + Power | `dtbo`, `boot` (lk2nd), `recovery` | Product: `ocean` |
| **lk2nd fastboot** | Power off → hold Vol Down + Power (after lk2nd is installed) | `boot` (kernel), `userdata` (rootfs), and more | May differ slightly — verify with `fastboot getvar product` |

After installing lk2nd to the boot partition, the device will boot into
lk2nd on the next reboot. From lk2nd you enter its own fastboot by holding
Vol Down + Power from off. It's the same key combo, but lk2nd is now in
control instead of stock ABOOT.

---

## Prerequisites

### Hardware

- Motorola Moto G7 Power (XT1955, any variant)
- USB-C data cable (not charge-only)
- Battery > 60%
- A Motorola account (required for unlock portal)

### Host Software

```bash
# Linux (Debian/Ubuntu)
sudo apt update
sudo apt install android-tools-adb android-tools-fastboot \
    gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
    gcc-arm-none-eabi binutils-arm-none-eabi \
    git make python3 bc bison flex libssl-dev libelf-dev

# Verify:
adb version          # must be present
fastboot --version   # must be present

# macOS
brew install android-platform-tools
brew tap messense/macos-cross-toolchains
brew install aarch64-unknown-linux-gnu
# For lk2nd (ARM32 cross-compiler):
brew install arm-none-eabi-gcc

# Verify
adb version
fastboot --version
aarch64-unknown-linux-gnu-gcc --version
arm-none-eabi-gcc --version
```

### Carrier-lock check

```bash
# On the device: Settings → About phone → SIM status
# If "Network locked" appears: the bootloader CANNOT be unlocked. Stop here.
```

---

## MANDATORY: Full Stock Backup Before Anything

Run this before ANY unlock or flash operation. **These partitions contain
your IMEI, MAC address, and radio calibration — they are irreplaceable if
wiped.** The backup takes about 5 minutes and could save your device.

```bash
# Ensure USB debugging is enabled and device is connected
adb devices
# Expected: <serial>    device

# Create a backup directory on the device's SD card
adb shell "mkdir -p /sdcard/nuxel-backup-ocean"

# Back up the critical and protected partitions
for part in boot recovery dtbo modemst1 modemst2 fsg fsc ddr persist misc; do
    echo "Backing up ${part}..."
    adb shell "dd if=/dev/block/bootdevice/by-name/${part} \
        of=/sdcard/nuxel-backup-ocean/${part}.img bs=4096 2>/dev/null && \
        echo '  OK: ${part}' || echo '  SKIP: ${part} (partition may not exist)'"
done

# Pull the backup to your host machine
mkdir -p ~/g7power-backup
adb pull /sdcard/nuxel-backup-ocean ~/g7power-backup/
echo "Backup complete. Store ~/g7power-backup/ in a safe place."
ls -lh ~/g7power-backup/

# KEEP THESE. You need them for recovery.
# dtbo.img  → needed to revert safely
# boot.img  → stock boot; needed for recovery and for extracting load addresses
# modemst1/2, fsg, fsc, ddr → IRREPLACEABLE calibration data
```

---

## Phase 0 — Device Inventory (Non-Destructive, Run First)

This collects the data needed to build correct kernel, firmware manifest, and
boot images. Runs on the unmodified device. Does not change anything.

```bash
# Verify identity
adb shell getprop ro.product.device   # must be: ocean
adb shell getprop ro.product.name     # e.g.: ocean
adb shell getprop ro.product.model    # e.g.: XT1955-2 (note the variant suffix)
adb shell getprop ro.bootloader       # save this string
adb shell getprop ro.build.id         # save this string

# Hardware props
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|qcom|msm|sdm' \
    > g7power-props.txt

# Kernel cmdline
adb shell cat /proc/cmdline

# Full dmesg — most important output; identifies every driver, sensor, camera
adb shell dmesg > g7power-dmesg.txt
echo "Key things to grep for:"
grep -iE 'ili210|touch|panel|backlight|lm3697' g7power-dmesg.txt | head -20
grep -iE 'wcn36|qcom.*wifi|wlan' g7power-dmesg.txt | head -20
grep -iE 'wcd9335|codec|audio|sound' g7power-dmesg.txt | head -20
grep -iE 'camera|cci|ov[0-9]|s5k|imx[0-9]' g7power-dmesg.txt | head -20
grep -iE 'fingerprint|fps' g7power-dmesg.txt | head -10

# Input devices (confirms ILI2117 + inverted-x)
adb shell getevent -pl 2>/dev/null > g7power-input-devices.txt
cat g7power-input-devices.txt | grep -iE 'name|ili|touch'

# eMMC partition table
adb shell ls -la /dev/block/bootdevice/by-name/ > g7power-partitions.txt
cat g7power-partitions.txt

# Vendor firmware listing (critical for manifest.yml)
adb shell ls -laR /vendor/firmware/       > g7power-vendor-firmware.txt
adb shell ls -laR /vendor/firmware_mnt/   >> g7power-vendor-firmware.txt 2>/dev/null
adb shell ls -laR /vendor/lib/modules/    > g7power-vendor-modules.txt
adb shell ls -laR /vendor/etc/firmware/   > g7power-vendor-etc-fw.txt 2>/dev/null

# WiFi firmware (wcn36xx — NOT brcm, NOT ath)
echo "=== WiFi firmware ==="
adb shell ls /vendor/firmware/WCNSS*           2>/dev/null
adb shell ls /vendor/firmware/wlan/prima/      2>/dev/null
adb shell ls /vendor/firmware/wlan_mac.bin     2>/dev/null

# BT firmware (hci_qca)
echo "=== BT firmware ==="
adb shell ls /vendor/firmware/qca/             2>/dev/null

# Audio card
echo "=== Audio ==="
adb shell cat /proc/asound/cards               2>/dev/null
adb shell ls /sys/class/sound/                 2>/dev/null

# Extract boot image load addresses from stock boot.img
adb shell "dd if=/dev/block/bootdevice/by-name/boot \
    of=/sdcard/stock-boot.img bs=4096"
adb pull /sdcard/stock-boot.img /tmp/stock-boot.img
python3 tools/read-boot-header-v1.py /tmp/stock-boot.img
# Save: kernel_addr, ramdisk_addr, tags_addr, page_size, cmdline

echo ""
echo "=== Phase 0 Complete ==="
echo "Update docs/g7power-device-inventory.md with:"
echo "  KERNEL_ADDR, RAMDISK_ADDR, TAGS_ADDR (from boot.img header)"
echo "  WIFI_FW_FILENAMES  (from /vendor/firmware/WCNSS*)"
echo "  BT_FW_FILENAMES    (from /vendor/firmware/qca/)"
echo "  AUDIO_UCM_CARD     (from /proc/asound/cards)"
echo "  CAMERA_SENSORS     (from dmesg grep)"
echo "  FINGERPRINT_SENSOR (from dmesg grep)"
```

---

## Phase 1 — Unlock the Bootloader

> ⚠️ **`fastboot oem unlock` FACTORY RESETS the device. All data is wiped.**
> Complete the backup above before this step.

```bash
# Step 1: Enable Developer Options and OEM Unlock
# Settings → About phone → tap "Build number" 7 times
# Settings → System → Developer options:
#   Toggle "OEM unlocking" ON
#   Toggle "USB debugging" ON
# Authorize the RSA key on the device when prompted.

# Step 2: Reboot to fastboot (stock ABOOT)
adb reboot bootloader
# OR: power off → hold Vol Down + Power

# Step 3: Verify you're in stock ABOOT fastboot
fastboot devices
# Expected: <serial>    fastboot
fastboot getvar product
# Expected: product: ocean
fastboot getvar unlocked
# Expected: unlocked: no (before unlock)

# Step 4: Get unlock data
fastboot oem get_unlock_data
# This prints a long hex string to the terminal. Copy the ENTIRE string.
# It may be split across multiple lines — join them into one continuous string.

# Step 5: Get unlock code from Motorola
# Open: https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device
# Sign in with your Motorola account (create one if needed).
# Paste the unlock data string. Submit. Wait for the unlock code by email.
# (Usually instant, sometimes up to a few hours.)

# Step 6: Unlock (WIPES DEVICE)
fastboot oem unlock <YOUR_UNLOCK_CODE_FROM_EMAIL>
# Device displays warning screen. Volume buttons to select "Unlock".
# Power to confirm. Device factory resets and reboots.

# Step 7: Re-enable USB debugging after reboot
# Settings → System → Developer options → USB debugging ON

# Step 8: Verify unlock
adb reboot bootloader
fastboot getvar unlocked
# Expected: unlocked: yes
```

---

## Phase 2 — Extract Firmware Blobs

```bash
# Device must be booted into Android with USB debugging enabled

# Pull vendor firmware into the Nuxel repo:
NUXEL_DEVICE=g7power bash firmware/g7power/install-firmware.sh --adb-pull
# This runs:
#   adb pull /vendor/firmware       firmware/g7power/blobs/vendor-firmware/
#   adb pull /vendor/firmware_mnt   firmware/g7power/blobs/vendor-firmware-mnt/
#   adb pull /vendor/lib/modules    firmware/g7power/blobs/vendor-modules/

# After pull, fill in checksums in firmware/g7power/manifest.yml:
sha256sum firmware/g7power/blobs/vendor-firmware/WCNSS_qcom_cfg.ini
sha256sum firmware/g7power/blobs/vendor-firmware/WCNSS_qcom_wlan_nv.bin
sha256sum firmware/g7power/blobs/vendor-firmware/qca/*.bin  2>/dev/null
sha256sum firmware/g7power/blobs/vendor-firmware/a506_zap.mbn  2>/dev/null
# Fill all sha256 hashes into firmware/g7power/manifest.yml

# Verify the manifest:
NUXEL_DEVICE=g7power bash firmware/g7power/verify-firmware.sh
```

---

## Phase 3 — Install Build Toolchain

The G7 Power needs **two** cross-compilers: `aarch64` for the Linux kernel and
`arm-none-eabi` for lk2nd (which is a 32-bit ARM LK bootloader).

```bash
# Linux (Debian/Ubuntu)
sudo apt update
sudo apt install \
    gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
    gcc-arm-none-eabi binutils-arm-none-eabi \
    bc bison flex libssl-dev libelf-dev make git python3

# Verify both:
aarch64-linux-gnu-gcc --version
# Expected: aarch64-linux-gnu-gcc (Ubuntu ...) 10.x.x or 11.x.x

arm-none-eabi-gcc --version
# Expected: arm-none-eabi-gcc (GNU Arm Embedded Toolchain ...) 10.x.x

# Set environment for kernel builds:
export CROSS_COMPILE=aarch64-linux-gnu-
export ARCH=arm64

# Set environment for lk2nd build:
export TOOLCHAIN_PREFIX=arm-none-eabi-
```

---

## Phase 4 — Build lk2nd (Mainline Qualcomm Bootloader)

lk2nd is what replaces the stock ABOOT for accepting mainline kernels. Build
it first because it needs to be flashed before the mainline kernel.

```bash
# Clone lk2nd
git clone https://github.com/msm8916-mainline/lk2nd
cd lk2nd

# Build for msm8953 target (covers SDM632 / ocean)
make TOOLCHAIN_PREFIX=arm-none-eabi- msm8953 -j$(nproc)

# Verify the output
ls -lh build-msm8953/lk2nd.img
# Expected: ~2-4 MB file; binary that ABOOT will accept as a boot.img

# Copy to Nuxel repo
cp build-msm8953/lk2nd.img <NUXEL_ROOT>/boot/g7power/lk2nd/lk2nd-msm8953.img

# KEEP THE STOCK BOOT.IMG BACKUP. It's your recovery if lk2nd has issues.
```

---

## Phase 5 — Build the Nuxel Kernel

```bash
cd <NUXEL_ROOT>

# Clone and build linux-postmarketos-qcom-msm8953
NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --clone

# This will:
# 1. Clone: https://github.com/msm8953-mainline/linux
# 2. Apply Nuxel patches from kernel/g7power/patches/
# 3. Merge kernel/g7power/defconfig on top of msm8953_defconfig
# 4. Build: Image.gz + sdm632-motorola-ocean.dtb + modules

# Verify outputs:
ls -lh kernel/g7power/.build/out/arch/arm64/boot/Image.gz
ls kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/ | grep ocean
# Expected: sdm632-motorola-ocean.dtb

ls kernel/g7power/.build/modules-staging/lib/modules/
# Expected: module directory for the built kernel version

# Key drivers to verify were compiled (check .config):
grep -E 'CONFIG_DRM_MSM|CONFIG_WCN36XX|CONFIG_TOUCHSCREEN_ILI210X|CONFIG_SND_SOC_WCD9335' \
    kernel/g7power/.build/out/.config
# All should show =y or =m
```

---

## Phase 6 — Build Nuxel Boot Images

```bash
# Build the full G7 Power image set
NUXEL_DEVICE=g7power bash images/g7power/build.sh

# This produces in build/out/g7power/:
#   lk2nd.img                  — copy of lk2nd-msm8953.img (for convenience)
#   nuxel-ocean-boot.img       — Nuxel kernel + initramfs (v1 format, page 2048)
#   nuxel-ocean-rootfs.img     — ext4 rootfs for userdata partition
#   build-manifest.json        — build metadata

# Verify:
ls -lh build/out/g7power/
cat build/out/g7power/build-manifest.json
```

### Boot image v1 format details (G7 Power)

The G7 Power uses a **legacy Android boot image header v1** — the same format
as the S10+, but with different load addresses. Key fields:

| Field | Value | Notes |
|---|---|---|
| Magic | `ANDROID!` | Always this exact string |
| Page size | 2048 bytes | Standard for msm8953 |
| Header version | 1 | Legacy format |
| kernel_addr | `PLACEHOLDER` | Extract from stock boot.img |
| ramdisk_addr | `PLACEHOLDER` | Extract from stock boot.img |
| tags_addr | `PLACEHOLDER` | Extract from stock boot.img |
| DTB | Appended after ramdisk | `sdm632-motorola-ocean.dtb` |
| Signing | None (Phase 1) | No AVB for initial bring-up |

```bash
# Extract load addresses from stock boot.img (run this during Phase 0):
python3 tools/read-boot-header-v1.py ~/g7power-backup/boot.img
# Output (example — VERIFY on your specific device):
#   magic:        ANDROID!
#   kernel_size:  XXXXXXXX
#   kernel_addr:  0x80008000    ← save this
#   ramdisk_addr: 0x81000000    ← save this
#   tags_addr:    0x80000100    ← save this
#   page_size:    2048
#   cmdline:      [existing stock cmdline]

# Build the boot image manually (if build.sh is not ready):
bash boot/g7power/pack-boot-v1.sh \
    --kernel kernel/g7power/.build/out/arch/arm64/boot/Image.gz \
    --ramdisk boot/initramfs/initramfs.cpio.gz \
    --dtb kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb \
    --cmdline "console=ttyMSM0,115200 earlycon=msm_geni_serial,0xa88000 nuxel.device=g7power root=/dev/block/bootdevice/by-name/userdata rootfstype=ext4 rootwait rw" \
    --output build/out/g7power/nuxel-ocean-boot.img
```

---

## Phase 7 — Flash to the Motorola Moto G7 Power

### Pre-flash checklist

- [ ] Full stock backup complete (`~/g7power-backup/boot.img`, `dtbo.img`, modem partitions)
- [ ] Bootloader unlocked (`fastboot getvar unlocked` → `yes`)
- [ ] Phase 0 inventory complete (load addresses filled in)
- [ ] Firmware blobs extracted + checksums in manifest
- [ ] lk2nd built (`boot/g7power/lk2nd/lk2nd-msm8953.img` exists)
- [ ] Nuxel kernel built (`build/out/g7power/nuxel-ocean-boot.img` exists)
- [ ] Nuxel rootfs built (`build/out/g7power/nuxel-ocean-rootfs.img` exists)
- [ ] Battery > 60%
- [ ] DO NOT touch: `modemst1`, `modemst2`, `fsg`, `fsc`, `ddr`, `persist`, `misc`

### Flash sequence — using the flash script

```bash
# === PHASE 1: Stock ABOOT fastboot ===
# Device must be in fastboot mode: power off → hold Vol Down + Power

# Verify you're in stock ABOOT fastboot:
fastboot getvar product    # must be: ocean
fastboot getvar unlocked   # must be: yes

# Flash dtbo FIRST (mandatory — prevents soft brick on msm8953):
# Then flash lk2nd to the boot partition:
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh \
    --device g7power \
    --dtbo ~/g7power-backup/dtbo.img \
    --lk2nd boot/g7power/lk2nd/lk2nd-msm8953.img
# Script will: flash dtbo → flash lk2nd → reboot into lk2nd fastboot

# === PHASE 2: lk2nd fastboot ===
# Device reboots into lk2nd. Re-enter fastboot: power off → hold Vol Down + Power
# (Now in lk2nd fastboot, not stock ABOOT fastboot)

# Verify lk2nd fastboot:
fastboot getvar product    # should still show ocean or similar

# Flash Nuxel kernel + rootfs:
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh \
    --device g7power \
    --boot build/out/g7power/nuxel-ocean-boot.img \
    --rootfs build/out/g7power/nuxel-ocean-rootfs.img
# Script will: flash boot.img → flash rootfs to userdata → reboot
```

### Flash sequence — manual step by step

```bash
# ─────────────────────────────────────────────────────────────────────
# PHASE 1: Stock ABOOT fastboot (power off → hold Vol Down + Power)
# ─────────────────────────────────────────────────────────────────────

# Verify device identity (NEVER skip this):
fastboot getvar product      # must be: ocean
fastboot getvar unlocked     # must be: yes

# Step 1: Flash dtbo FIRST (MANDATORY — soft-brick prevention):
fastboot flash dtbo ~/g7power-backup/dtbo.img
# (Use backed-up stock dtbo for Phase 1 flash)

# Step 2: Flash lk2nd to the boot partition:
fastboot flash boot boot/g7power/lk2nd/lk2nd-msm8953.img

# Step 3: Reboot into lk2nd fastboot:
fastboot reboot bootloader
# Device reboots. lk2nd loads. Re-enter fastboot: power off → Vol Down + Power.

# ─────────────────────────────────────────────────────────────────────
# PHASE 2: lk2nd fastboot (power off → hold Vol Down + Power again)
# ─────────────────────────────────────────────────────────────────────

# Verify lk2nd fastboot is responding:
fastboot devices
fastboot getvar product   # ocean (or lk2nd variant string)

# Step 4: Flash Nuxel kernel boot image (v1 format):
fastboot flash boot build/out/g7power/nuxel-ocean-boot.img

# Step 5: Flash Nuxel rootfs to userdata:
# WARNING: Overwrites all data on userdata partition.
fastboot flash userdata build/out/g7power/nuxel-ocean-rootfs.img

# Optional: wipe userdata metadata (clean install):
# fastboot erase metadata

# Step 6: Reboot into Nuxel:
fastboot reboot

# ─────────────────────────────────────────────────────────────────────
# Expected boot sequence:
# 1. lk2nd logo / boot
# 2. lk2nd loads nuxel-ocean-boot.img
# 3. Kernel console output (ttyMSM0)
# 4. Nuxel initramfs → mounts userdata
# 5. Phosh launches at 1520×720
# ─────────────────────────────────────────────────────────────────────
```

---

## Recovery Paths

### Quick revert (boot partition only — fastest)

If Nuxel doesn't boot but fastboot still works:

```bash
# Enter stock ABOOT fastboot (Vol Down + Power from off)
fastboot getvar product   # must be: ocean

# Flash stock dtbo + boot (restores to pre-lk2nd state):
fastboot flash dtbo ~/g7power-backup/dtbo.img
fastboot flash boot ~/g7power-backup/boot.img
fastboot reboot
# Device boots back into stock Android. Done.

# Or using the flash script:
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh \
    --device g7power \
    --revert \
    --stock-dtbo ~/g7power-backup/dtbo.img \
    --stock-boot  ~/g7power-backup/boot.img
```

### Full stock restore (all partitions)

If the device boots but behaves incorrectly, or you want a clean slate:

```bash
# 1. Download Motorola stock firmware for your exact model (XT1955-X)
#    From: https://mirrors.lolinet.com/firmware/moto/ocean/
#    Or:   https://support.lenovo.com (Motorola support)
#    Match the firmware build ID to your ro.build.id from Phase 0.

# 2. Extract the firmware zip — contains individual partition images.

# 3. Restore critical partitions via fastboot (stock ABOOT mode):
fastboot flash boot      stock/boot.img
fastboot flash recovery  stock/recovery.img
fastboot flash dtbo      stock/dtbo.img
fastboot flash system    stock/system.img
fastboot flash vendor    stock/vendor.img
fastboot -w              # wipe userdata + metadata
fastboot reboot

# The modem partitions (modemst1/modemst2/fsg/fsc/ddr) should already be intact
# from your backup. Only flash them from backup if you believe they were corrupted.
```

### EDL (Qualcomm 9008) — The Nuclear Option

Use this only if fastboot is completely inaccessible (the device is hard-bricked
and neither stock ABOOT fastboot nor lk2nd fastboot respond):

```bash
# Step 1: Enter EDL mode
# Power off completely. Hold Vol Down + Vol Up simultaneously. Plug in USB.
# The screen stays off — this is normal. EDL has no display output.

# Step 2: Verify host detects the device
lsusb | grep "05C6:9008"
# Expected: Bus XXX Device YYY: ID 05c6:9008 Qualcomm, Inc. Gobi Wireless Modem (QDL mode)

# Step 3: Install edl tool (bkerler/edl — best open-source EDL client)
pip3 install edl

# Step 4: Flash individual partitions (use backed-up stock images)
edl flash boot      ~/g7power-backup/boot.img
edl flash dtbo      ~/g7power-backup/dtbo.img
edl flash recovery  ~/g7power-backup/recovery.img
edl flash persist   ~/g7power-backup/persist.img   # only if corrupted
edl reset

# Step 5: Device should reboot normally after flashing boot + dtbo.
# If not: flash system + vendor from stock firmware as well.

# Windows alternative: QFIL (Qualcomm Flash Image Loader)
#   Requires: QDLoader 9006/9008 drivers + firehose programmer for XT1955
#   Search XDA Developers for "XT1955 QFIL flash guide"
```

---

## Phase-by-Phase Bring-Up Plan

| Phase | Goal | Entry Criteria | Exit Criteria |
|---|---|---|---|
| 0 | Device inventory | Android booted, USB debugging on | All unknowns in `docs/g7power-device-inventory.md` filled |
| 1 | lk2nd + kernel boot | Phase 0 done + toolchain + backup | lk2nd loads; kernel boots to debug console on ttyMSM0 |
| 2 | Display + touch | Phase 1 done | Phosh at 1520×720; ILI2117 touch responds (verify inverted-x) |
| 3 | WiFi | Phase 2 done + WCN3680B firmware | `wlan0` up via wcn36xx; `ip link show wlan0` |
| 4 | BT | Phase 3 done + hci_qca firmware | `bluetoothctl power on` succeeds |
| 5 | Audio | Phase 4 done + WCD9335 UCM | Speaker output via PipeWire UCM |
| 6 | GPU full accel | Phase 5 done | Mesa freedreno GLES in Phosh (no llvmpipe fallback) |
| 7 | Modem/camera | Phase 6 done | Stretch goal: X9 LTE MM plugin; camera ISP |

---

## Driver Status

| Subsystem | Status | Notes |
|---|---|---|
| GPU (Adreno 506 / freedreno) | ✅ **Mainline** | `CONFIG_DRM_MSM`; Mesa freedreno; full upstream |
| Display (MSM DRM / DSI) | ✅ **Mainline** | MSM DRM; framebuffer from lk2nd on first boot |
| Backlight (TI LM3697) | ✅ **Mainline** | `CONFIG_BACKLIGHT_TI_LM3697` |
| Touch (ILI2117 `ili210x`) | ✅ **Mainline** | `CONFIG_TOUCHSCREEN_ILI210X`; i2c_3 @ 0x41; verify inverted-x on device |
| WiFi (WCN3680B `wcn36xx`) | 🚧 Needs firmware | Driver mainline; WCNSS_PIL firmware from device |
| Bluetooth (WCN3680B `hci_qca`) | 🚧 Needs firmware | Driver mainline; hcd firmware from device |
| Accel/Gyro (BMI160) | ✅ **Mainline** | `CONFIG_BMI160_I2C`; mainline IIO driver |
| Magnetometer (MMC3630KJ) | 🚧 Check tree | Verify driver symbol in msm8953 kernel tree |
| Prox+ALS (TMD2725) | 🚧 Check tree | Verify driver symbol in msm8953 kernel tree |
| Audio (WCD9335 cajon-v2) | 🚧 Partial mainline | ASoC driver; UCM from msm8953-mainline/alsa-ucm-conf |
| eMMC (mmc_core) | ✅ **Mainline** | Standard MMC; no special driver needed |
| USB (dwc3) | ✅ **Mainline** | fastboot gadget works; no fastbootd (A-only device) |
| Modem (X9 LTE) | ❌ Not MM-ready | No upstream MM plugin; WiFi only in Phase 1–6 |
| Camera | ⬜ Unknown | Identify sensors from dmesg in Phase 0 |
| NFC | ✅ N/A | None on most variants — verify `ls /dev/nfc*` |
| Fingerprint | ⬜ Unknown | Rear-mounted; identify from dmesg in Phase 0 |

**Bottom line:** This is the most mainline-friendly Nuxel target. GPU, display,
backlight, and touch are all upstream. The G7 Power has a genuinely achievable
Phase 1–3 boot path.

---

## Key Differences from S10+ Flash Procedure

Both devices use legacy boot image v1. Everything else differs:

| | Galaxy S10+ | **Moto G7 Power** |
|---|---|---|
| Chainloader | U-Boot (chiffathefox) | **lk2nd (msm8916-mainline)** |
| Flash tool | TWRP `adb+dd` (**no fastboot**) | **fastboot** (2 phases) |
| Storage | UFS 2.1 | **eMMC** |
| Partition path | `/dev/block/platform/13d60000.ufs/by-name/` | **`/dev/block/bootdevice/by-name/`** |
| Unlock | Knox trip (already done) | **`fastboot oem unlock <code>`** (Motorola portal) |
| Unbrick | Download Mode + heimdall | **EDL (Qualcomm 9008) + edl tool** |
| dtbo requirement | Not applicable | **Must flash dtbo before lk2nd** |
| Fastboot phases | N/A — no fastboot | **Phase 1 (stock ABOOT) then Phase 2 (lk2nd)** |

---

## Warnings Reference Card

Print this and keep it nearby during flashing:

```
╔══════════════════════════════════════════════════════════════════════╗
║          NUXEL G7 POWER (OCEAN) FLASH SAFETY REFERENCE              ║
╠══════════════════════════════════════════════════════════════════════╣
║  NEVER TOUCH THESE PARTITIONS:                                       ║
║    modemst1  modemst2  fsg  fsc  ddr  persist  misc                 ║
║  These hold your IMEI, MAC, and radio calibration — irreplaceable.  ║
╠══════════════════════════════════════════════════════════════════════╣
║  ALWAYS FLASH dtbo BEFORE lk2nd.                                     ║
║  Flashing lk2nd without a valid dtbo = soft brick on msm8953.       ║
╠══════════════════════════════════════════════════════════════════════╣
║  TWO FASTBOOT MODES — know which one you're in:                      ║
║  Phase 1: Stock ABOOT fastboot → for dtbo + lk2nd only              ║
║  Phase 2: lk2nd fastboot       → for kernel boot.img + rootfs       ║
╠══════════════════════════════════════════════════════════════════════╣
║  WiFi driver: wcn36xx + CONFIG_QCOM_WCNSS_PIL                        ║
║  NOT ath10k. NOT brcmfmac. Loading wrong driver = no WiFi.           ║
╠══════════════════════════════════════════════════════════════════════╣
║  REVERT (fast): fastboot flash dtbo <stock> → flash boot <stock>    ║
║  UNBRICK: Power off → Vol Down + Vol Up + USB → EDL 9008 mode       ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Key URLs

| Resource | URL |
|---|---|
| pmOS msm8953 generic | https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_450/625/626/632_(MSM8953) |
| pmOS Moto G7 Power | https://wiki.postmarketos.org/wiki/Motorola_Moto_G7_Power_(motorola-ocean) |
| lk2nd bootloader | https://github.com/msm8916-mainline/lk2nd |
| msm8953 mainline kernel | https://github.com/msm8953-mainline/linux |
| msm8953 ALSA UCM configs | https://github.com/msm8953-mainline/alsa-ucm-conf |
| Motorola unlock portal | https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device |
| edl tool (EDL/9008 flash) | https://github.com/bkerler/edl |
| Motorola stock firmware | https://mirrors.lolinet.com/firmware/moto/ocean/ |

---

## FAQ

**Q: Do I need a Motorola account to unlock the bootloader?**
Yes. The Motorola unlock portal requires an account to generate an unlock code.
Create one free at motorola.com before starting.

**Q: Why are there two fastboot modes? That's confusing.**
Stock ABOOT fastboot and lk2nd fastboot are two completely separate programs in
the same boot partition slot. lk2nd replaces stock ABOOT in the boot partition.
After flashing lk2nd, the "fastboot" that responds is lk2nd's implementation,
not Motorola's. They both respond to the same `fastboot` host tool, but lk2nd
correctly handles mainline kernels and device trees.

**Q: My unlock code from the Motorola portal says "device not eligible".**
Your device is likely carrier-locked or hasn't met a service requirement. Common
cause: the device needs to have been activated for 30+ days on the original
carrier. Contact your carrier or wait the eligibility period.

**Q: I flashed lk2nd but the device is stuck on the Motorola logo.**
This usually means the dtbo was bad or missing before lk2nd was flashed.
Enter stock ABOOT fastboot (if accessible) and run the revert:
`fastboot flash dtbo <backup-dtbo.img> && fastboot flash boot <backup-boot.img>`.
If fastboot is not accessible, use EDL (Qualcomm 9008 mode).

**Q: The touch screen is inverted/mirrored after Nuxel boots.**
The DTS specifies `inverted-x`, and mainline `ili210x` applies it in the kernel
(through the generic touchscreen-property helpers). The Xorg InputClass that
also carried `TransformationMatrix "-1 0 1 0 1 0 0 0 1"` is therefore
**disabled** (`configs/g7power/libinput/99-nuxel-ocean-touch.conf.disabled`) —
enabling it would invert X twice and mirror touch. If touch still appears
mirrored, first check that only ONE layer inverts: confirm
`touchscreen-inverted-x` is present in the live DT, run
`evtest /dev/input/eventX` and compare X against display coordinates, and do
**not** add a matrix unless the DT property is removed first. (Under Wayland/
Phosh, `xorg.conf.d` is not read at all — the only sane per-device override
would be the `LIBINPUT_CALIBRATION_MATRIX` udev property.)

**Q: Will I have cellular service in Nuxel on the G7 Power?**
No, not in Phases 1–6. The Snapdragon X9 LTE modem is integrated but there is
no ModemManager plugin for it on msm8953. Phase 1–6 target WiFi only. Cellular
data/calls/SMS are a Phase 7 stretch goal requiring a custom MM plugin.

**Q: Can I still use the G7 Power as a phone (calls + SMS) after reverting?**
Yes. Reverting via `fastboot flash dtbo <stock> && fastboot flash boot <stock>`
restores stock Motorola Android completely. The bootloader remains unlocked but
that doesn't affect normal phone functionality.

**Q: What's the difference between lk2nd and U-Boot? The S10+ uses U-Boot.**
Both are secondary bootloaders that sit between the stock vendor bootloader and
the mainline Linux kernel. U-Boot is the approach used by the S10+ (Exynos
family), while lk2nd is specific to Qualcomm platforms. lk2nd is built on top
of the Little Kernel (LK) codebase, the same codebase stock ABOOT is built on,
which makes it compatible with the boot partition format stock ABOOT expects.

**Q: The G7 Power doesn't have NFC. Does Nuxel support it anyway?**
Most G7 Power variants (ocean) do not have NFC hardware. Nuxel doesn't need NFC
for core functionality. If your unit somehow has it, check `ls /dev/nfc*` and
`dmesg | grep nfc` — report the chip to update the hardware ID table.

---

*Build the bunker first. Add the rave lights later.*
*— Nuxel v0.2.0*
