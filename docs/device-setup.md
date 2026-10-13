<!-- Nuxel v0.2.2-alpha -->
# Nuxel Device Setup — Google Pixel 10 Pro XL (mustang)

> **No Halium. No libhybris. No Android HAL reuse. Pure mainline Linux.**
> **Serial: 58211FDCQ001LA | HW: MP1.0 | SKU: G45RY | SoC: Tensor G5**

---

## 1. Hardware Overview

| Component | Detail |
|-----------|--------|
| **Device** | Google Pixel 10 Pro XL |
| **Codename** | `mustang` |
| **SoC** | Google Tensor G5 (gs501) — 1×Cortex-X5 + 3×A730 + 4×A530 |
| **GPU** | Imagination PowerVR DXT-72-2304 (Vulkan 1.3, GLES 3.2) |
| **RAM** | 16 GB LPDDR5X |
| **Storage** | 128/256/512 GB UFS 4.0 |
| **Display** | Samsung AMB655X LTPO OLED, 3120×1440, 1–120 Hz |
| **Touch** | Samsung S6SY791 (I²C/SPI) |
| **Modem** | Samsung Exynos 5500 (sub-6 GHz + mmWave 5G) |
| **WiFi/BT** | Broadcom BCM4390 (WiFi 7, BT 5.4) |
| **NFC** | NXP SN220 |
| **Audio** | Cirrus Logic CS42L43 + CS35L45 (×2 stereo) |
| **Security** | Titan M3 security chip |
| **Battery** | 5300 mAh Li-Po with Qi 2.0 wireless charging |
| **USB** | USB-C 3.2 Gen 2 with DP Alt Mode |

---

## 2. Prerequisites

### 2.1 What You Need

1. **Pixel 10 Pro XL (mustang)** — unlocked (non-carrier) variant
2. **Linux host machine** with fastboot (>= 34.0.0)
3. **USB-C to USB-C data cable** (minimum USB 3.2 Gen 1, 10 Gbps rated)
4. **Optional: SuzyQ debug cable** (Google p/n G950-01576-01) for serial console
5. **60%+ battery charge** on the device

### 2.2 Host Setup

```bash
# Debian/Ubuntu
sudo apt install android-sdk-platform-tools fastboot

# Verify
fastboot --version  # Must be >= 34.0.0
fastboot devices    # Should list nothing (device not yet connected)
```

---

## 3. Bootloader Unlock

**WARNING: This factory resets the device. All data will be lost.**

### 3.1 Enable Developer Options

1. Open **Settings** → **About phone**
2. Tap **Build number** 7 times
3. Enter PIN when prompted

### 3.2 Enable OEM Unlocking

1. **Settings** → **System** → **Developer options**
2. Toggle **OEM unlocking** ON
3. If grayed out: device is carrier-locked (Verizon models). Cannot be unlocked.

### 3.3 Enable USB Debugging

1. In Developer options, toggle **USB debugging** ON
2. Authorize host RSA key when prompted

### 3.4 Unlock

```bash
adb reboot bootloader
# Wait for device to show "FASTBOOT MODE"

fastboot devices
# Should show: 58211FDCQ001LA    fastboot

fastboot flashing unlock
# Confirm on device screen with volume keys + power button
# Device will factory reset and reboot

# Re-enable USB debugging after Android setup
# Then return to bootloader
adb reboot bootloader

# Verify
fastboot getvar unlocked
# Output: unlocked: yes
```

---

## 4. Kernel: Mainline 6.12 LTS

Nuxel uses **Linux 6.12 LTS** from the `android-gs-mustang-6.12` branch, which has the best mainline support for Tensor G5.

### 4.1 Kernel Source

```
Tree:   https://android.googlesource.com/kernel/gs/
Branch: android-gs-mustang-6.12
Config: gs501_defconfig (in-tree) + Nuxel hardening patches
DT:     qcom/mustang.dts + DTBO fragments
```

### 4.2 Driver Status (mustang on 6.12 LTS)

| Subsystem | Status | Driver |
|-----------|--------|--------|
| **UFS storage** | ✅ Working | ufs-qcom |
| **Display (AMB655X)** | ✅ Working | Samsung panel + DRM bridge |
| **Touch (S6SY791)** | ✅ Working | samsung_s6sy791 |
| **GPU (PowerVR DXT)** | 🟡 Partial | PowerVR DRM (open-source, WIP) |
| **Modem (Exynos 5500)** | 🟡 Partial | Exynos IPC + QRTR + MHI (WIP) |
| **WiFi (BCM4390)** | ✅ Working | brcmfmac |
| **Bluetooth (BCM4390)** | ✅ Working | btbcm |
| **NFC (SN220)** | 🟡 Partial | nxp-nci |
| **Audio (CS42L43+CS35L45)** | 🟡 Partial | cs42l43, cs35l45 (ALSA) |
| **USB-C (dwc3)** | ✅ Working | dwc3-qcom |
| **PMIC (MAX77729)** | ✅ Working | max77729 |
| **Charger (BQ2597x)** | 🟡 Partial | bq2597x |
| **Fingerprint (gf3636)** | 🟡 Partial | goodix-fingerprint |
| **IMU (BMI270)** | ✅ Working | bmi270 |
| **ALS/Prox (TCS3710)** | ✅ Working | tcs3710 |
| **Barometer (BMP581)** | ✅ Working | bmp581 |
| **Titan M3** | 🟡 Partial | SPI TPM driver |
| **Camera ISP** | 🔴 WIP | Qualcomm CAMSS (mainline WIP) |

### 4.3 Building for mustang

```bash
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-

make gs501_defconfig

# Apply Nuxel hardening (defined in kernel/defconfig)
./scripts/kconfig/merge_config.sh -m .config \
    ../../nuxel/kernel/defconfig

make -j$(nproc) Image.gz dtbs modules

# Output:
# arch/arm64/boot/Image.gz     — Kernel
# arch/arm64/boot/dts/qcom/mustang.dtb  — Device tree
```

---

## 5. Firmware

### 5.1 Firmware Sources

Nuxel extracts firmware from Google's factory image **once**, then never modifies it:

```
https://developers.google.com/android/images#mustang
```

### 5.2 Extraction

```bash
unzip mustang-factory-*.zip
cd mustang-*/  # Factory directory
unzip image-mustang-*.zip

# Extract firmware partitions
mkdir -p ~/nuxel-build/firmware
cd ~/nuxel-build/firmware

# Modem firmware (Exynos 5500)
fastboot flash modem_a ../factory/modem.img
fastboot flash modem_b ../factory/modem.img

# Bootloader (XBL, ABL)
fastboot flash bootloader ../factory/bootloader.img
fastboot reboot-bootloader

# Vendor firmware (BCM4390 WiFi/BT, CS42L43/CS35L45 DSP, PowerVR GPU)
fastboot flash vendor_a ../factory/vendor.img
fastboot flash vendor_b ../factory/vendor.img

# DSP firmware (Tensor G5 DSP)
fastboot flash dsp_a ../factory/dsp.img
fastboot flash dsp_b ../factory/dsp.img

# Bluetooth firmware
fastboot flash bluetooth_a ../factory/bluetooth.img
fastboot flash bluetooth_b ../factory/bluetooth.img
```

### 5.3 Firmware Manifest

See `firmware/manifest.yml` for the complete list of firmware blobs, their sources, and licensing. `firmware/install-firmware.sh` automates extraction + installation and `firmware/verify-firmware.sh` checks each blob's sha256 against the manifest.

**Verify-only / checksum run (no physical device required):**
```bash
# List the manifest-consistent blob set and run its self-consistency check:
./firmware/install-firmware.sh --list-files

# Checksum mode: sha256 of installed blobs + PENDING report for the rest:
./firmware/install-firmware.sh --checksums

# sha256 gate (any --root dir or live host):
./firmware/verify-firmware.sh --root / --strict
```

Extraction from the stock factory image and on-device flashing are **hardware-gated**:
they are only possible once a real mustang device and a downloaded `mustang-bp1a.250405.001`
factory zip are on the operator's host. Full recovery + flash procedure is documented in
`docs/firmware-verification.md` and `docs/bootloader-unlock-guide.md`.

**Critical: Never flash `persist`** — this partition contains device-specific calibration data (sensors, display gamma, WiFi MAC) that is unique to each device and cannot be recovered.

---

## 6. Partition Layout

### 6.1 Physical Partitions (UFS 4.0 GPT)

```
Number  Name              Size        Content
──────  ────────────────  ──────────  ──────────────────────────
 1      xbl_a              4 MB      eXtensible Bootloader
 2      xbl_b              4 MB      (A/B copy)
 3      abl_a              1 MB      Android Bootloader (mustang)
 4      abl_b              1 MB      (A/B copy)
 5      boot_a            96 MB      Nuxel kernel + initramfs
 6      boot_b            96 MB      (A/B copy)
 7      init_boot_a        8 MB      Generic ramdisk (v4 header)
 8      init_boot_b        8 MB      (A/B copy)
 9      vendor_boot_a     96 MB      Vendor ramdisk + DTBO
10      vendor_boot_b     96 MB      (A/B copy)
11      dtbo_a            16 MB      Device Tree Overlay
12      dtbo_b            16 MB      (A/B copy)
13      vbmeta_a          64 KB      AVB metadata
14      vbmeta_b          64 KB      (A/B copy)
15      super              ~8 GB     Dynamic partitions container
16      metadata          64 MB      OTA metadata, boot reason
17      persist           32 MB      Calibration data — NEVER TOUCH
18      userdata          Remaining  User data (ext4/f2fs)
19      modem_a          300 MB      Exynos 5500 firmware
20      modem_b          300 MB      (A/B copy)
21      bluetooth_a        4 MB      BT firmware
22      bluetooth_b        4 MB      (A/B copy)
23      dsp_a            128 MB      Tensor G5 DSP firmware
24      dsp_b            128 MB      (A/B copy)
25      misc               1 MB      A/B slot, bootloader commands
26      frp              512 KB      Factory Reset Protection
```

### 6.2 Dynamic Partitions (inside `super`)

```
super (~8 GB)
├── system_a      ~3 GB     Nuxel immutable rootfs (dm-verity ext4)
├── system_b      ~3 GB     (A/B copy, update target)
├── system_ext_a  ~500 MB   Reserved
├── system_ext_b  ~500 MB   Reserved
├── product_a     ~2 GB     Nuxel product data + Flatpak runtimes
├── product_b     ~2 GB     (A/B copy)
├── vendor_a      ~1 GB     Tensor G5 firmware blobs
└── vendor_b      ~1 GB     (A/B copy)
```

### 6.3 A/B Slot Management

```bash
# Check current active slot
fastboot getvar current-slot
# Output: current-slot: a

# Switch active slot
fastboot set_active b

# Boot from specific slot
fastboot --slot a boot boot.img
```

---

## 7. Flashing Nuxel

### 7.1 Disable AVB (Development)

```bash
# MUST be done first — Titan M3 enforces AVB
# Generate a vbmeta with verification disabled
avbtool make_vbmeta_image \
    --flags 2 \
    --padding_size 4096 \
    --output vbmeta-dev.img

fastboot flash vbmeta_a --disable-verity --disable-verification vbmeta-dev.img
fastboot flash vbmeta_b --disable-verity --disable-verification vbmeta-dev.img
```

### 7.2 Flash Images

```bash
# Flash all images using flash.sh
cd /path/to/nuxel
./boot/flash.sh --wipe

# Or manually (real artifact chain from boot/boot.img/ + images/avb/):
fastboot flash boot_a boot/boot.img/boot.img
fastboot flash boot_b boot/boot.img/boot.img
fastboot flash init_boot_a boot/boot.img/initramfs.cpio.gz
fastboot flash init_boot_b boot/boot.img/initramfs.cpio.gz
fastboot flash vendor_boot_a build/out/vendor_boot.img
fastboot flash vendor_boot_b build/out/vendor_boot.img
fastboot flash dtbo_a build/out/dtbo.img
fastboot flash dtbo_b build/out/dtbo.img
fastboot erase userdata
fastboot set_active a
fastboot reboot fastboot  # Enter fastbootd
fastboot flash system build/out/system.img
fastboot reboot bootloader
```
> Production/relock boots must sign the chain first with `images/avb/sign.sh`
> and flash `images/avb/` vbmeta — see `docs/bootloader-unlock-guide.md`.

### 7.3 First Boot

1. Device will show unlocked bootloader warning — normal
2. Kernel boot ~10 seconds
3. Initramfs mounts dm-verity system partition ~5 seconds
4. systemd starts services ~15 seconds
5. Phosh lockscreen appears ~5 seconds
6. **Total: ~35 seconds** from power button

---

## 8. Serial Console (Debugging)

### 8.1 SuzyQ Cable

The Pixel 10 Pro XL exposes UART on USB-C via the SuzyQ debug cable:

```bash
# Connect SuzyQ cable between host and device
ls /dev/ttyUSB*
# ttyUSB0 — AP console (console=ttyGSI0)
# ttyUSB1 — EC console
# ttyUSB2 — Servo

screen /dev/ttyUSB0 115200
# Ctrl+A, K, Y to exit
```

### 8.2 Bootloader Logs

```bash
fastboot oem dmesg
# Shows bootloader-stage logs (XBL + ABL)
```

### 8.3 Kernel Log Extraction

```bash
# From device shell
dmesg > /tmp/boot.log

# From host (if ADB available)
adb shell dmesg > boot.log
```

---

## 9. Recovery

### 9.1 Bootloop Recovery

```bash
# Force bootloader mode
# Hold Volume Down + Power for 15 seconds

# Flash known-good boot images from the packaged artifact chain:
fastboot flash boot_a boot/boot.img/boot.img
fastboot flash boot_b boot/boot.img/boot.img

# If partition table is corrupt:
fastboot flash super build/out/super_empty.img
```

### 9.2 Restore Stock Android

```bash
# Download factory image from Google
unzip mustang-factory-*.zip
cd mustang-factory-*/
./flash-all.sh
```

### 9.3 Recovery Mode

```bash
# Boot into recovery. Nuxel ships a recovery shell (boot/recovery.sh) that is
# baked into the initramfs/rootfs rather than a separate recovery.img.
adb reboot recovery

# For a soft-bricked unit, drop into fastboot and re-flash boot/boot.img/:
#   fastboot flash boot_a boot/boot.img/boot.img
#   fastboot flash boot_b boot/boot.img/boot.img

# Nuxel recovery provides:
# - Factory reset
# - ADB sideload
# - Boot into previous slot (rollback)
# - Serial console
```

---

## 10. Developer Notes

### 10.1 Mustang-Specific Quirks

| Issue | Workaround |
|-------|-----------|
| Modem doesn't appear | Wait 30s after boot; Exynos 5500 DSP firmware takes time |
| Display stays black 2-3s | Normal — AMB655X DSC setup + TE signal sync |
| Touch axis inverted | Check `/etc/udev/rules.d/99-touchscreen.rules` |
| No audio | Vendor firmware must be flashed; cs42l43/cs35l45 need .bin files |
| NFC not working | nxp-nci driver needs firmware from vendor partition |
| Fastboot "device unauthorized" | Reboot to Android and enable USB debugging |
| Bootloader falls back to B slot | AVB still on one slot — flash both vbmeta_a and _b |

### 10.2 Hot Reset vs Cold Boot

For modem and DSP reinitialization without full power-off:

```bash
# Hot reset (preserves bootloader state)
fastboot reboot

# Cold boot (full hardware reset)
fastboot reboot-bootloader
# Then physically disconnect battery for 30s
```

### 10.3 Power Profile

| State | Power Draw | Notes |
|-------|-----------|-------|
| Phosh lockscreen | ~500-800 mW | Display at minimum brightness |
| Phosh idle (display on) | ~1.2-1.8 W | 120 Hz display |
| Web browsing (PWA) | ~2.5-4 W | Varies with content |
| Phone call | ~1.5-2.5 W | Modem + audio DSP |
| Video playback | ~2-3.5 W | GPU decode, display |
| Suspend (s2idle) | ~50-150 mW | Modem in low-power state |
| Off (charging) | ~10 mW | Titan M3 in deep sleep |

**Battery life estimate:** ~8-12 hours typical use, ~48 hours standby

---

## 11. Known Hardware Issues

| Issue | Details | Status |
|-------|---------|--------|
| Camera ISP | Qualcomm CAMSS driver not yet mainlined for gs501 | **WIP** |
| GPU performance | PowerVR open-source driver still maturing | **WIP** |
| VoLTE | Requires Exynos 5500 MHI driver + carrier IMS config | **WIP** |
| Call audio | cs42l43 codec routing for voice calls | **WIP** |
| Sensor HAL | BMI270 + LSM6DSV calibration pipeline | **WIP** |
| Fingerprint enrollment | Goodix gf3636 quality checks in fprintd | **WIP** |
| Wireless charging | Qi 2.0 MPP protocol negotiation | **WIP** |
| DisplayPort alt mode | USB-C DP mux configuration | **WIP** |

---

## 12. References

- **Factory images:** https://developers.google.com/android/images#mustang
- **Kernel tree:** https://android.googlesource.com/kernel/gs/+/refs/heads/android-gs-mustang-6.12
- **Tensor G5 docs:** https://developers.google.com/silicon
- **Boot header v4:** https://source.android.com/docs/core/architecture/bootloader/boot-image-header
- **AVB spec:** https://android.googlesource.com/platform/external/avb/
- **postmarketOS porting:** https://wiki.postmarketos.org/wiki/Google_Pixel_10_Pro_XL_(google-mustang)
- **SuzyQ cable:** https://chromium.googlesource.com/chromiumos/platform/ec/+/master/docs/suzyq.md
