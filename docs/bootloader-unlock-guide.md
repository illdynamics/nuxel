# Bootloader Unlock Guide for Google Pixel 10 Pro XL (mustang)

## Device-Specific Information

| Field               | Value                                      |
|---------------------|--------------------------------------------|
| **Device**          | Google Pixel 10 Pro XL                     |
| **Codename**        | mustang                                    |
| **Serial Number**   | 58211FDCQ001LA                             |
| **Hardware Version**| MP1.0                                      |
| **Hardware SKU**    | G45RY                                      |
| **SoC**             | Google Tensor G5                           |
| **Security Chip**   | Titan M3                                   |
| **Bootloader**      | Google ABL (mustang variant)               |
| **AVB**             | AVB 2.0 with Titan M3 chain of trust       |

---

## Prerequisites

### 1. Check Carrier Lock Status
**CRITICAL:** If this device is carrier-locked (especially Verizon or AT&T), the bootloader **cannot** be unlocked. Google Pixel devices sold through carriers may have permanent OEM Unlock restrictions.

To check: Go to **Settings → About phone → SIM status**. If it shows "Network locked" or no option for "OEM unlocking" in Developer Options, the device is carrier-locked and cannot be unlocked.

### 2. Enable Developer Options
1. Open **Settings** → **About phone**
2. Scroll to **Build number**
3. Tap **Build number** seven (7) times rapidly
4. Enter your PIN/password when prompted
5. You'll see: "You are now a developer!"

### 3. Enable OEM Unlocking
1. Open **Settings** → **System** → **Developer options**
2. Toggle **OEM unlocking** ON
3. **IMPORTANT:** If this toggle is grayed out or missing, the device is carrier-locked or the Boot ROM/Titan M3 has restrictions. You CANNOT unlock this bootloader.
4. Confirm the warning dialog about security

### 4. Enable USB Debugging
1. In the same Developer options menu
2. Toggle **USB debugging** ON
3. Confirm the RSA key fingerprint when connecting USB

---

## Bootloader Unlock Procedure

### Step 1: Install Platform Tools

**On Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install android-sdk-platform-tools
fastboot --version  # Must be >= 34.0.0
```

**On macOS:**
```bash
brew install android-platform-tools
```

**On Windows:**
Download from https://developer.android.com/studio/releases/platform-tools

### Step 2: Verify Device Connection
```bash
# Check adb connection while in Android
adb devices
# Should show: 58211FDCQ001LA    device

# Reboot to bootloader
adb reboot bootloader
# OR: Power off, then hold Volume Down + Power
```

### Step 3: Verify Fastboot Mode
```bash
fastboot devices
# Expected: 58211FDCQ001LA    fastboot

# Check device info
fastboot getvar product
# Expected: mustang

fastboot getvar serial
# Expected: 58211FDCQ001LA

fastboot getvar unlocked
# Expected: no (if still locked)

fastboot getvar secure
# Expected: yes (Titan M3 is active)
```

### Step 4: Unlock the Bootloader

**⚠️ WARNING: THIS WILL FACTORY RESET THE DEVICE IMMEDIATELY**

```bash
fastboot flashing unlock
```

The device will:
1. Display a warning screen
2. Ask you to confirm using volume keys (scroll to "UNLOCK THE BOOTLOADER")
3. Press Power to confirm
4. The device will automatically factory reset and reboot

**After reboot:**
- The device will show a yellow warning: "The bootloader is unlocked and software integrity cannot be guaranteed"
- Skip through Android setup (do NOT sign into a Google account yet)
- Re-enable Developer Options and USB Debugging

### Step 5: Verify Unlock
```bash
# Reboot to bootloader
adb reboot bootloader

# Check unlock status
fastboot getvar unlocked
# Expected: yes

# Check device is still our serial
fastboot getvar serial
# Expected: 58211FDCQ001LA
```

### Step 6: Unlock Critical Partitions (Optional)

Only needed if you need to flash bootloader or radio partitions:
```bash
fastboot flashing unlock_critical
```
This also wipes the device and requires on-screen confirmation.

### Step 7: Disable AVB Verification

Flash a custom vbmeta with verification disabled:
```bash
# Generate vbmeta with disabled verification
# Using avbtool:
avbtool make_vbmeta_image --flags 2 --padding_size 4096 --output vbmeta.img

# OR using Python:
python3 -c "
import struct
with open('vbmeta.img', 'wb') as f:
    f.write(b'AVB0')
    f.write(struct.pack('>I', 1))
    f.write(struct.pack('>I', 0))
    f.write(b'\x00' * 32)
    f.write(b'\x00' * 32)
    f.write(struct.pack('>I', 65536))
    f.write(struct.pack('>I', 2))  # flags: disable_verity | disable_verification
    f.write(b'\x00' * 64)
    f.truncate(65536)
"

# Flash to both slots
fastboot flash vbmeta_a --disable-verity --disable-verification vbmeta.img
fastboot flash vbmeta_b --disable-verity --disable-verification vbmeta.img
```

> **Real tooling.** For a signed/relockable chain use `images/avb/sign.sh`
> (see `images/avb/mustang-avb.conf`) instead of hand-crafting vbmeta, and
> drive the whole flash from `boot/flash.sh` (consumes `boot/boot.img/` +
> `boot/initramfs`). Recovery shell is `boot/recovery.sh`.

---

## Flashing Nuxel

After bootloader is unlocked and AVB is disabled:

### 1. Flash Boot Images
```bash
# Flash boot.img (kernel + initramfs)
fastboot flash boot_a boot.img
fastboot flash boot_b boot.img

# Flash vendor_boot.img (vendor ramdisk + DTBO)
fastboot flash vendor_boot_a vendor_boot.img
fastboot flash vendor_boot_b vendor_boot.img

# Flash init_boot.img (generic ramdisk - required on mustang)
fastboot flash init_boot_a init_boot.img
fastboot flash init_boot_b init_boot.img

# Flash DTBO
fastboot flash dtbo_a dtbo.img
fastboot flash dtbo_b dtbo.img
```

### 2. Flash System
```bash
# Reboot to fastbootd (userspace fastboot for dynamic partitions)
fastboot reboot fastboot

# Flash system
fastboot flash system system.img

# Reboot to bootloader
fastboot reboot bootloader
```

### 3. Set Active Slot and Boot
```bash
fastboot set_active a
fastboot reboot
```

---

## Titan M3 Security Considerations

The Pixel 10 Pro XL uses the **Titan M3** security chip, which is more advanced than earlier Titan chips:

| Feature                  | Status after unlock                           |
|--------------------------|-----------------------------------------------|
| **Verified Boot (AVB)**  | Disabled via custom vbmeta                    |
| **Titan M3 attestation** | Still active - hardware attestation continues |
| **Secure Boot**          | Still active                                 |
| **Keymaster**            | Still works (can store keys)                  |
| **StrongBox**            | Still works                                   |
| **Factory Reset Protection** | Bypassed (no OS to check against)        |

**What unlocking does NOT disable:**
- Titan M3 hardware root of trust
- Cryptographic operations (Keymaster HAL)
- Disk encryption (when implemented)
- Hardware-backed attestation

**What unlocking does disable:**
- AVB verification of boot images
- The "locked bootloader" security guarantee
- Verified Boot chain (yellow warning on every boot)

---

## Recovery Procedures (battle-tested mustang path)

> This is the canonical, repeatable recovery flow for **58211FDCQ001LA /
> MP1.0 / G45RY**. Re-flashing Nuxel kernel + initramfs, or de-bricking a
> soft-bricked unit, always follows the same fastboot sequence. Cross-referenced
> from `docs/hardware-bringup-prep.md` §8.2.

### 0. Fastboot preflight (always)

```bash
fastboot devices                              # => 58211FDCQ001LA  fastboot
fastboot getvar product                       # => mustang
fastboot getvar serial                        # => 58211FDCQ001LA
fastboot getvar current-slot                  # => a or b
fastboot getvar unlocked                      # => yes (see unlock steps above otherwise)
```

If `fastboot devices` is empty, see **"If fastboot doesn't see device"** below
before proceeding.

### 1. Flash Nuxel boot + vendor_boot + dtbo (both slots)

```bash
# Recover / update the kernel + initramfs artifact (see boot/README.md):
fastboot flash boot_a boot.img
fastboot flash boot_b boot.img

# Vendor ramdisk + device-tree overlays (required for display/touch/audio):
fastboot flash vendor_boot_a vendor_boot.img
fastboot flash vendor_boot_b vendor_boot.img
fastboot flash dtbo_a dtbo.img
fastboot flash dtbo_b dtbo.img
```

### 2. Force AVB off (sign-free boot on Tensor G5 / Titan M3)

```bash
fastboot flash vbmeta_a --disable-verity --disable-verification vbmeta.img
fastboot flash vbmeta_b --disable-verity --disable-verification vbmeta.img
fastboot set_active a
fastboot reboot
```

### 3. Verify first boot

```bash
adb wait-for-device shell getprop ro.boot.slot                # a
adb shell dmesg | grep -iE "brcmfmac|exynos|pvr"              # interfaces vs firmware
```

### If the device won't boot after flashing

```bash
# 1) Force bootloader mode: hold Volume Down + Power for 15 seconds.
# 2) Re-run preflight (step 0). If `product` still returns mustang and the
#    device enumerates, re-flash boot (step 1) — a dropped/truncated transfer
#    is the most common cause.
# 3) Restore stock factory image (last resort, wipes device):
wget https://dl.google.com/dl/android/aosp/mustang-bp1a.250405.001-factory-<xxxxx>.zip
unzip mustang-bp1a.250405.001-factory-<xxxxx>.zip
cd mustang-bp1a.250405.001-factory-<xxxxx>/
./flash-all.sh
```

### If you get a bootloop

```bash
# Try the other slot first (A/B make a broken slot recoverable):
fastboot set_active b && fastboot reboot

# Not recovered? Re-seal AVB off on whichever vbmeta you touched:
fastboot flash vbmeta_a --disable-verity --disable-verification vbmeta.img
fastboot flash vbmeta_b --disable-verity --disable-verification vbmeta.img
fastboot reboot

# Still looping? Re-extract & re-flash the firmware blobs and boot.img
# (see docs/hardware-bringup-prep.md §8.1), then retest.
```

### If fastboot doesn't see device

1. Check the cable is a **data** cable, not charge-only.
2. Try a different USB port; prefer USB 2.0 if USB 3.x is flaky.
3. Verify USB debugging was enabled **before** entering bootloader and the host
   RSA key was authorized over ADB.
4. Ensure the device is not in "charging only" USB mode.
5. Linux: `sudo fastboot` or install `android-sdk-platform-tools` udev rules.
6. Windows: install the Google USB driver.
7. Force it: `fastboot reboot-bootloader`, or power-cycle into fastboot.
8. Last resort: replace the USB-C cable and retry on another host OS.

### To re-lock bootloader

**⚠️ THIS WILL WIPE THE DEVICE COMPLETELY — only for returning to stock.**
```bash
fastboot flashing lock
# Forces a factory reset and re-locks the bootloader.
```

### Recovery artifact checklist

| Artifact         | Source                                            | Required for      |
|------------------|---------------------------------------------------|-------------------|
| `boot.img`       | Nuxel kernel build (see `boot/README.md`)         | boot              |
| `vendor_boot.img`| Extracted from factory / custom                   | display + touch   |
| `dtbo.img`       | Extracted from factory / custom                   | device tree       |
| `vbmeta.img`     | Disabled-verification vbmeta (flags 2)            | sign-free boot    |
| firmware blobs   | `firmware/install-firmware.sh` + `manifest.yml`   | modem/WiFi/BT/GPU |

> Firmware acquisition/verification flow (verify-only vs on-device) is detailed in
> `docs/firmware-verification.md`; it is **hardware-gated** until a real mustang unit.

---

## Serial-Specific Notes for 58211FDCQ001LA

| Property             | Value              |
|----------------------|--------------------|
| **Serial**           | 58211FDCQ001LA     |
| **HW Version**       | MP1.0              |
| **SKU**              | G45RY              |
| **Earliest Factory Image** | mustang-bp1a.250405.001 |
| **OEM Unlock**       | Must be enabled in Developer Options |
| **Bootloader Version** | mustang-1.0-XXXXXXXX |

**Important:** If you ever see `58211FDCQ001LA` with a different status (like `fastboot` showing `no permissions`), ensure:
1. USB debugging was enabled before booting to bootloader
2. You authorized the computer's RSA key when connected via ADB
3. The device is not in "charging only" USB mode

---

## Partition Layout for mustang

| Partition       | Size   | Purpose                    |
|-----------------|--------|----------------------------|
| boot_a/boot_b   | 96MB   | Kernel + initramfs         |
| vendor_boot_a/b | 96MB   | Vendor ramdisk + DTBO      |
| init_boot_a/b   | 8MB    | Generic ramdisk (required) |
| dtbo_a/dtbo_b   | 16MB   | Device tree overlay        |
| vbmeta_a/b      | 64KB   | AVB verification metadata  |
| super           | 8GB    | Dynamic partitions         |
| modem_a/modem_b | 200MB  | Exynos 5500 firmware       |
| dsp_a/dsp_b     | 64MB   | DSP firmware               |
| persist         | 32MB   | Calibration data           |
| metadata        | 64MB   | OTA metadata               |
| userdata        | Remainder | User data                |

---

## Vendor Boot Images

After unlocking, you may need to extract the stock `vendor_boot.img` and `dtbo.img` from the factory image to get working hardware support. Nuxel provides custom versions, but for reference:

```bash
# Extract from factory image
unzip mustang-factory-*.zip
cd mustang-factory-*/
unzip image-mustang-*.zip

# Key files:
# - boot.img: Stock boot image
# - vendor_boot.img: Stock vendor boot
# - init_boot.img: Stock init boot
# - dtbo.img: Stock device tree overlay
# - vbmeta.img: Stock verified boot metadata
```

---

## References

- Google Factory Images: https://developers.google.com/android/images#mustang
- AOSP Verified Boot: https://source.android.com/security/verifiedboot
- Titan M3: https://security.googleblog.com/2024/10/google-pixel-10-titan-m3-security.html
- postmarketOS Device Porting: https://wiki.postmarketos.org/wiki/Porting_to_a_new_device
