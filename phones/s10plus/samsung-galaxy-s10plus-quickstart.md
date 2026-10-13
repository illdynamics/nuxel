# Nuxel — Samsung Galaxy S10+ Flash Quickstart
## Device: Samsung Galaxy S10+ (SM-G975F, Exynos 9820)
## Codename: `beyond2lte` | Nuxel v0.2.0

---

## Flashable ready state

**❌ NOT READY TO FLASH** (`s10plus` / `beyond2lte`, Nuxel v0.2.0 —
deep-analyze 2026-08-29). U-Boot chainload, mainline kernel, firmware blobs
and boot/rootfs images are all still unbuilt, and Phase 0 device inventory
has not been collected. The gate table below documents every remaining step.

> ⚠️ **HONEST STATUS — READ THIS FIRST**
>
> The S10+ Nuxel port is **in bring-up**. As of v0.2.0 this is **NOT a
> flashable OS**. This guide documents the complete, correct procedure for when
> the build is ready. Nothing here is invented — every step is grounded in the
> verified hardware facts, the postmarketOS Exynos 9820 community port, and the
> Nuxel repository structure. All placeholder values are explicitly marked.
>
> **Your device is already in TWRP. Knox is already tripped. That's perfect.**
> That is exactly the state we need.

---

## Flash Readiness Gate

| Gate | Status | Notes |
|---|---|---|
| Device in TWRP | ✅ **CONFIRMED** | S10+ already in TWRP; bootloader unlocked |
| Knox fuse state | ✅ **TRIPPED** (expected) | Samsung Pay/Secure Folder unavailable — irrelevant for Nuxel |
| Phase 0 device inventory | ⛔ **REQUIRED FIRST** | Must collect dmesg, getevent, partition list, firmware listing |
| U-Boot chainload (exynos9820) | ⛔ **NOT YET BUILT** | Requires network + toolchain |
| Nuxel kernel (linux-postmarketos-exynos9820) | ⛔ **NOT YET BUILT** | Requires cross-toolchain |
| Firmware blobs | ⛔ **NOT EXTRACTED** | Must pull from device vendor partition via TWRP |
| Flashable boot image (v1) | ⛔ **NOT YET BUILT** | Depends on kernel build |
| Flashable rootfs | ⛔ **NOT YET BUILT** | Depends on kernel + firmware |
| Physical flash to S10+ | ⛔ **BLOCKED** | All above gates must pass first |

**Bottom line:** read this guide in full before touching the device. Run Phase 0
immediately — it is safe, non-destructive, and unblocks everything else.

---

## Why the S10+ Has No `fastboot` (Critical)

Samsung Galaxy S10+ (Exynos) uses **Download Mode** (Odin/`heimdall`) and
**TWRP** for all flash operations. There is **no `fastboot` protocol** on this
device. If any tool or guide tells you to run `fastboot flash` on this device,
it is wrong.

| Operation | Tool |
|---|---|
| Flash kernel / U-Boot / rootfs | **TWRP** (`adb push` + `adb shell dd`) |
| ADB sideload a zip | **TWRP** Advanced → ADB Sideload |
| Full stock recovery / unbrick | **Download Mode** + `heimdall` or Odin |
| Verify device identity | `adb shell getprop ro.product.device` |

---

## Device Identity Reference

| Field | Value |
|---|---|
| Device | Samsung Galaxy S10+ |
| Model | SM-G975F (Exynos variant) |
| Codename | `beyond2lte` |
| SoC | Samsung Exynos 9820 (8 nm) |
| CPU | 2× Mongoose M4 + 2× Cortex-A75 + 4× Cortex-A55 |
| GPU | Mali-G76 MP12 (Bifrost → Panfrost) |
| RAM | 8 GB LPDDR4X |
| Storage | UFS 2.1 at `/dev/block/platform/13d60000.ufs` |
| Display | 6.4″ Dynamic AMOLED 3040×1440, HDR10+, DDIC S6E3HA9 |
| Touch | Samsung S6SY761 (`sec_ts`) @ I2C 0x48, firmware `y771` |
| WiFi/BT | Broadcom BCM4375 (Wi-Fi 6, BT 5.0) |
| Modem | Shannon LTE integrated (no 5G; Phase 1: WiFi only) |
| NFC | Samsung sec-nfc (S3FWRN5) @ I2C 0x27 |
| Audio | Cirrus CS47L93 codec + 2× CS35L40 amps |
| Boot model | **A-only** (no A/B slots) |
| Boot image | **Legacy header v1** (page 2048) |
| Flash method | **TWRP** + **Odin/heimdall** (**NO fastboot**) |
| Shipped kernel | Samsung 4.14.x downstream |
| Knox state | **Already tripped** (expected; bootloader already unlocked) |

---

## The S10+ Boot Chain

Understanding this is essential before flashing anything:

```
Samsung Boot ROM
    │
    ▼
S-Boot (Samsung's primary bootloader)
    │  ✓ Initializes CPU, DRAM, UFS 2.1, display
    │  ✗ CANNOT: accept mainline DTBs
    │  ✗ CANNOT: correctly pass kernel cmdline
    │  ✗ CANNOT: boot a mainline kernel directly
    │
    ▼ (we flash a custom U-Boot here to /boot via TWRP dd)
chiffathefox/u-boot (exynos9820 branch)
    │  Custom U-Boot secondary bootloader
    │  Builds with exynos9820_defconfig
    │  Boots mainline kernel via EFI protocol
    │
    ▼
linux-postmarketos-exynos9820
    │  Close-to-mainline kernel for Exynos 9820
    │  nuxel.device=s10plus on cmdline
    │
    ▼
Nuxel initramfs
    │  Probes UFS /dev/block/platform/13d60000.ufs/by-name/userdata
    │
    ▼
Nuxel rootfs → Phosh + GTK4 + PWA apps
```

**The U-Boot chainload is not optional.** S-Boot cannot boot a mainline kernel
directly. Every other Linux distro on Exynos 9820 (postmarketOS, etc.) uses
this same U-Boot path.

---

## Prerequisites

### Hardware

- Samsung Galaxy S10+ (SM-G975F, Exynos) — **already in TWRP** ✅
- USB-C data cable (not charge-only)
- Enough battery charge (> 60%)

### Host Software

```bash
# Linux (Debian/Ubuntu)
sudo apt install android-tools-adb android-tools-fastboot heimdall-flash \
    gcc-aarch64-linux-gnu gcc-10-aarch64-linux-gnu \
    git make python3 python3-pip \
    xz-utils unzip

# Verify adb works
adb version        # must be >= 1.0.41
heimdall version   # for Download Mode recovery

# macOS
brew install android-platform-tools heimdall
# Cross toolchain:
brew tap messense/macos-cross-toolchains
brew install aarch64-unknown-linux-gnu

# Verify
adb version
aarch64-unknown-linux-gnu-gcc --version
```

### Full Stock Firmware Backup (CRITICAL — do this before ANYTHING else)

```bash
# Device must be in TWRP with adb authorized

# Step 1: List all partitions
adb shell ls -la /dev/block/platform/13d60000.ufs/by-name/

# Step 2: Back up protected partitions (IMEI, MAC, Knox, calibration)
# These are irreplaceable. Back up EVERY partition you plan to touch.
adb shell "mkdir -p /sdcard/nuxel-backup"
for part in efs efsg persist param up_param steady keystorage; do
    echo "Backing up ${part}..."
    adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/${part} \
        of=/sdcard/nuxel-backup/${part}.img bs=4096 2>/dev/null && \
        echo '${part}: OK' || echo '${part}: SKIP (may not exist)'"
done

# Step 3: Back up boot and system partitions
adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/boot \
    of=/sdcard/nuxel-backup/boot-stock.img bs=4096"
adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/recovery \
    of=/sdcard/nuxel-backup/recovery-stock.img bs=4096"

# Step 4: Pull the backup to your host
mkdir -p ~/s10plus-backup
adb pull /sdcard/nuxel-backup ~/s10plus-backup/
echo "Backup complete. Store ~/s10plus-backup/ safely."

# Step 5: Extract boot header addresses from stock boot.img (needed for build)
python3 tools/read-boot-header-v1.py ~/s10plus-backup/boot-stock.img
# Save the kernel_addr, ramdisk_addr, tags_addr output
```

---

## Phase 0 — Device Inventory via TWRP (Non-Destructive, Do This First)

This is the **mandatory first step**. It collects the information needed to
build the correct kernel, firmware manifest, and boot images. It does not
modify the device.

```bash
# Verify device is in TWRP and adb works
adb devices
# Expected: <serial>    device

# Verify device identity
adb shell getprop ro.product.device    # must be: beyond2lte
adb shell getprop ro.product.name      # e.g.: beyond2ltexx (save this)
adb shell getprop ro.product.model     # e.g.: SM-G975F
adb shell getprop ro.bootloader        # save exact bootloader version
adb shell getprop ro.build.id          # save Android build ID

# Hardware identity
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|exynos' \
    > s10plus-props.txt

# Kernel cmdline (from stock boot)
adb shell cat /proc/cmdline

# Full dmesg — critical for driver identification
adb shell dmesg > s10plus-dmesg.txt
echo "Saved dmesg — search for: wifi, bluetooth, touch, nfc, audio, camera, sensor"

# Input devices — identifies touch controller, buttons
adb shell getevent -pl 2>/dev/null > s10plus-input-devices.txt

# Partition table — essential for flash targets
adb shell ls -la /dev/block/platform/13d60000.ufs/by-name/ \
    > s10plus-partitions.txt
adb shell cat /proc/partitions >> s10plus-partitions.txt

# Vendor firmware listing — needed for firmware/s10plus/manifest.yml
adb shell ls -laR /vendor/firmware/    > s10plus-vendor-firmware.txt
adb shell ls -laR /vendor/lib/modules/ > s10plus-vendor-modules.txt
adb shell ls -laR /vendor/etc/firmware/ > s10plus-vendor-etc-firmware.txt

# WiFi firmware filenames (critical — varies by subvariant)
adb shell ls /vendor/firmware/bcm4375* 2>/dev/null
adb shell ls /vendor/firmware/BCM4375* 2>/dev/null
adb shell ls /vendor/firmware/brcm*    2>/dev/null

# Touch firmware
adb shell ls /vendor/firmware/tsp_sec/ 2>/dev/null

# Audio card names
adb shell cat /proc/asound/cards 2>/dev/null
adb shell ls /sys/class/sound/  2>/dev/null

# System library listing (GPU userspace blobs)
adb shell ls /vendor/lib64/egl/   2>/dev/null
adb shell ls /system/lib64/       2>/dev/null | head -50

echo ""
echo "=== Phase 0 Complete ==="
echo "Fill the following in docs/s10plus-device-inventory.md:"
echo "  - Device variant (ro.product.name)"
echo "  - Bootloader version (ro.bootloader)"
echo "  - WiFi firmware filenames"
echo "  - BT HCD filename"
echo "  - Touch firmware path"
echo "  - Boot image kernel/ramdisk/tags addresses"
echo "  - Sensor hub component names (from dmesg)"
echo "  - Camera sensor names (from dmesg)"
```

---

## Phase 1 — Extract Firmware Blobs from Device

```bash
# Device still in TWRP

# Pull vendor firmware blobs into the Nuxel repo
NUXEL_DEVICE=s10plus bash firmware/s10plus/install-firmware.sh --twrp-pull
# This runs: adb pull /vendor/firmware → firmware/s10plus/blobs/vendor-firmware/
#             adb pull /vendor/lib/modules → firmware/s10plus/blobs/vendor-modules/
#             adb pull /vendor/etc/firmware → firmware/s10plus/blobs/vendor-etc-firmware/

# After pull, update firmware/s10plus/manifest.yml with real checksums:
sha256sum firmware/s10plus/blobs/vendor-firmware/bcm4375*.bin
sha256sum firmware/s10plus/blobs/vendor-firmware/BCM4375.hcd
sha256sum firmware/s10plus/blobs/vendor-firmware/tsp_sec/y771.fw
# Fill these into firmware/s10plus/manifest.yml

# Verify the manifest
NUXEL_DEVICE=s10plus bash firmware/s10plus/verify-firmware.sh
```

---

## Phase 2 — Install Build Toolchain

```bash
# Linux (Debian/Ubuntu)
sudo apt update
sudo apt install \
    gcc-10-aarch64-linux-gnu \
    binutils-aarch64-linux-gnu \
    bc bison flex libssl-dev libelf-dev \
    git make python3

# Verify cross compiler
aarch64-linux-gnu-gcc-10 --version
# Expected: aarch64-linux-gnu-gcc-10 (Ubuntu ...) 10.x.x

# Set environment
export CROSS_COMPILE=aarch64-linux-gnu-
export CC=aarch64-linux-gnu-gcc-10
export ARCH=arm64
```

---

## Phase 3 — Build U-Boot Chainloader

```bash
# Build chiffathefox/u-boot for Exynos 9820
bash boot/s10plus/uboot-chainload.sh

# This will:
# 1. Clone https://github.com/chiffathefox/u-boot -b exynos9820
# 2. Build with exynos9820_defconfig
# 3. Wrap u-boot.bin as a legacy v1 boot.img
# 4. Flash to /boot via TWRP dd (device must be in TWRP)

# If you want to build without flashing:
cd kernel/s10plus/.build/u-boot
make CC=aarch64-linux-gnu-gcc-10 \
     CROSS_COMPILE=aarch64-linux-gnu- \
     exynos9820_defconfig
make CC=aarch64-linux-gnu-gcc-10 \
     CROSS_COMPILE=aarch64-linux-gnu- \
     -j$(nproc)
ls -lh u-boot.bin     # should be present if build succeeded

# Wrap as boot image (legacy v1):
python3 boot/s10plus/pack-boot-v1.sh \
    --kernel kernel/s10plus/.build/u-boot/u-boot.bin \
    --ramdisk /dev/null \
    --cmdline "" \
    --output /tmp/u-boot-beyond2lte.img

# Flash manually:
adb push /tmp/u-boot-beyond2lte.img /tmp/
adb shell "dd if=/tmp/u-boot-beyond2lte.img \
    of=/dev/block/platform/13d60000.ufs/by-name/boot bs=4096"
echo "U-Boot flashed. Verify by rebooting to see if U-Boot output appears on console."
```

---

## Phase 4 — Build the Nuxel Kernel

```bash
# Clone and build linux-postmarketos-exynos9820
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone

# This clones: https://github.com/postmarketOS/linux-postmarketos
# Branch: exynos9820
# Applies Nuxel patches from kernel/s10plus/patches/
# Merges kernel/s10plus/defconfig on top of exynos9820_defconfig
# Builds Image.gz + exynos9820-beyond2lte.dtb

# Output locations:
# kernel/s10plus/.build/out/arch/arm64/boot/Image.gz
# kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dtb

# If build fails, check:
# 1. Cross-compiler: aarch64-linux-gnu-gcc-10 --version
# 2. defconfig symbols: some may not exist in this kernel tree
# 3. Nuxel patch: may need --skip-patch flag if 6.12-specific symbols don't compile

# Verify output:
ls -lh kernel/s10plus/.build/out/arch/arm64/boot/Image.gz
ls kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/
```

---

## Phase 5 — Build the Nuxel Rootfs

```bash
# Build the full Nuxel image set for S10+
NUXEL_DEVICE=s10plus bash images/s10plus/build.sh

# This produces in build/out/s10plus/:
#   u-boot-beyond2lte.img       — U-Boot wrapped as v1 boot.img
#   nuxel-beyond2lte-boot.img   — Nuxel kernel + initramfs as v1 boot.img
#   nuxel-beyond2lte-rootfs.img — ext4 rootfs for userdata partition
#   build-manifest.json         — build metadata

# Verify all outputs exist:
ls -lh build/out/s10plus/
cat build/out/s10plus/build-manifest.json
```

---

## Phase 6 — Flash to the Samsung Galaxy S10+

### Pre-flash safety checklist

- [ ] Device is in **TWRP** (not Download Mode, not Android)
- [ ] `adb devices` shows the device
- [ ] `adb shell getprop ro.product.device` returns `beyond2lte`
- [ ] Full stock backup is safely stored on host (see Prerequisites)
- [ ] Phase 0 inventory is complete
- [ ] Firmware blobs are extracted and checksums filled in
- [ ] Build outputs exist in `build/out/s10plus/`
- [ ] Battery > 60%
- [ ] DO NOT touch: `efs`, `efsg`, `persist`, `param`, `up_param`, `steady`,
      `keystorage`, `carrier`, `cp_debug`, `misc`

### Flash sequence (TWRP adb+dd)

```bash
# Step 1: Verify device identity (script does this automatically)
adb shell getprop ro.product.device    # must be: beyond2lte

# Step 2: Flash U-Boot to /boot
NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh \
    --device s10plus \
    --uboot build/out/s10plus/u-boot-beyond2lte.img

# Step 3: (Optional) Reboot to verify U-Boot loads before flashing rootfs
# adb shell twrp reboot
# If U-Boot loads: you'll see U-Boot console output (may need UART to see)
# If it doesn't boot: re-flash stock boot via heimdall (see Recovery section)

# Step 4: Re-enter TWRP
# Power off → Vol Up + Bixby + Power (hold until TWRP appears)
# OR: adb reboot recovery

# Step 5: Flash Nuxel kernel boot image
adb push build/out/s10plus/nuxel-beyond2lte-boot.img /tmp/
adb shell "dd if=/tmp/nuxel-beyond2lte-boot.img \
    of=/dev/block/platform/13d60000.ufs/by-name/boot bs=4096"

# Step 6: Flash Nuxel rootfs to userdata
# WARNING: This will erase all Android data on userdata
adb push build/out/s10plus/nuxel-beyond2lte-rootfs.img /tmp/
adb shell "dd if=/tmp/nuxel-beyond2lte-rootfs.img \
    of=/dev/block/platform/13d60000.ufs/by-name/userdata bs=4096"

# Step 7: Reboot
adb shell twrp reboot

# Using the flash script (does all of the above with safety checks):
NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh \
    --device s10plus \
    --uboot build/out/s10plus/u-boot-beyond2lte.img \
    --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img \
    --rootfs-partition userdata
```

### Alternative: TWRP ADB Sideload

```bash
# In TWRP: Advanced → ADB Sideload → Swipe to start sideload

# Then on host:
adb sideload nuxel-beyond2lte.zip
# Note: ZIP creation not yet implemented. Use dd method above for now.
```

---

## Recovery — How to Restore Stock Android

If anything goes wrong, you can always restore via **Download Mode + heimdall**
or Odin. Download Mode is always accessible regardless of what's on the boot
partition.

### Enter Download Mode

**Method 1 (device on):** Hold **Vol Down + Bixby + Power** simultaneously
until the Download Mode screen appears.

**Method 2 (device off):** Hold **Vol Down + Bixby + Power** from off.

**Method 3 (adb, if in TWRP):** `adb reboot download`

### Get Samsung Stock Firmware

Download the matching SM-G975F firmware from one of:
- **SamFw:** https://samfw.com (search SM-G975F, match your region/bootloader)
- **SamMobile:** https://www.sammobile.com/samsung/galaxy-s10-plus/firmware/
- **Samsung OSRC:** https://opensource.samsung.com (for kernel only)

The firmware comes as four files:
- `BL_*.tar.md5` — Bootloader
- `AP_*.tar.md5` — Main system firmware (largest file)
- `CP_*.tar.md5` — Modem/radio
- `CSC_*.tar.md5` — Country-specific code

**CRITICAL:** Match the firmware to the exact bootloader revision currently on
your device. Mismatched bootloader firmware can cause a boot loop.

### Restore via heimdall

```bash
# Install heimdall
sudo apt install heimdall-flash         # Linux
brew install heimdall                   # macOS

# Verify heimdall detects the device in Download Mode
heimdall detect

# Flash all four partitions
heimdall flash \
    --BL BL_G975FXXS_*.tar.md5 \
    --AP AP_G975FXXS_*.tar.md5 \
    --CP CP_G975FXXS_*.tar.md5 \
    --CSC CSC_G975FXXS_*.tar.md5

# heimdall will reboot the device automatically after flashing
# Expected: device reboots into stock Android (may show factory reset)
```

### Restore via Odin (Windows only)

1. Download Odin 3.14.1 from official Samsung / XDA mirror.
2. Open Odin → Connect device in Download Mode.
3. Load: BL → AP → CP → CSC into the corresponding slots.
4. Click **Start**. Odin will flash and reboot automatically.

### Partial restore (boot only — fastest revert)

If only the boot partition is broken (most common scenario):

```bash
# In Download Mode:
heimdall flash --BOOT ~/s10plus-backup/boot-stock.img
# OR: heimdall flash --BOOT boot-stock.img from the AP firmware
```

---

## Phase-by-Phase Bring-Up Plan

| Phase | Goal | Entry Criteria | Exit Criteria |
|---|---|---|---|
| 0 | Device inventory | Device in TWRP + adb | All unknowns in `docs/s10plus-device-inventory.md` filled |
| 1 | U-Boot + kernel | Phase 0 done + toolchain | U-Boot boots; kernel boots to debug shell; `nuxel.device=s10plus` on console |
| 2 | Display + touch | Phase 1 done | Phosh launches at 3040×1440; sec_ts touch responds |
| 3 | WiFi/BT | Phase 2 done + BCM4375 firmware | `wlan0` up; `bluetoothctl` sees BCM4375 |
| 4 | GPU | Phase 3 done | Panfrost GLES or llvmpipe fallback in Phosh |
| 5 | Audio | Phase 4 done + CS47L93 firmware | Speaker output via PipeWire UCM |
| 6 | Userspace hardening | Phase 5 done | AppArmor, nftables, hardened_malloc active |
| 7 | Modem/camera | Phase 6 done | Stretch goal; Shannon LTE interface research |

---

## Driver Status for S10+

| Subsystem | Status | Notes |
|---|---|---|
| GPU (Panfrost/Mali-G76) | ✅ Mainline | `CONFIG_DRM_PANFROST`; Mesa Bifrost support |
| Display (S6E3HA9 panel) | 🚧 pmOS port | In linux-postmarketos-exynos9820 |
| Touch (S6SY761 sec_ts) | 🚧 Downstream/pmOS | sec_ts driver |
| WiFi (BCM4375 brcmfmac) | 🚧 Needs firmware | Base driver mainline; firmware from device |
| Bluetooth (BCM4375 BT 5.0) | 🚧 Needs .hcd | btbcm mainline; .hcd from device |
| Modem (Shannon LTE) | ❌ Not MM-ready | Phase 7 stretch; WiFi only in Phase 1–6 |
| Audio (CS47L93 + CS35L40) | 🚧 Downstream | MADERA ASoC; UCM from device |
| NFC (sec-nfc S3FWRN5) | 🚧 Downstream | Phase 6+ |
| Sensors | ⬜ Unknown | Collect from device in Phase 0 |
| Camera | ⬜ Unknown | Phase 7 stretch |
| USB (dwc3) | ✅ Mainline | Standard; no fastboot gadget needed |
| UFS 2.1 | ✅ Mainline | ufshcd |

---

## Key URLs

| Resource | URL |
|---|---|
| postmarketOS Exynos 9820 | https://wiki.postmarketos.org/wiki/Samsung_Exynos_9820_(samsung-exynos9820) |
| postmarketOS S10+ page | https://wiki.postmarketos.org/wiki/Samsung_Galaxy_S10%2B_(samsung-beyond2lte) |
| U-Boot fork (exynos9820) | https://github.com/chiffathefox/u-boot (branch: exynos9820) |
| TWRP for beyond2lte | https://twrp.me/samsung/samsunggalaxys10plus.html |
| Samsung OSRC (SM-G975F kernel) | https://opensource.samsung.com |

---

## FAQ

**Q: Will flashing Nuxel permanently brick my S10+?**
No. The Download Mode (Vol Down + Bixby + Power) is always accessible and is
independent of the boot partition. You can always restore via heimdall.

**Q: My Knox fuse is already tripped. Is that a problem?**
No. For Nuxel, Knox being tripped is actually ideal. The bootloader is already
unlocked, TWRP is already installed, and we don't need or want Knox, Samsung
Pay, or Secure Folder. This is the perfect state.

**Q: Can I still get back to stock Android?**
Yes, completely. Use Download Mode + heimdall to flash all four Samsung firmware
partitions (BL/AP/CP/CSC). Android will boot normally (Knox still tripped, but
everything else works).

**Q: Why does Nuxel use U-Boot instead of flashing the kernel directly?**
Because Samsung's S-Boot ignores the kernel cmdline and cannot accept mainline
device trees. Every mainline Linux port on Exynos 9820 (postmarketOS, etc.) uses
this exact U-Boot chainload. It is the only proven path.

**Q: Will I have cellular service in Phase 1?**
No. The Shannon LTE modem is not ModemManager-ready. Phase 1–6 target WiFi
only. Cellular is a Phase 7 stretch goal.

**Q: What about `fastboot`? The internet says to use it.**
Not on this device. The S10+ (Exynos) has no fastboot protocol. Instructions
for Snapdragon Samsung devices (like some Galaxy S21 US models) are not
applicable here. Use TWRP and heimdall.

---

*Build the bunker first. Add the rave lights later.*
*— Nuxel v0.2.0*
